"""add video_gen_count to usage_quotas

Revision ID: add_video_gen_count_20251008
Revises: add_slops_table_20251008
Create Date: 2025-10-08 02:12:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_video_gen_count_20251008'
down_revision = 'add_slops_table_20251008'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('usage_quotas', schema=None) as batch_op:
        batch_op.add_column(sa.Column('video_gen_count', sa.Integer(), nullable=True))



def downgrade():
    with op.batch_alter_table('usage_quotas', schema=None) as batch_op:
        batch_op.drop_column('video_gen_count')
