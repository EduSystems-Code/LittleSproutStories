"""add fulfillments.printify_order_id

Revision ID: 2b1f4c7a9d02
Revises: 1e08de9e02dc
Create Date: 2026-08-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b1f4c7a9d02'
down_revision = '1e08de9e02dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('fulfillments', sa.Column('printify_order_id', sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column('fulfillments', 'printify_order_id')
