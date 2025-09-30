from flask import (
    session,
    request,
)
from flask_socketio import emit, join_room, leave_room, disconnect, Namespace
from models.db_utils import db
from models.user import User
import datetime
from socketio_utils import socketio
import queue_util
import auth_utils
from config import logger
from flask_jwt_extended import decode_token
from models.device_token import DeviceToken
from fcm_utils import send_push_to_users

def get_user_id():
    return str(session.get('user_id'))

@socketio.on('connect')
def handle_connect(auth):
    logger.info(f"Client connection requested!")
    if not auth.get('token') or not auth.get('userId'):
        disconnect('Missing token or userId')
    token = auth['token']
    try:
        payload = decode_token(token)
    except Exception as e:
        print(e)
        disconnect('Invalid token')
    # Normalize ids to strings for comparison and socket rooms
    uid = str(auth['userId'])
    user_sub = str(payload.get('sub') or payload.get('identity') or '')
    if user_sub != uid:
        disconnect('User ID mismatch')
    session['token'] = token
    user = User.query.get(auth['userId'])
    if not user:
        disconnect('User not found')
    session['user_id'] = uid
    # Always join a string room id to match emit(to=<str>)
    join_room(uid)


@socketio.on_error()
def handle_error(e):
    logger.error(f"SocketIO error: {e}")
    print(e)
    if type(e) is auth_utils.AuthError:
        emit('auth-error', {'message': str(e)})
        disconnect()


@socketio.on('disconnect')
def handle_disconnect(e, **kwargs):
    logger.info(f"Client disconnected: {e}")
