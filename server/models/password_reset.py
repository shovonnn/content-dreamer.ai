from .db_utils import db
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

class PasswordReset(db.Model):
    __tablename__ = 'password_resets'
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'), index=True, nullable=False)
    token_hash = db.Column(db.String(256), nullable=False)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    expires_on = db.Column(db.DateTime, nullable=False)
    used_on = db.Column(db.DateTime, nullable=True)

    @classmethod
    def create(cls, user_id: str, token_plain: str, ttl_minutes: int = 60):
        rec = PasswordReset(
            id=str(uuid4()),
            user_id=user_id,
            token_hash=generate_password_hash(token_plain),
            expires_on=datetime.utcnow() + timedelta(minutes=ttl_minutes),
        )
        db.session.add(rec)
        db.session.commit()
        return rec

    def matches(self, token_plain: str) -> bool:
        if self.used_on is not None:
            return False
        if datetime.utcnow() > self.expires_on:
            return False
        return check_password_hash(self.token_hash, token_plain)

    def mark_used(self):
        self.used_on = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
