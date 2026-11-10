"""payout review/approval

Revision ID: 7c8d9e0f1a2b
Revises: 9a1b2c3d4e5f
Create Date: 2026-11-10 14:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '7c8d9e0f1a2b'
down_revision: str | Sequence[str] | None = '9a1b2c3d4e5f'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD = "status IN ('requested','processing','paid','failed','cancelled')"
NEW = "status IN ('requested','approved','processing','paid','failed','rejected','cancelled')"


def upgrade() -> None:
    op.add_column('payouts', sa.Column('reviewed_by_id', sa.UUID(), nullable=True))
    op.add_column('payouts', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('payouts', sa.Column('review_note', sa.String(length=300), nullable=True))
    op.create_foreign_key(op.f('fk_payouts_reviewed_by_id_users'), 'payouts', 'users',
                          ['reviewed_by_id'], ['id'])
    op.drop_constraint(op.f('ck_payouts_status'), 'payouts', type_='check')
    op.create_check_constraint(op.f('ck_payouts_status'), 'payouts', NEW)


def downgrade() -> None:
    op.drop_constraint(op.f('ck_payouts_status'), 'payouts', type_='check')
    op.create_check_constraint(op.f('ck_payouts_status'), 'payouts', OLD)
    op.drop_constraint(op.f('fk_payouts_reviewed_by_id_users'), 'payouts', type_='foreignkey')
    op.drop_column('payouts', 'review_note')
    op.drop_column('payouts', 'reviewed_at')
    op.drop_column('payouts', 'reviewed_by_id')
