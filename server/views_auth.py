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
from sklearn import logger
from auth_utils import (
    requires_auth,
    get_token_auth_header,
    create_tokens,
)
from flask_jwt_extended import (
    JWTManager, create_access_token,
    create_refresh_token, jwt_required,
    get_jwt_identity
)
from google.oauth2 import id_token
from google.auth.transport import requests
import config

from models.user import User
from models.otp import OTP
from models.db_utils import db

from sms_utils import send_otp
from models.device_token import DeviceToken
from models.password_reset import PasswordReset
from uuid import uuid4
import secrets
from werkzeug.security import generate_password_hash

auth_views = Blueprint("auth_views", __name__)

def _request_guest_id():
    # Prefer header, fallback to query param
    return (request.headers.get('X-Guest-Id') or request.args.get('guest_id') or '').strip() or None

# Register endpoint
@auth_views.route('/api/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    name = data.get('name', None)
    email = data.get('email', None)
    password = data.get('password', None)
    
    if not all([name, email, password]):
        return jsonify({"message": "Missing parameters"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "Email already registered"}), 400

    new_user = User.create(name=name, email=email, password=password)
    guest_id = _request_guest_id()
    if guest_id:
        new_user.guest_id = guest_id
        db.session.add(new_user)
        db.session.commit()

    tokens = create_tokens(new_user)

    return jsonify(tokens), 200

# Login endpoint
@auth_views.route('/api/login', methods=['POST'])
def login():
    """Authenticate user and return tokens."""
    data = request.get_json()
    email = data.get('email', None)
    password = data.get('password', None)
    
    if not all([email, password]):
        return jsonify({"message": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.password_hash or not user.check_password(password):
        return jsonify({"message": "Invalid email or password"}), 400

    tokens = create_tokens(user)

    return jsonify(tokens), 200

@auth_views.route('/api/login_with_google', methods=['POST'])
def login_with_google():
    """Authenticate user and return tokens."""
    data = request.get_json()
    token = data.get('idToken', None)
    
    if not token:
        return jsonify({"message": "Missing id token"}), 400

    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), config.google_oauth_client_id
        )

        # Extract user information
        userid = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name', '')

        # Check if the user exists or create a new user
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User.create(name=name, email=email, password=None)
        
        tokens = create_tokens(user)

        return jsonify(tokens), 200

    except ValueError:
        # Invalid token
        return jsonify({'error': 'Invalid token'}), 400


@auth_views.route("/api/auth/otp/request", methods=["POST"])
def request_otp():
    phone = request.json.get("phone")
    if not phone: abort(400)
    _, code = OTP.create(phone)
    send_otp(phone, code)
    return jsonify({"message": "OTP sent successfully"}), 200


@auth_views.route("/api/auth/otp/verify", methods=["POST"])
def verify_otp():
    phone = request.json.get("phone")
    code  = request.json.get("code")
    if not phone or not code:
        abort(400, "Phone number and code are required")
    rec = OTP.get_by_code(phone, code)
    if not rec or not rec.verify(code):
        abort(401, "Invalid or expired OTP")
    user = User.query.filter_by(phone=phone).first() or User.create_from_phone(phone)
    user.verified = True
    db.session.delete(rec)
    db.session.add(user)
    db.session.commit()
    tokens = create_tokens(user)
    return jsonify(tokens), 200

@auth_views.route('/api/auth/password/forgot', methods=['POST'])
def password_forgot():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    if not email:
        return jsonify({'message': 'Email required'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        # Do not reveal existence
        return jsonify({'ok': True}), 200
    raw_token = secrets.token_urlsafe(6)
    PasswordReset.create(user.id, raw_token, ttl_minutes=30)
    logger.info(f"Password reset token for {email}: {raw_token}")
    # TODO: send email containing raw_token link
    # send_email(user.email, f"Reset your password: {raw_token}") (placeholder)
    return jsonify({'ok': True}), 200

@auth_views.route('/api/auth/password/reset', methods=['POST'])
def password_reset():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    token = data.get('token')
    new_password = data.get('password')
    if not all([email, token, new_password]):
        return jsonify({'message': 'Missing parameters'}), 400
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'message': 'Invalid token'}), 400
    rec = PasswordReset.query.filter_by(user_id=user.id).order_by(PasswordReset.created_on.desc()).first()
    if not rec or not rec.matches(token):
        return jsonify({'message': 'Invalid token'}), 400
    user.set_password(new_password)
    rec.mark_used()
    db.session.add(user)
    db.session.commit()
    tokens = create_tokens(user)
    return jsonify(tokens), 200

# Token refresh endpoint
@auth_views.route('/api/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token(**kwargs):
    """Refresh the access token using a refresh token."""
    current_user_id = get_jwt_identity()
    current_user = User.query.get(current_user_id)
    tokens = create_tokens(current_user)
    return jsonify(tokens), 200

@auth_views.route('/api/device/register', methods=['POST'])
@requires_auth
def register_device(current_user: User, **kwargs):
    data = request.get_json(force=True, silent=True) or {}
    token = data.get('token')
    platform = data.get('platform')
    if not token:
        return jsonify({'error': 'token required'}), 400
    try:
        DeviceToken.register(current_user.id, token, platform)
        return jsonify({'ok': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@auth_views.route('/api/me', methods=['GET'])
@requires_auth
def get_me(current_user: User, **kwargs):
    return jsonify({
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'avatar_url': current_user.avatar_url,
        'created_on': current_user.created_on.isoformat() if current_user.created_on else None
    }), 200