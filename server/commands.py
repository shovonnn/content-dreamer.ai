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
from email_utils import generate_report_summary_email
from models.report import Report
from models.user import User

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


@app_commands.cli.command(with_appcontext=True)
@click.argument('report_id')
@click.option('--email', required=False, help='Override recipient email')
@click.option('--name', required=False, help='Override recipient name')
def send_report_email(report_id, email=None, name=None):
  """Send a summary email with top 5 suggestions for a report."""
  rep = Report.query.get(report_id)
  if not rep:
    print("Report not found")
    return
  # Prefer report user, otherwise require overrides
  user: User | None = getattr(rep, 'user', None)
  to_email = email or (getattr(user, 'email', None) if user else None)
  to_name = name or (getattr(user, 'name', None) if user else None) or 'there'
  if not to_email:
    print('No recipient email found. Provide --email.')
    return
  subject, html = generate_report_summary_email(report_id)
  payload = {
    "from": "ContentDreamer <support@contentdreamer.ai>",
    "to": f"{to_name} <{to_email}>",
    "subject": subject,
    "html": html,
  }
  resp = requests.post(
    "https://api.mailgun.net/v3/mg.contentdreamer.ai/messages",
    auth=("api", config.mailgun_api_key),
    data=payload,
  )
  print(resp.status_code, resp.text)


@app_commands.cli.command(with_appcontext=True)
@click.option('--user-id', required=False, help='Target a single user id')
@click.option('--send-all', is_flag=True, default=False, help='Send to all users')
@click.option('--logo-url', required=False, help='Optional logo URL for email branding')
def send_latest_report_emails(user_id: str | None, send_all: bool, logo_url: str | None):
  """Send the latest generated report summary email.

  Behavior:
  - If --user-id is provided: find that user's latest generated report and email them.
  - Else if --send-all: iterate all users and send each their latest generated report.
  - "Latest generated" prioritizes reports with status in (complete, partial_ready). If none, falls back to any latest report. As an edge fallback, also checks guest_id == user_id.
  """

  def find_latest_report_for_user(uid: str) -> Report | None:
    # Prefer complete/partial reports
    preferred = (Report.query
      .filter(Report.user_id == uid, Report.status.in_(['complete', 'partial_ready']))
      .order_by(Report.created_on.desc())
      .first())
    if preferred:
      return preferred
    # Fallback to any report for the user
    any_rep = (Report.query
      .filter(Report.user_id == uid)
      .order_by(Report.created_on.desc())
      .first())
    if any_rep:
      return any_rep
    # Edge fallback: if guest_id happened to equal uid (rare)
    guest_rep = (Report.query
      .filter(Report.guest_id == uid)
      .order_by(Report.created_on.desc())
      .first())
    return guest_rep

  def send_for_user(uid: str):
    usr: User | None = User.query.get(uid)
    if not usr:
      print(f"User {uid} not found")
      return
    rep = find_latest_report_for_user(uid)
    if not rep:
      print(f"No report found for user {uid}")
      return
    to_email = getattr(usr, 'email', None)
    to_name = getattr(usr, 'name', None) or 'there'
    if not to_email:
      print(f"User {uid} has no email; skipping")
      return
    subject, html = generate_report_summary_email(rep.id, logo_url=logo_url)
    payload = {
      "from": "ContentDreamer AI <support@contentdreamer.ai>",
      "to": f"{to_name} <{to_email}>",
      "subject": subject,
      "html": html,
    }
    resp = requests.post(
      "https://api.mailgun.net/v3/mg.contentdreamer.ai/messages",
      auth=("api", config.mailgun_api_key),
      data=payload,
    )
    print(f"User {uid}: {resp.status_code}")

  if user_id:
    send_for_user(user_id)
    return
  if send_all:
    users = User.query.all()
    for u in users:
      try:
        send_for_user(u.id)
      except Exception as e:
        print(f"User {getattr(u, 'id', 'unknown')} failed: {e}")
    return
  print("Provide --user-id <id> or --send-all")

