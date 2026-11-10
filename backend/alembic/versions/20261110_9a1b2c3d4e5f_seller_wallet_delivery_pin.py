"""seller wallet, payouts and delivery PIN

Revision ID: 9a1b2c3d4e5f
Revises: 56c8854d3d50
Create Date: 2026-11-10 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '9a1b2c3d4e5f'
down_revision: str | Sequence[str] | None = '56c8854d3d50'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYOUT_STATUSES = ("requested", "processing", "paid", "failed", "cancelled")


def upgrade() -> None:
    op.add_column('seller_profiles', sa.Column('payouts_frozen', sa.Boolean(), nullable=False,
                                               server_default=sa.text('false')))
    op.add_column('delivery_records', sa.Column('pin_enc', sa.Text(), nullable=True))
    op.add_column('delivery_records', sa.Column('pin_attempts', sa.Integer(), nullable=False,
                                                server_default=sa.text('0')))
    op.add_column('delivery_records', sa.Column('pin_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('delivery_records', sa.Column('pin_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('delivery_records', sa.Column('provider', sa.String(length=30), nullable=True))
    op.add_column('delivery_records', sa.Column('provider_reference', sa.String(length=120), nullable=True))
    op.create_index(op.f('ix_delivery_records_provider_reference'), 'delivery_records', ['provider_reference'])

    op.create_table(
        'seller_bank_accounts',
        sa.Column('seller_id', sa.UUID(), nullable=False),
        sa.Column('bank_code', sa.String(length=10), nullable=False),
        sa.Column('bank_name', sa.String(length=80), nullable=False),
        sa.Column('account_number_enc', sa.Text(), nullable=False),
        sa.Column('account_number_last4', sa.String(length=4), nullable=False),
        sa.Column('account_name', sa.String(length=120), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['seller_id'], ['seller_profiles.id'], name=op.f('fk_seller_bank_accounts_seller_id_seller_profiles'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_seller_bank_accounts')),
    )
    op.create_index(op.f('ix_seller_bank_accounts_seller_id'), 'seller_bank_accounts', ['seller_id'])
    op.create_index('ix_seller_bank_accounts_seller', 'seller_bank_accounts', ['seller_id', 'created_at'])

    op.create_table(
        'payouts',
        sa.Column('seller_id', sa.UUID(), nullable=False),
        sa.Column('bank_account_id', sa.UUID(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('fee', sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text('0')),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='requested'),
        sa.Column('provider', sa.String(length=30), nullable=True),
        sa.Column('provider_reference', sa.String(length=120), nullable=True),
        sa.Column('idempotency_key', sa.String(length=80), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processing_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_reason', sa.String(length=300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.CheckConstraint('amount > 0', name=op.f('ck_payouts_amount_positive')),
        sa.CheckConstraint('fee >= 0', name=op.f('ck_payouts_fee_non_negative')),
        sa.CheckConstraint("status IN ('requested','processing','paid','failed','cancelled')", name=op.f('ck_payouts_status')),
        sa.ForeignKeyConstraint(['bank_account_id'], ['seller_bank_accounts.id'], name=op.f('fk_payouts_bank_account_id_seller_bank_accounts'), ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['seller_id'], ['seller_profiles.id'], name=op.f('fk_payouts_seller_id_seller_profiles'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_payouts')),
        sa.UniqueConstraint('idempotency_key', name=op.f('uq_payouts_idempotency_key')),
    )
    op.create_index(op.f('ix_payouts_seller_id'), 'payouts', ['seller_id'])
    op.create_index(op.f('ix_payouts_status'), 'payouts', ['status'])
    op.create_index(op.f('ix_payouts_provider_reference'), 'payouts', ['provider_reference'])
    op.create_index('ix_payouts_seller_created', 'payouts', ['seller_id', 'created_at'])
    op.create_index('ix_payouts_status_created', 'payouts', ['status', 'created_at'])

    op.create_table(
        'wallet_holds',
        sa.Column('seller_id', sa.UUID(), nullable=False),
        sa.Column('order_id', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=40), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.CheckConstraint('amount > 0', name=op.f('ck_wallet_holds_amount_positive')),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], name=op.f('fk_wallet_holds_created_by_id_users')),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name=op.f('fk_wallet_holds_order_id_orders')),
        sa.ForeignKeyConstraint(['seller_id'], ['seller_profiles.id'], name=op.f('fk_wallet_holds_seller_id_seller_profiles'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_wallet_holds')),
    )
    op.create_index(op.f('ix_wallet_holds_seller_id'), 'wallet_holds', ['seller_id'])
    op.create_index(op.f('ix_wallet_holds_order_id'), 'wallet_holds', ['order_id'])
    op.create_index('ix_wallet_holds_seller_open', 'wallet_holds', ['seller_id', 'released_at'])


def downgrade() -> None:
    op.drop_index('ix_wallet_holds_seller_open', table_name='wallet_holds')
    op.drop_index(op.f('ix_wallet_holds_order_id'), table_name='wallet_holds')
    op.drop_index(op.f('ix_wallet_holds_seller_id'), table_name='wallet_holds')
    op.drop_table('wallet_holds')

    op.drop_index('ix_payouts_status_created', table_name='payouts')
    op.drop_index('ix_payouts_seller_created', table_name='payouts')
    op.drop_index(op.f('ix_payouts_provider_reference'), table_name='payouts')
    op.drop_index(op.f('ix_payouts_status'), table_name='payouts')
    op.drop_index(op.f('ix_payouts_seller_id'), table_name='payouts')
    op.drop_table('payouts')

    op.drop_index('ix_seller_bank_accounts_seller', table_name='seller_bank_accounts')
    op.drop_index(op.f('ix_seller_bank_accounts_seller_id'), table_name='seller_bank_accounts')
    op.drop_table('seller_bank_accounts')

    op.drop_index(op.f('ix_delivery_records_provider_reference'), table_name='delivery_records')
    op.drop_column('delivery_records', 'provider_reference')
    op.drop_column('delivery_records', 'provider')
    op.drop_column('delivery_records', 'pin_expires_at')
    op.drop_column('delivery_records', 'pin_verified_at')
    op.drop_column('delivery_records', 'pin_attempts')
    op.drop_column('delivery_records', 'pin_enc')
    op.drop_column('seller_profiles', 'payouts_frozen')
