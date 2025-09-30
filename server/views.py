from flask import (
  Flask,
  render_template,
  request,
  redirect,
  url_for,
  jsonify,
  abort,
  Blueprint,
  g,
)
from sqlalchemy import (
    Column,
    Boolean,
)
from auth_utils import (
    requires_auth,
    requires_scope,
    get_token_auth_header,
)
from models.db_utils import db
from models.user import User
from cache import cache_store
from config import (
    logger,
)
import config
from hashlib import md5
import phonenumbers
import re
import os
import urllib
import datetime
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import click
import random
from sqlalchemy.sql.expression import func
import requests
import json
import jwt
import humanize
from datetime import datetime, timedelta
import time
import pytz
import logging
import logging.handlers
import sys
from werkzeug.exceptions import HTTPException
import dateutil.parser as date_parser
from urllib.parse import unquote
from flask_cors import cross_origin
from uuid import uuid4
from typing import List
from flask_validate_json import validate_json
import os
from uuid import uuid4
try:
  import boto3  # type: ignore
except Exception:  # pragma: no cover
  boto3 = None
try:
  from werkzeug.utils import secure_filename as _secure_filename  # type: ignore
  def secure_filename(name: str) -> str:
    return _secure_filename(name)
except Exception:  # pragma: no cover
  import re as _re
  def secure_filename(name: str) -> str:  # fallback
    name = name or 'upload'
    name = _re.sub(r'[^A-Za-z0-9_.-]+', '_', name)
    return name.strip('._') or 'upload'

ALLOWED_IMAGE_MIME = {
  'image/jpeg','image/png','image/webp','image/jpg','image/heic','image/heif'
}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB avatar cap
USE_S3 = os.getenv('USE_S3', '0') in ('1','true','TRUE')
S3_BUCKET = os.getenv('S3_BUCKET')
S3_REGION = os.getenv('S3_REGION')

def _ensure_dir(path: str):
  os.makedirs(path, exist_ok=True)

def _save_file_to_local(fs, rel_dir: str):
  root = os.path.join('static', rel_dir)
  _ensure_dir(root)
  name = secure_filename(fs.filename or f"upload-{uuid4().hex}.bin")
  dest = os.path.join(root, name)
  fs.save(dest)
  size_bytes = os.path.getsize(dest)
  mime = fs.mimetype
  return os.path.join(rel_dir, name), size_bytes, mime

def _upload_to_s3(fs, prefix: str):
  if boto3 is None or not S3_BUCKET:
    raise RuntimeError('S3 not configured')
  s3 = boto3.client('s3', region_name=S3_REGION) if S3_REGION else boto3.client('s3')
  name = secure_filename(fs.filename or f"upload-{uuid4().hex}.bin")
  key = f"{prefix.rstrip('/')}/{uuid4().hex}-{name}"
  body = fs.stream if hasattr(fs, 'stream') else fs
  extra_args = {'ContentType': fs.mimetype} if getattr(fs,'mimetype',None) else None
  if extra_args:
    s3.upload_fileobj(body, S3_BUCKET, key, ExtraArgs=extra_args)
  else:
    s3.upload_fileobj(body, S3_BUCKET, key)
  body.seek(0, os.SEEK_END)
  size = body.tell()
  body.seek(0)
  return key, size, getattr(fs,'mimetype',None)

def _avatar_public_url(stored: str | None):
  if not stored:
    return None
  if stored.startswith('s3://'):
    if boto3 is None or not S3_BUCKET:
      return None
    key = stored.split('/', 3)[-1]
    s3 = boto3.client('s3', region_name=S3_REGION) if S3_REGION else boto3.client('s3')
    try:
      return s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET,'Key': key}, ExpiresIn=3600)
    except Exception:
      return None
  # relative path under static
  if stored.startswith('http://') or stored.startswith('https://'):
    return stored
  return f"{config.cdn_url}/{stored}" if config.cdn_url else stored

app_views = Blueprint("app_views", __name__)


@app_views.route('/api/external', methods=['GET'])
@cross_origin(headers=["Content-Type", "Authorization"])
@requires_auth
def index(current_user, **kwargs):
  return jsonify("ok"), 200

@app_views.route('/api/userdata', methods=['GET'])
@requires_auth
def get_userdata(current_user: User, **kwargs):
  return jsonify({
    'id': current_user.id,
    'name': current_user.name,
    'email': current_user.email,
    'phone': current_user.phone,
    'partner_account_type': current_user.partner_account_type,
    'avatar_url': _avatar_public_url(current_user.avatar_url),
  })

