"""add image_path to memes

Revision ID: add_memes_image_path_20251008
Revises: add_memes_image_bytes_20251008
Create Date: 2025-10-08 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_memes_image_path_20251008'
down_revision = 'add_memes_image_bytes_20251008'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('memes', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_path', sa.String(length=300), nullable=True))


def downgrade():
    with op.batch_alter_table('memes', schema=None) as batch_op:
        batch_op.drop_column('image_path')
