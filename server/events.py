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
from models.call import Call  # NEW
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

# ---- Minimal signaling events (namespace-less for now) ----
def require_call(f):
    def wrapper(data, *args, **kwargs):
        user_id = get_user_id()
        if not user_id:
            return { 'error': 'unauthenticated' }
        event_type = f.__name__
        logger.info(f"Event '{event_type}' received with data: {data}")
        call_id = data.get('callId')
        call = Call.query.get(call_id) if call_id else None
        if not call or user_id not in [call.caller_id, call.callee_id]:
            raise ValueError("Invalid or missing callId")
        return f(data, user_id, call, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@socketio.on('call:invite')
@require_call
def on_call_invite(data, user_id, call):
    if call.status != 'initiated':
        logger.info(f"Call invite failed: call status is {call.status}")
        return { 'error': 'call already in progress or ended' }
    emit('call:invite', data, to=call.callee_id)
    push_payload = {
        'type': 'call.invite',
        'callId': call.id,
        'toUserId': call.callee_id,
        'fromUserId': call.caller_id,
        'name': call.caller.name,
        'handle': 'ConversationCoach',
        'avatar': ''
    }
    send_push_to_users([call.callee_id], push_payload)
    return { 'ok': True, 'callId': call.id }

@socketio.on('call:ringing')
@require_call
def on_call_ringing(data, user_id, call):
    if call.status not in ['initiated', 'ringing']:
        logger.info(f"Call ringing failed: call status is {call.status}")
        return { 'error': 'call already in progress or ended' }
    call.mark_ringing()
    emit('call:ringing', data, to=call.caller_id)
    return { 'ok': True }

@socketio.on('call:cancel')
@require_call
def on_call_cancel(data, user_id, call):
    call.mark_canceled()
    to_user = call.callee_id if call.caller_id == user_id else call.caller_id
    emit('call:cancel', data, to=to_user)
    send_push_to_users([to_user], {
        'type': 'call.cancel',
        'callId': call.id,
        'fromUserId': user_id
    })
    logger.info(f"Call cancel for callId {call.id} with data: {data}")
    return { 'ok': True }

@socketio.on('call:accept')
@require_call
def on_call_accept(data, user_id, call):
    if call.status not in ['initiated', 'ringing']:
        logger.info(f"Call accept failed: call status is {call.status}")
        return { 'error': 'call already in progress or ended' }
    call.mark_accepted()
    logger.info(f"Call accept for callId {call.id} ")
    emit('call:accept', data, to=call.caller_id)
    return { 'ok': True }

@socketio.on('call:reject')
@require_call
def on_call_reject(data, user_id, call):
    call.mark_rejected()
    logger.info(f"Call reject for callId {call.id} ")
    emit('call:reject', data, to=call.caller_id)
    send_push_to_users([call.caller_id], {'type': 'call.cancel', 'callId': call.id})
    return { 'ok': True }

@socketio.on('rtc:requested')
@require_call
def on_rtc_offer(data, user_id, call):
    to_user = call.callee_id if call.caller_id == user_id else call.caller_id
    logger.info(f"RTC offer for {to_user} with data: {data}")
    emit('rtc:requested', data, to=to_user)
    return { 'ok': True }

@socketio.on('rtc:offer')
@require_call
def on_rtc_offer(data, user_id, call):
    to_user = call.callee_id if call.caller_id == user_id else call.caller_id
    logger.info(f"RTC offer for {to_user} with data: {data}")
    emit('rtc:offer', data, to=to_user)
    return { 'ok': True }

@socketio.on('rtc:answer')
@require_call
def on_rtc_answer(data, user_id, call):
    to_user = call.callee_id if call.caller_id == user_id else call.caller_id
    logger.info(f"RTC answer for {to_user} with data: {data}")
    emit('rtc:answer', data, to=to_user)
    return { 'ok': True }

@socketio.on('rtc:candidate')
@require_call
def on_rtc_candidate(data, user_id, call):
    to_user = call.callee_id if call.caller_id == user_id else call.caller_id
    logger.info(f"RTC candidate for {to_user} with data: {data}")
    emit('rtc:candidate', data, to=to_user)
    return { 'ok': True }

@socketio.on('call:end')
@require_call
def on_call_end(data, user_id, call):
    call.mark_ended()
    to_user = call.callee_id if call.caller_id == user_id else call.caller_id
    logger.info(f"Call end for {to_user} with data: {data}")
    emit('call:end', data, to=to_user)
    send_push_to_users([to_user], {'type': 'call.cancel', 'callId': call.id})
    return { 'ok': True }