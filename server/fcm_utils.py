import json
from typing import Iterable, Dict, Any, List
from config import (
    FIREBASE_CREDENTIALS,
    logger,
)
from models.device_token import DeviceToken

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except Exception as e:  # pragma: no cover
    firebase_admin = None
    messaging = None
    credentials = None
    logger.error(f"firebase_admin not available: {e}")

_initialized = False

def _init_app() -> None:
    global _initialized
    if _initialized:
        return
    if not FIREBASE_CREDENTIALS:
        logger.warning("Firebase env vars missing; FCM disabled")
        return
    if firebase_admin is None:
        return
    try:
        cred = credentials.Certificate(FIREBASE_CREDENTIALS)
        firebase_admin.initialize_app(cred)
        _initialized = True
        logger.info("Firebase Admin SDK initialized for FCM")
    except Exception as e:  # pragma: no cover
        logger.exception(f"Failed to initialize Firebase Admin SDK: {e}")


def send_push_to_users(user_ids: Iterable[str], data_payload: Dict[str, Any]) -> None:
    """Send a data push notification to all device tokens for the given users.

    Only data messages are required for CallKit-like behavior; an optional
    notification object can be included for fallback UI.
    """
    _init_app()
    if not _initialized or messaging is None:
        return
    unique_ids = {str(u) for u in user_ids}
    if not unique_ids:
        return
    tokens: List[DeviceToken] = DeviceToken.query.filter(
        DeviceToken.user_id.in_(list(unique_ids))
    ).all()
    if not tokens:
        logger.info('No device tokens for push')
        return

    # Build messages list
    messages = []
    for t in tokens:
        # FCM requires all values in data dict to be strings
        data_section = {k: str(v) for k, v in data_payload.items()}
        notification = messaging.Notification(
            title=data_payload.get('title', 'ConversationCoach'),
            body=data_payload.get('body', '')
        )
        android_config = messaging.AndroidConfig(priority='high')
        aps = messaging.Aps(
            content_available=True,
            sound='default'
        )
        apns_config = messaging.APNSConfig(payload=messaging.APNSPayload(aps=aps))
        message = messaging.Message(
            token=t.token,
            data=data_section,
            notification=notification,
            android=android_config,
            apns=apns_config,
        )
        messages.append(message)

    try:
        # Use send_all for batching (up to 500 messages)
        response = messaging.send_each(messages)
        if response.failure_count:
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    logger.error(f"FCM send failed for token index {idx}: {resp.exception}")
    except Exception as e:  # pragma: no cover
        logger.exception(f"FCM send error: {e}")
