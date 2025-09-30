from .db_utils import db
from datetime import datetime, timedelta
import calendar
from sqlalchemy import tuple_, func, or_

class CreditLedger(db.Model):
  UNIT = 1000*1000
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.String(200), index=True)
  credit = db.Column(db.Integer)
  debit = db.Column(db.Integer)
  model = db.Column(db.String(100))
  created_on = db.Column(db.DateTime(), nullable=True)

  @classmethod
  def create(cls, user_id, credit, debit, model):
    entity = CreditLedger(user_id=user_id, 
    credit=credit,
    debit=debit,
    model=model,
    created_on=datetime.now())
    db.session.add(entity)
    db.session.commit()
    return entity

  @classmethod
  def get_total_debit(cls, user_id):
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(day=calendar.monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    return db.session.query(func.sum(CreditLedger.debit)).filter_by(user_id=user_id)\
      .filter(CreditLedger.created_on >= start)\
      .filter(CreditLedger.created_on <= end)\
      .scalar() or 0

  @classmethod
  def get_total_credit(cls, user_id):
    now = datetime.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(day=calendar.monthrange(now.year, now.month)[1], hour=23, minute=59, second=59, microsecond=999999)
    return db.session.query(func.sum(CreditLedger.credit)).filter_by(user_id=user_id)\
      .filter(CreditLedger.created_on >= start)\
      .filter(CreditLedger.created_on <= end)\
      .scalar() or 0

  @classmethod
  def calculate_cost(cls, prompts, completion, model):
    if model == 'gpt-4':
      return (prompts * 0.03 * CreditLedger.UNIT ) + (completion * 0.06 * CreditLedger.UNIT)
    elif model == 'gpt-3.5-turbo':
      return (prompts * 0.002 * CreditLedger.UNIT ) + (completion * 0.002 * CreditLedger.UNIT)
    else:
      return 0