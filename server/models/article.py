from .db_utils import db
from uuid import uuid4


class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.String(100), primary_key=True)
    report_id = db.Column(db.String(100), db.ForeignKey('reports.id'), nullable=False, index=True)
    suggestion_id = db.Column(db.String(100), db.ForeignKey('suggestions.id'), nullable=True)
    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=True)
    content_html = db.Column(db.Text, nullable=True)
    content_md = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='generating')  # generating|ready|failed
    error_message = db.Column(db.Text, nullable=True)
    model_used = db.Column(db.String(50), nullable=True)
    tokens_used = db.Column(db.Integer, nullable=True)

    report = db.relationship('Report', backref=db.backref('articles', lazy=True))

    @classmethod
    def create(cls, report_id: str, title: str, description: str | None = None, suggestion_id: str | None = None):
        rec = Article(
            id=str(uuid4()),
            report_id=report_id,
            suggestion_id=suggestion_id,
            title=title,
            description=description,
            status='generating',
        )
        db.session.add(rec)
        db.session.commit()
        return rec
