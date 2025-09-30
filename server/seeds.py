# seed_doctors.py
"""
Populate the DB with ~100 doctors, their users, reviews, consultations & prescriptions.
Run:  python seed_doctors.py
"""
from flask import (
    Blueprint,
)
import click
import random
from uuid import uuid4
from datetime import datetime, timedelta

from faker import Faker

from models.db_utils import db
from models.user import User

seed_commands = Blueprint('seeds', __name__)

fake = Faker("en_US")

def rand_datetime(within_days: int = 30) -> datetime:
    """Return a random datetime within the last `within_days` days."""
    return datetime.utcnow() - timedelta(
        days=random.randint(0, within_days),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59)
    )
