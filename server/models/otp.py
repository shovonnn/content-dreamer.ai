from .db_utils import db
from sqlalchemy_serializer import SerializerMixin
from dataclasses import dataclass
import os, random, hashlib, datetime as dt
from passlib.hash import pbkdf2_sha256
from uuid import uuid4

class OTP(db.Model, SerializerMixin):
    __tablename__ = 'OTP'
    id = db.Column(db.String(100), primary_key=True)
    phone = db.Column(db.String(20), index=True)
    code_hash = db.Column(db.String(120))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime)
    @classmethod
    def create(cls, phone):
        # check if an OTP already exists for this phone
        existing_otps = OTP.query.filter_by(phone=phone).all()
        for existing_otp in existing_otps:
            #if existing OTP created within last minute, raise an error
            if dt.datetime.now() - existing_otp.created_at < dt.timedelta(minutes=1):
                raise ValueError("An OTP was already sent within the last minute.")
            if dt.datetime.now() < existing_otp.expires_at:
                continue  # skip if the existing OTP is still valid
            # if the existing OTP has expired, delete it
            db.session.delete(existing_otp)
            db.session.commit()
        
        code = f"{random.randint(0, 999999):06d}"
        code_hash = pbkdf2_sha256.hash(code)
        expires_at = dt.datetime.now() + dt.timedelta(minutes=5)
        created_at = dt.datetime.now()
        otp = OTP(id=str(uuid4()), phone=phone, code_hash=code_hash, expires_at=expires_at, created_at=created_at)
        db.session.add(otp)
        db.session.commit()
        return otp, code
    
    @classmethod
    def get_by_code(cls, phone, code):
        otps = OTP.query.filter_by(phone=phone).all()
        for otp in otps:
            if dt.datetime.now() > otp.expires_at:
                db.session.delete(otp)
                db.session.commit()
                continue # skip expired OTPs
            # verify the code against the stored hash
            if otp.code_hash and pbkdf2_sha256.verify(code, otp.code_hash):
                return otp
        return None
    
    def verify(self, code):
        if dt.datetime.now() > self.expires_at:
            return False
        return pbkdf2_sha256.verify(code, self.code_hash)
