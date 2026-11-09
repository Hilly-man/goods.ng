"""listing promotions

Revision ID: 5f7a9b1c2d3e
Revises: 3283422a72e2
Create Date: 2026-11-07 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f7a9b1c2d3e'
down_revision: Union[str, Sequence[str], None] = '3283422a72e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('products', sa.Column('promoted_tier', sa.String(length=20), nullable=True))
    op.add_column('promotions', sa.Column('package_code', sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('promotions', 'package_code')
    op.drop_column('products', 'promoted_tier')
