from models.db_utils import db
from datetime import datetime

class DeviceToken(db.Model):
    __tablename__ = 'device_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), index=True, nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    platform = db.Column(db.String(20), nullable=True)  # ios | android | web | other
    created_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_on = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    @classmethod
    def register(cls, user_id: str, token: str, platform: str | None = None):
        rec = cls.query.filter_by(token=token).first()
        if rec:
            changed = False
            if rec.user_id != user_id:
                rec.user_id = user_id
                changed = True
            if platform and rec.platform != platform:
                rec.platform = platform
                changed = True
            if changed:
                db.session.add(rec)
                db.session.commit()
            return rec
        rec = cls(user_id=user_id, token=token, platform=platform)
        db.session.add(rec)
        db.session.commit()
        return rec
