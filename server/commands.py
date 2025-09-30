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
from tenacity import RetryError
from tenacity import retry, stop_after_attempt, wait_random_exponential
import requests
import config
from typing import List
from models.recording_segment import RecordingChunk
from transcription_utils import transcribe_chunk_record, transcribe_chunk_job, transcribe_chunk_record_openai
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
		"https://api.mailgun.net/v3/mg.devassistant.ai/messages",
		auth=("api", config.mailgun_api_key),
		data={"from": "DevAssistant AI <support@devassistant.ai>",
			"to": f"{name} <{email}>",
			"subject": subject,
			"template": template,
			"h:X-Mailgun-Variables": f'{{"name": "{name}"}}'})
  print(response.status_code, response.text)


@app_commands.cli.command('transcribe-chunk', with_appcontext=True)
@click.argument('chunk_id')
@click.option('--language', '-l', default='en-US', help='Language code, e.g., en-US (Google only)')
@click.option('--enqueue', is_flag=True, help='Enqueue as background job instead of running synchronously')
@click.option('--provider', '-p', type=click.Choice(['google','openai']), default='google', help='Transcription provider')
@click.option('--model', '-m', default=None, help='OpenAI model override (e.g., gpt-4o-transcribe)')
@click.option('--prompt', default=None, help='Optional prompt/context (OpenAI only)')
def transcribe_chunk_cli(chunk_id, language, enqueue, provider, model, prompt):
  """Transcribe a RecordingChunk by DB id.
  Example: flask app transcribe-chunk <chunk_id> --language en-US --enqueue
  """
  rec = RecordingChunk.query.get(chunk_id)
  if not rec:
    click.echo(f"Chunk {chunk_id} not found")
    return
  if enqueue:
    job = transcribe_chunk_job(rec.id, language_code=language, provider=provider, prompt=prompt)
    job.enqueue(timeout='15m')
    click.echo(f"Enqueued transcription job for {rec.id}")
  else:
    if provider == 'openai':
      transcribe_chunk_record_openai(rec, model=model, response_format='text', prompt=prompt)
    else:
      transcribe_chunk_record(rec, language_code=language)
    click.echo(f"Transcription status: {rec.transcription_status}")


@app_commands.cli.command("create-admin-staff", with_appcontext=True)
@click.option('--name', prompt=True, help='Full name for the staff user')
@click.option('--email', prompt=True, help='Unique email for login')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.option('--access', type=click.Choice(['superadmin','admin','editor','viewer']), default='editor')
def create_admin_staff(name, email, password, access):
  """Create a new admin staff account."""
  existing = AdminStaff.query.filter_by(email=email.lower().strip()).first()
  if existing:
    click.echo('Staff with that email already exists.')
    return
  staff = AdminStaff.create(name=name, email=email, password=password, access_level=access)
  click.echo(f"Created staff {staff.email} with id {staff.id} and access {staff.access_level}")


@app_commands.cli.command('export-chunk-wav', with_appcontext=True)
@click.argument('chunk_id')
@click.option('--out', '-o', help='Output file path. Defaults to exports/<id>.wav')
def export_chunk_wav(chunk_id, out):
  """Write the binary data for a RecordingChunk to a .wav file.
  Example: flask app export-chunk-wav <chunk_id> -o /tmp/segment.wav
  """
  rec = RecordingChunk.query.get(chunk_id)
  if not rec:
    click.echo(f"Chunk {chunk_id} not found")
    return
  # Determine output path
  if out:
    out_path = out
  else:
    export_dir = os.path.join(os.getcwd(), 'exports')
    os.makedirs(export_dir, exist_ok=True)
    out_path = os.path.join(export_dir, f"{rec.id}.wav")
  try:
    # Write bytes as-is. Assumes data contains WAV bytes.
    with open(out_path, 'wb') as f:
      f.write(rec.data or b'')
    click.echo(f"Wrote {len(rec.data or b'')} bytes to {out_path}")
  except Exception as e:
    click.echo(f"Failed to write file: {e}")


@app_commands.cli.command('transcribe-session', with_appcontext=True)
@click.argument('session_id')
@click.option('--provider', '-p', type=click.Choice(['google','openai']), default='google')
@click.option('--language', '-l', default='en-US', help='Language code (Google only)')
@click.option('--model', '-m', default=None, help='OpenAI model override')
@click.option('--prompt', default=None, help='Optional prompt/context (OpenAI)')
def transcribe_session(session_id, provider, language, model, prompt):
  """Concatenate all chunks for a session and transcribe as one.
  Prints transcript to console.
  """
  from models.recording_segment import RecordingChunk
  from transcription_utils import transcribe_bytes, transcribe_bytes_openai
  chunks = RecordingChunk.list_by_session(session_id)
  if not chunks:
    click.echo('No chunks for session')
    return
  wav_bytes = RecordingChunk.concat_session_wav(session_id)
  content_type = 'audio/wav'
  try:
    if provider == 'openai':
      text = transcribe_bytes_openai(wav_bytes, content_type, model=model, response_format='text', prompt=prompt)
    else:
      text = transcribe_bytes(wav_bytes, content_type, language_code=language)
    click.echo(text or '[Empty transcript]')
  except Exception as e:
    click.echo(f"Transcription failed: {e}")
