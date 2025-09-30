from .db_utils import db
from sqlalchemy_serializer import SerializerMixin
from dataclasses import dataclass
from typing import List
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4
import re



class User(db.Model, SerializerMixin):
  id = db.Column(db.String(100), primary_key=True)
  auth0_id = db.Column(db.String(200), index=True)
  name = db.Column(db.String(100), default=None)
  email = db.Column(db.String(200), default=None)
  phone = db.Column(db.String(20), unique=True, nullable=True)
  verified = db.Column(db.Boolean, default=False)
  password_hash = db.Column(db.String(256))
  # Type of partner account if this user is a partner (e.g., 'doctor', 'pharmacy', 'lab')
  partner_account_type = db.Column(db.String(50), default=None)
  # Avatar / profile photo URL
  avatar_url = db.Column(db.String(300), default=None)
  created_on = db.Column(db.DateTime, default=db.func.current_timestamp())
  updated_on = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

  def set_password(self, password):
    self.password_hash = generate_password_hash(password)

  def check_password(self, password):
    return check_password_hash(self.password_hash, password)

  def fetch_name_email(self, access_token=None):
    from auth_utils import get_management_access_token, call_auth0_management_api
    if not access_token:
      access_token = get_management_access_token()
    response = call_auth0_management_api(f'api/v2/users/{self.auth0_id}', access_token)
    if 'name' in response:
      self.name = response['name']
    if 'email' in response:
      self.email = response['email']
    db.session.commit()

  @classmethod
  def create(cls, name, email, password):
    user = User(id=str(uuid4()), name=name, email=email)
    if password:
      user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user

  @classmethod
  def create_from_phone(cls, phone):
    user = User(id=str(uuid4()), phone=phone)
    db.session.add(user)
    db.session.commit()
    return user

  def __repr__(self):
    return f"<User({self.id}) Name {self.name}>"