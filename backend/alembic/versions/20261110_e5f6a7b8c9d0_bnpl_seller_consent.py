"""record Goods Flex seller terms acceptance per listing

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-11-10 21:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: str | Sequence[str] | None = 'd4e5f6a7b8c9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('products', sa.Column('bnpl_terms_version', sa.String(length=20), nullable=True))
    op.add_column('products', sa.Column('bnpl_terms_accepted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('products', 'bnpl_terms_accepted_at')
    op.drop_column('products', 'bnpl_terms_version')
