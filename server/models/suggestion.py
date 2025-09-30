from .db_utils import db
from uuid import uuid4


class Suggestion(db.Model):
    __tablename__ = 'suggestions'
    id = db.Column(db.String(100), primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey('reports.id'), nullable=False, index=True)
    source_type = db.Column(db.String(50), nullable=False)  # trending_topic|kw_g1|kw_g2|medium_tag
    kind = db.Column(db.String(50), nullable=False)  # article_headline|tweet|tweet_reply
    text = db.Column(db.Text, nullable=False)
    rank = db.Column(db.Float, default=0.0)
    meta_json = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(20), default='subscriber')  # guest|subscriber

    report = db.relationship('Report', backref=db.backref('suggestions', lazy=True))

    @classmethod
    def add(cls, report_id: str, source_type: str, kind: str, text: str, rank: float = 0.0, meta_json: str | None = None, visibility: str = 'subscriber'):
        rec = Suggestion(
            id=str(uuid4()),
            report_id=report_id,
            source_type=source_type,
            kind=kind,
            text=text,
            rank=rank,
            meta_json=meta_json,
            visibility=visibility,
        )
        db.session.add(rec)
        db.session.commit()
        return rec
