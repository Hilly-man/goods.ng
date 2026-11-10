"""link wallet holds to Goods Flex instalments

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-11-10 20:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: str | Sequence[str] | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('wallet_holds', sa.Column('installment_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_wallet_holds_installment_id'), 'wallet_holds', ['installment_id'])
    op.create_foreign_key(op.f('fk_wallet_holds_installment_id_installments'), 'wallet_holds', 'installments',
                          ['installment_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint(op.f('fk_wallet_holds_installment_id_installments'), 'wallet_holds', type_='foreignkey')
    op.drop_index(op.f('ix_wallet_holds_installment_id'), table_name='wallet_holds')
    op.drop_column('wallet_holds', 'installment_id')
