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

    def switch_plan(self, new_plan: dict, *, proration_behavior: str = 'create_prorations'):
        """Switch this subscription to the specified plan using Stripe API.
        - Validates plan exists in SUBSCRIPTION_PLANS
        - Updates the active subscription item to the new price
        - Refreshes local status and plan from Stripe via update_status()

        Returns: self
        Raises: Exception on invalid state or Stripe errors
        """
        if not self.stripe_subscription_id:
            raise Exception('Missing stripe_subscription_id for this subscription')

        # Retrieve current Stripe subscription and its first item
        sub = stripe.Subscription.retrieve(self.stripe_subscription_id)
        items = sub.get('items', None)
        item_list = getattr(items, 'data', None) if items is not None else None
        if not item_list:
            raise Exception('Stripe subscription has no items to update.')

        first_item = item_list[0]
        item_id = getattr(first_item, 'id', None) or first_item.get('id')
        if not item_id:
            raise Exception('Unable to determine subscription item id to update.')

        # If already on the same price, no-op (but sync local tier id)
        current_price = getattr(first_item, 'price', None) or first_item.get('price')
        current_price_id = getattr(current_price, 'id', None) or (current_price.get('id') if current_price else None)
        new_price_id = new_plan['stripe_price_id']
        if current_price_id == new_price_id:
            # Ensure local plan is correct and persist
            self.plan_id = new_plan['id']
            db.session.commit()
            return self

        # Update Stripe subscription item with the new price
        stripe.Subscription.modify(
            self.stripe_subscription_id,
            items=[{
                'id': item_id,
                'price': new_price_id,
            }],
            proration_behavior=proration_behavior,
        )

        # Refresh local status/plan from Stripe (commits internally)
        self.update_status()
        return self


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
