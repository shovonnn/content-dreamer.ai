from app import (
    create_app,
    db,
)
from flask_testing import (
    TestCase,
)
from models import (
    User,
)
from datetime import (
    datetime,
)
import helpers
import jwt
import json

class AppTestCase(TestCase):
    def create_app(self):
        return create_app(True)

    def create_test_user(self, renewed_token=True):
        pass

    def get_dummy_data(self):
        with open('tests/dummy_data.json') as fp:
            data = json.loads(fp.read())
        return data    

    def setUp(self):
        with self.client:
            db.create_all()

    def tearDown(self):
        with self.client:
            db.drop_all()

