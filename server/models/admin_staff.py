from .db_utils import db
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash
from uuid import uuid4


class AdminStaff(db.Model, SerializerMixin):
    """Administrative / staff user able to manage doctors, refunds, etc.

    access_level examples:
      - superadmin: full access including deletions & refunds
      - admin: manage all records
      - editor: create / update doctors only
      - viewer: read‑only (future use)
    """
    id = db.Column(db.String(100), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    access_level = db.Column(db.String(50), default='editor')
    active = db.Column(db.Boolean, default=True)
    created_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_on = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @classmethod
    def create(cls, name: str, email: str, password: str, access_level: str = 'editor'):
        staff = cls(id=str(uuid4()), name=name, email=email.lower().strip(), access_level=access_level)
        staff.set_password(password)
        db.session.add(staff)
        db.session.commit()
        return staff

    def __repr__(self):  # pragma: no cover - simple repr
        return f"<AdminStaff {self.email} ({self.access_level})>"
