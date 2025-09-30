from .db_utils import db
from uuid import uuid4


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'), nullable=True, index=True)
    guest_id = db.Column(db.String(100), nullable=True, index=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_on = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    user = db.relationship('User', backref=db.backref('products', lazy=True))

    @classmethod
    def create(cls, name: str, description: str, user_id=None, guest_id=None):
        prod = Product(
            id=str(uuid4()),
            name=name.strip(),
            description=description.strip(),
            user_id=user_id,
            guest_id=guest_id,
        )
        db.session.add(prod)
        db.session.commit()
        return prod
