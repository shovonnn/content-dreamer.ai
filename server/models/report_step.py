from .db_utils import db
from uuid import uuid4
from datetime import datetime


class ReportStep(db.Model):
    __tablename__ = 'report_steps'
    id = db.Column(db.String(100), primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey('reports.id'), nullable=False, index=True)
    step_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='queued')  # queued|running|done|failed
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    payload_json = db.Column(db.Text, nullable=True)

    report = db.relationship('Report', backref=db.backref('steps', lazy=True))

    @classmethod
    def start(cls, report_id: str, step_name: str):
        rec = ReportStep(id=str(uuid4()), report_id=report_id, step_name=step_name, status='running', started_at=datetime.utcnow())
        db.session.add(rec)
        db.session.commit()
        return rec

    def done(self, payload_json: str | None = None):
        self.status = 'done'
        self.finished_at = datetime.utcnow()
        if payload_json is not None:
            self.payload_json = payload_json
        db.session.add(self)
        db.session.commit()

    def fail(self, message: str):
        self.status = 'failed'
        self.error_message = message
        self.finished_at = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
