from functools import (
    wraps,
)
from flask import (
    redirect,
    url_for,
    request,
    abort,
    _request_ctx_stack,
    session,
    jsonify,
)
from typing import (
    Callable,
)
from six.moves.urllib.request import urlopen
from models.db_utils import db
from models.user import User
from datetime import (
    datetime,
)
from jose import jwt
import os
import json
from config import logger
import config
from werkzeug.wrappers import Response
from uuid import uuid4
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, create_access_token, create_refresh_token


AUTH0_DOMAIN = config.auth0_domain
API_AUDIENCE = config.auth0_api_audience
ALGORITHMS = config.auth0_algorithms

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

# Format error response and append status code
def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                        "description":
                            "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != "bearer":
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must start with"
                            " Bearer"}, 401)
    elif len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                        "description": "Token not found"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                        "description":
                            "Authorization header must be"
                            " Bearer token"}, 401)

    token = parts[1]
    return token

def validate_token(token):
    jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if not rsa_key:
        raise AuthError({"code": "invalid_header",
                        "description": "Unable to find appropriate key"}, 401)
    return jwt.decode(
        token,
        rsa_key,
        algorithms=ALGORITHMS,
        audience=API_AUDIENCE,
        issuer="https://"+AUTH0_DOMAIN+"/"
    )
    

def requires_auth(f):
    """Determines if the Access Token is valid
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Verify the JWT in the request
        verify_jwt_in_request()

        # Get the user identity from the JWT
        user_id = get_jwt_identity()

        # Load the user from the database
        user = User.query.get(user_id)
        if not user:
            return jsonify({"msg": "User not found"}), 401

        # Add 'current_user' to kwargs
        kwargs['current_user'] = user

        # Call the original function with updated kwargs
        return f(*args, **kwargs)
    return decorated

def requires_scope(required_scope):
    """Determines if the required scope is present in the Access Token
    Args:
        required_scope (str): The scope required to access the resource
    """
    token = get_token_auth_header()
    unverified_claims = jwt.get_unverified_claims(token)
    if unverified_claims.get("scope"):
            token_scopes = unverified_claims["scope"].split()
            for token_scope in token_scopes:
                if token_scope == required_scope:
                    return True
    return False

def get_management_access_token():
    import json, requests

    # Configuration Values
    domain = config.auth0_mgmt_domain   
    audience = f'https://{domain}/api/v2/'
    client_id = config.auth0_client_id
    client_secret = config.auth0_client_secret
    grant_type = "client_credentials" # OAuth 2.0 flow to use

    # Get an Access Token from Auth0
    base_url = f"https://{domain}"
    payload =  { 
        'grant_type': grant_type,
        'client_id': client_id,
        'client_secret': client_secret,
        'audience': audience
    }
    response = requests.post(f'{base_url}/oauth/token', data=payload)
    oauth = response.json()
    access_token = oauth.get('access_token')
    if not access_token:
        print(response.text)
        raise Exception("Unable to retrieve Access Token")
    return access_token

def call_auth0_management_api(api_path, access_token):
    import json, requests

    domain = config.auth0_mgmt_domain
    base_url = f"https://{domain}"
    # Add the token to the Authorization header of the request
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    res = requests.get(f'{base_url}/{api_path}', headers=headers)
    return res.json()

# def requires_permission(*permissions):
#     def decorator(f: Callable):
#         @wraps(f)
#         def decorated_function(*args, **kwargs):
#             if 'current_user' not in kwargs:
#                 return Response('Unauthorized', 401)
#             if 'business' not in kwargs:
#                 return Response('Business ID is required', 400)
#             business:Business = kwargs['business']
#             user:User = kwargs['current_user']
#             matched_permissions = user.has_permission(business, permissions)
#             if not matched_permissions:
#                 return Response('Unauthorized', 403)
#             if 'matched_permissions' in kwargs:
#                 matched_permissions.update(kwargs['matched_permissions'])
#             kwargs['matched_permissions'] = matched_permissions
#             return f(*args, **kwargs)
#         return decorated_function
#     return decorator

def create_tokens(user: User):
    access_token = create_access_token(identity=user.id, expires_delta=config.jwt_token_expires)
    refresh_token = create_refresh_token(identity=user.id, expires_delta=config.jwt_token_expires*25)
    return {
        'access_token': access_token,
        'refresh_token': refresh_token
    }