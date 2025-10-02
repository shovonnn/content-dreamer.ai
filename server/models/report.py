from .db_utils import db
from uuid import uuid4
from datetime import datetime


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.String(100), primary_key=True)
    product_id = db.Column(db.String(100), db.ForeignKey('products.id'), nullable=False, index=True)
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'), nullable=True, index=True)
    guest_id = db.Column(db.String(100), nullable=True, index=True)
    status = db.Column(db.String(50), default='queued', index=True)
    error_message = db.Column(db.Text, nullable=True)
    visibility_cutoff = db.Column(db.Integer, default=5)  # number of items visible to guests
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    created_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_on = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    product = db.relationship('Product', backref=db.backref('reports', lazy=True))
    user = db.relationship('User', backref=db.backref('reports', lazy=True))

    @classmethod
    def create(cls, product_id: str, user_id=None, guest_id=None, visibility_cutoff=5):
        rep = Report(
            id=str(uuid4()),
            product_id=product_id,
            user_id=user_id,
            guest_id=guest_id,
            status='queued',
            visibility_cutoff=visibility_cutoff,
        )
        db.session.add(rep)
        db.session.commit()
        return rep

    def mark_running(self):
        self.status = 'running'
        self.started_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def mark_partial(self):
        self.status = 'partial_ready'
        db.session.add(self)
        db.session.commit()

    def mark_complete(self):
        self.status = 'complete'
        self.completed_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def mark_failed(self, message: str):
        try:
            db.session.rollback()
        except Exception:
            pass
        self.status = 'failed'
        self.error_message = message
        db.session.add(self)
        db.session.commit()
