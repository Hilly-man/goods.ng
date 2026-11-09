"""outbound email templates

Revision ID: 56c8854d3d50
Revises: 5f7a9b1c2d3e
Create Date: 2026-11-09 17:13:58.558786

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '56c8854d3d50'
down_revision: str | Sequence[str] | None = '5f7a9b1c2d3e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('outbound_messages', sa.Column('event_type', sa.String(length=40), nullable=True))
    op.add_column('outbound_messages', sa.Column('html', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('outbound_messages', 'html')
    op.drop_column('outbound_messages', 'event_type')
