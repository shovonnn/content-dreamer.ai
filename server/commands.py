from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    abort,
    Blueprint,
)
from models.db_utils import db
from models.user import User
from models.admin_staff import AdminStaff
from cache import cache_store
from config import (
    logger,
)
import click
from datetime import datetime
from uuid import uuid4
from socketio_utils import socketio
import time
from paramiko import SSHClient
import json
import queue_util
from paramiko.transport import Transport, DEFAULT_WINDOW_SIZE
import requests
import config
from typing import List
import os

app_commands = Blueprint('app', __name__)


@app_commands.cli.command(with_appcontext=True)
def setup_db():
  db.create_all()

@app_commands.cli.command(with_appcontext=False)
@click.argument('vendor_name')
@click.option('--scopes', '-s', multiple=True)
def gen_access_token(vendor_name, scopes):
  pass

@app_commands.cli.command(with_appcontext=True)
def sync_name_email():
  from typing import List
  from auth_utils import get_management_access_token
  users: List[User] = User.query.all()
  access_token = get_management_access_token()
  for user in users:
    if not user.name or not user.email:
      user.fetch_name_email(access_token)

@app_commands.cli.command(with_appcontext=True)
@click.option('--email', '-e')
@click.option('--name', '-n')
@click.option('--subject', '-s')
@click.option('--template', '-t')
def send_email(email, name, subject, template):
  response = requests.post(
		"https://api.mailgun.net/v3/mg.contentdreamer.ai/messages",
		auth=("api", config.mailgun_api_key),
		data={"from": "ContentDreamer AI <support@contentdreamer.ai>",
			"to": f"{name} <{email}>",
			"subject": subject,
			"template": template,
			"h:X-Mailgun-Variables": f'{{"name": "{name}"}}'})
  print(response.status_code, response.text)

