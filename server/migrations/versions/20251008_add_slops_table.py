"""create slops table for AI slop videos

Revision ID: add_slops_table_20251008
Revises: add_memes_image_path_20251008
Create Date: 2025-10-08 02:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_slops_table_20251008'
down_revision = 'add_memes_image_path_20251008'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'slops',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('report_id', sa.String(length=100), nullable=False),
        sa.Column('suggestion_id', sa.String(length=100), nullable=True),
        sa.Column('concept', sa.String(length=500), nullable=True),
        sa.Column('instructions_json', sa.Text(), nullable=True),
        sa.Column('video_path', sa.String(length=400), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=50), nullable=True),
        sa.Column('created_on', sa.DateTime(), nullable=True),
        sa.Column('updated_on', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_slops_report_id'), 'slops', ['report_id'], unique=False)
    op.create_index(op.f('ix_slops_suggestion_id'), 'slops', ['suggestion_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_slops_report_id'), table_name='slops')
    op.drop_index(op.f('ix_slops_suggestion_id'), table_name='slops')
    op.drop_table('slops')
