"""add board_post moderation fields

Revision ID: 4f7a1c9e5b3d
Revises: 2b1f4c7a9d02
Create Date: 2026-09-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f7a1c9e5b3d'
down_revision = '2b1f4c7a9d02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('board_posts', sa.Column('submitter_ip', sa.String(length=64), nullable=True))
    op.add_column('board_posts', sa.Column('flagged', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('board_posts', sa.Column('flag_reason', sa.String(length=200), nullable=True))


def downgrade() -> None:
    op.drop_column('board_posts', 'flag_reason')
    op.drop_column('board_posts', 'flagged')
    op.drop_column('board_posts', 'submitter_ip')
