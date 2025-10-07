from .db_utils import db
from uuid import uuid4


class Meme(db.Model):
    __tablename__ = 'memes'
    id = db.Column(db.String(100), primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey('reports.id'), nullable=False, index=True)
    suggestion_id = db.Column(db.String(100), db.ForeignKey('suggestions.id'), nullable=True, index=True)
    concept = db.Column(db.String(500), nullable=True)
    instructions_json = db.Column(db.Text, nullable=True)  # JSON string with generation instructions
    # Deprecated: base64-encoded image data (PNG)
    image_b64 = db.Column(db.Text, nullable=True)
    # Preferred: raw PNG bytes
    image_bytes = db.Column(db.LargeBinary, nullable=True)
    # Preferred approach now: save to disk and store relative path under static/
    image_path = db.Column(db.String(300), nullable=True)
    status = db.Column(db.String(20), default='generating')  # generating|ready|failed
    error_message = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)
    created_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_on = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    report = db.relationship('Report', backref=db.backref('memes', lazy=True))

    @classmethod
    def create(cls, report_id: str, suggestion_id: str | None = None, concept: str | None = None, instructions_json: str | None = None):
        rec = Meme(
            id=str(uuid4()),
            report_id=report_id,
            suggestion_id=suggestion_id,
            concept=concept,
            instructions_json=instructions_json,
            status='generating',
        )
        db.session.add(rec)
        db.session.commit()
        return rec