@app_views.route('/api/profile/update', methods=['POST'])
@requires_auth
def update_profile(current_user: User, **kwargs):
  data = request.get_json(force=True, silent=True) or {}
  name = data.get('name')
  email = data.get('email')
  avatar_url = data.get('avatar_url')
  new_password = data.get('new_password')
  confirm_password = data.get('confirm_password')
  old_password = data.get('old_password')

  # basic validations
  if new_password or confirm_password:
    if new_password != confirm_password:
      abort(400, 'Password confirmation does not match')
    if new_password and len(new_password) < 6:
      abort(400, 'Password must be at least 6 characters')
    if current_user.password_hash and (not old_password or not current_user.check_password(old_password)):
      abort(400, 'Old password incorrect')

  # unique email check
  if email and email != current_user.email:
    from models.user import User as U
    if U.query.filter_by(email=email).first():
      abort(400, 'Email already in use')
    current_user.email = email

  if name:
    current_user.name = name
  if avatar_url:
    current_user.avatar_url = avatar_url
  if new_password:
    current_user.set_password(new_password)
  db.session.add(current_user)
  db.session.commit()
  return jsonify({'ok': True, 'user': {
    'id': current_user.id,
    'name': current_user.name,
    'email': current_user.email,
    'phone': current_user.phone,
    'partner_account_type': current_user.partner_account_type,
    'avatar_url': _avatar_public_url(current_user.avatar_url),
  }}), 200

@app_views.route('/api/profile/request_phone_change', methods=['POST'])
@requires_auth
def request_phone_change(current_user: User, **kwargs):
  from models.otp import OTP
  from sms_utils import send_otp
  data = request.get_json(force=True, silent=True) or {}
  new_phone = data.get('new_phone')
  if not new_phone:
    abort(400, 'new_phone required')
  otp_obj, code = OTP.create(new_phone)
  send_otp(new_phone, code)
  return jsonify({'ok': True, 'message': 'OTP sent'}), 200

@app_views.route('/api/profile/confirm_phone_change', methods=['POST'])
@requires_auth
def confirm_phone_change(current_user: User, **kwargs):
  from models.otp import OTP
  data = request.get_json(force=True, silent=True) or {}
  new_phone = data.get('new_phone')
  code = data.get('code')
  if not new_phone or not code:
    abort(400, 'new_phone and code required')
  rec = OTP.get_by_code(new_phone, code)
  if not rec or not rec.verify(code):
    abort(400, 'Invalid or expired OTP')
  # ensure phone not used
  from models.user import User as U
  if U.query.filter_by(phone=new_phone).first():
    abort(400, 'Phone already in use')
  current_user.phone = new_phone
  db.session.add(current_user)
  from models.db_utils import db as _db
  _db.session.delete(rec)
  _db.session.commit()
  return jsonify({'ok': True, 'phone': new_phone}), 200

@app_views.route('/api/profile/avatar', methods=['POST'])
@requires_auth
def upload_avatar(current_user: User, **kwargs):
  fs = request.files.get('avatar') or request.files.get('file')
  if not fs:
    abort(400, 'avatar file required (field name avatar)')
  mime = (getattr(fs, 'mimetype', '') or '').lower()
  # Accept any image/* but still restrict extremely
  if not (mime in ALLOWED_IMAGE_MIME or mime.startswith('image/')):
    abort(400, f'Unsupported image type: {mime}')
  # size check: attempt seek; fallback to read
  size = None
  try:
    fs.stream.seek(0, os.SEEK_END)
    size = fs.stream.tell()
    fs.stream.seek(0)
  except Exception:
    try:
      data_bytes = fs.read()
      size = len(data_bytes)
      from io import BytesIO
      fs.stream = BytesIO(data_bytes)
      fs.stream.seek(0)
    except Exception:
      size = None
  if size is not None and size > MAX_UPLOAD_BYTES:
    abort(400, 'File too large (>5MB)')
  try:
    if USE_S3 and S3_BUCKET:
      key, _, _ = _upload_to_s3(fs, f"avatars/{current_user.id}")
      stored = f"s3://{S3_BUCKET}/{key}"
    else:
      path_rel, _, _ = _save_file_to_local(fs, f"uploads/avatars/{current_user.id}")
      stored = path_rel
    current_user.avatar_url = stored
    db.session.add(current_user)
    db.session.commit()
    return jsonify({'ok': True, 'avatar_url': _avatar_public_url(stored)}), 200
  except Exception as e:
    logger.error(f"Avatar upload failed: {e}")
    abort(500, 'Upload failed')

@app_views.route('/terms', methods=['GET'])
def show_terms_page():
  return render_template('terms.html')

@app_views.route('/privacy', methods=['GET'])
def show_privacy_page():
  return render_template('privacy.html')

@app_views.route('/tinker', methods=['GET'])
def tinker_view():
  requests.get("http://google.com")
  return render_template('selection.html')

