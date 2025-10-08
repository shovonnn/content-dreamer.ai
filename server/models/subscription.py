import stripe
from .db_utils import db
from uuid import uuid4


class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    id = db.Column(db.String(50), primary_key=True)  # basic|pro|advanced
    price_usd = db.Column(db.Integer, nullable=False)
    stripe_price_id = db.Column(db.String(200), nullable=True)
    limits_json = db.Column(db.Text, nullable=False)  # json string of limits
    active = db.Column(db.Boolean, default=True)


class UserSubscription(db.Model):
    __tablename__ = 'user_subscriptions'
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'), nullable=False, index=True)
    plan_id = db.Column(db.String(50), nullable=False)
    stripe_customer_id = db.Column(db.String(200), nullable=True)
    stripe_subscription_id = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(20), default='active')  # active|past_due|canceled
    current_period_start = db.Column(db.DateTime, nullable=True)
    current_period_end = db.Column(db.DateTime, nullable=True)

    user = db.relationship('User', backref=db.backref('subscriptions', lazy=True))

    @classmethod
    def create(cls, user_id: str, plan_id: str, status: str = 'active'):
        rec = UserSubscription(id=str(uuid4()), user_id=user_id, plan_id=plan_id, status=status)
        db.session.add(rec)
        db.session.commit()
        return rec

    def update_status(self):
        subscription_obj = stripe.Subscription.retrieve(self.stripe_subscription_id)
        self.status = subscription_obj.status
        db.session.commit()


class UsageQuota(db.Model):
    __tablename__ = 'usage_quotas'
    id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(100), db.ForeignKey('user.id'), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, index=True)
    product_count = db.Column(db.Integer, default=0)
    content_gen_count = db.Column(db.Integer, default=0)
    article_gen_count = db.Column(db.Integer, default=0)
    video_gen_count = db.Column(db.Integer, default=0)

    user = db.relationship('User', backref=db.backref('usage_quotas', lazy=True))

    @classmethod
    def get_or_create(cls, user_id, date):
        rec = UsageQuota.query.filter_by(user_id=user_id, date=date).first()
        if not rec:
            rec = UsageQuota(id=str(uuid4()), user_id=user_id, date=date)
            db.session.add(rec)
            db.session.commit()
        return rec
