"""add memes table

Revision ID: add_memes_table_20251008
Revises: 
Create Date: 2025-10-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_memes_table_20251008'
down_revision = 'd9db3a932297'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'memes',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('report_id', sa.String(length=100), sa.ForeignKey('reports.id'), nullable=False, index=True),
        sa.Column('suggestion_id', sa.String(length=100), sa.ForeignKey('suggestions.id'), nullable=True, index=True),
        sa.Column('concept', sa.String(length=500), nullable=True),
        sa.Column('instructions_json', sa.Text(), nullable=True),
        sa.Column('image_b64', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='generating'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('created_on', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_on', sa.DateTime(), server_default=sa.func.current_timestamp()),
    )


def downgrade():
    op.drop_table('memes')
