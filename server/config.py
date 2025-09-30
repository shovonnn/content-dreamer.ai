import os
import logging
import sys
import logging.handlers
from datetime import timedelta
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger('ApiAPP')
logger.setLevel(logging.INFO)
#logger.addHandler(logging.handlers.SysLogHandler(address = '/dev/log'))
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.addHandler(logging.FileHandler("app.log"))

api_threshold = 1000
server_domain = 'server.devassistant.ai'
auth0_domain = os.getenv('AUTH0_DOMAIN', 'dev-wx62kx3mbwa7l3ie.us.auth0.com')
auth0_api_audience = os.getenv('AUTH0_AUD', 'http://localhost:5000')
auth0_algorithms = ["RS256"]

auth0_mgmt_domain = os.getenv('AUTH0_MGMT_DOMAIN', 'dev-wx62kx3mbwa7l3ie.us.auth0.com')
auth0_client_id = os.getenv('AUTH0_CLIENT_ID', '5Q6VZ4j8ZL2w7aX5q6ZQxJ3C5W6F3q3z')
auth0_client_secret = os.getenv('AUTH0_CLIENT_SECRET', '5Q6VZ4j8ZL2w7aX5q6ZQxJ3C5W6F3q3z')

google_oauth_client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID', '225252280110-pla5o2astfludh3jv7lelv06bgnimqk7.apps.googleusercontent.com')

openai_key = os.getenv("OPENAI_API_KEY")

stripe_api_key = os.getenv("STRIPE_API_KEY")

mailgun_api_key = os.getenv("MAILGUN_API_KEY")

admin_username = os.getenv("ADMIN_USERNAME", "admin")
admin_password = os.getenv("ADMIN_PASSWORD", "admin_password")


app_url = os.getenv('APP_URL')

jwt_secret_key = os.getenv('JWT_SECRET_KEY', 'your_jwt_secret_key')

jwt_token_expires = timedelta(seconds=3600*12)

cdn_url = os.getenv('CDN_URL', 'https://localhost:5000/static')

FIREBASE_CREDENTIALS = os.getenv('FIREBASE_CREDENTIALS')