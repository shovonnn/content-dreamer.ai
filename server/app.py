import os
if not os.environ.get("DISABLE_GEVENT_PATCH"):
    from gevent import monkey
    monkey.patch_all()

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    abort,
)
from models.db_utils import db
from models.user import User
from models.otp import OTP
from config import (
    logger,
)
from flask_session import Session
from events import socketio
from flask_cors import CORS
import config
import os
from flask_migrate import Migrate
import json
from werkzeug.exceptions import HTTPException
from flask_jwt_extended import JWTManager
from datetime import timedelta
from admin_auth import AdminAuth
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from dotenv import load_dotenv
from models.password_reset import PasswordReset
from models.credit_ledger import CreditLedger
load_dotenv()

def create_app(is_testing = False):
    app = Flask(__name__, static_url_path='')
    app.config['ENV'] = os.environ.get('ENV', 'development')
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = "redis"
    app.template_folder = 'templates'
    app.static_folder = 'static'

    app.config['JWT_SECRET_KEY'] = config.jwt_secret_key  # Change this to a secure secret key
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config.jwt_token_expires

    if is_testing:
        app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:////tmp/tests.db'
    else:
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URI')
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    if not is_testing:
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            'pool_size': 30,
            'max_overflow': 10,
            'pool_recycle': 3600
        }
    db.init_app(app)
    Session(app)
    migrate = Migrate(app, db)
    JWTManager(app)
    socketio.init_app(app, async_mode="gevent", message_queue='redis://', cors_allowed_origins="*")

    app.register_error_handler(Exception, handle_exception)

    CORS(app, origins=['http://localhost:56808', 'http://localhost:*', 'https://mahfuz.ngrok.io', 'https://app.conversation_coach.app'], support_credentials=True)
    
    AdminAuth().init_app(app)
    admin = Admin(app, name='ConversationCoach Admin')
    admin.add_view(ModelView(User, db.session))
    admin.add_view(ModelView(Call, db.session))  # NEW
    admin.add_view(ModelView(RecordingChunk, db.session))
    admin.add_view(ModelView(RecordingSession, db.session))
    
    from views import app_views
    app.register_blueprint(app_views)
    from views_auth import auth_views
    app.register_blueprint(auth_views)
    from views_calls import bp_calls  # NEW
    app.register_blueprint(bp_calls)
    from views_staff import staff_views
    app.register_blueprint(staff_views)

    from commands import app_commands
    app.register_blueprint(app_commands)
    # from seeds import seed_commands
    # app.register_blueprint(seed_commands)

    return app


def handle_exception(e):
    logger.info(request.url)
    logger.exception(e)
    message = str(e)
    if hasattr(e, 'description'):
        message = e.description
    if hasattr(e, 'code'):
        code = e.code
    else:
        code = 500
    return jsonify({'error': message}), code


if __name__ == "__main__":
    app = create_app()
    socketio.run(app, host='localhost', port=5000, debug=True)
