"""Seller wallet: bank accounts, payout requests and payout holds.

The wallet is a ledger-backed view: Goods.ng never custodies funds. Released earnings sit in
``liability:seller_payable:<seller>`` until the seller requests a payout, which is executed by the
licensed payout partner. A buyer complaint inside the clearing window freezes the affected amount
(and the seller's payouts) until an administrator resolves it.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDelete, StrEnum, Timestamps, UUIDPk
from app.models.enums import PayoutStatus


class SellerBankAccount(UUIDPk, Timestamps, SoftDelete, Base):
    __tablename__ = "seller_bank_accounts"
    __table_args__ = (Index("ix_seller_bank_accounts_seller", "seller_id", "created_at"),)

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE"), index=True
    )
    bank_code: Mapped[str] = mapped_column(String(10))
    bank_name: Mapped[str] = mapped_column(String(80))
    # Encrypted at rest; only the last four digits are returned by the API.
    account_number_enc: Mapped[str] = mapped_column(Text)
    account_number_last4: Mapped[str] = mapped_column(String(4))
    account_name: Mapped[str] = mapped_column(String(120))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None]


class Payout(UUIDPk, Timestamps, Base):
    __tablename__ = "payouts"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("fee >= 0", name="fee_non_negative"),
        Index("ix_payouts_seller_created", "seller_id", "created_at"),
        Index("ix_payouts_status_created", "status", "created_at"),
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="RESTRICT"), index=True
    )
    bank_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_bank_accounts.id", ondelete="RESTRICT")
    )
    amount: Mapped[Decimal]
    fee: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    status: Mapped[PayoutStatus] = mapped_column(StrEnum(PayoutStatus), default=PayoutStatus.REQUESTED, index=True)
    provider: Mapped[str | None] = mapped_column(String(30))
    provider_reference: Mapped[str | None] = mapped_column(String(120), index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(80), unique=True)
    requested_at: Mapped[datetime]
    processing_at: Mapped[datetime | None]
    paid_at: Mapped[datetime | None]
    failed_at: Mapped[datetime | None]
    failure_reason: Mapped[str | None] = mapped_column(String(300))

    bank_account = relationship("SellerBankAccount")


class WalletHold(UUIDPk, Timestamps, Base):
    __tablename__ = "wallet_holds"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        Index("ix_wallet_holds_seller_open", "seller_id", "released_at"),
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), index=True)
    amount: Mapped[Decimal]
    reason: Mapped[str] = mapped_column(String(40))  # dispute | post_delivery_claim | manual | reserve
    note: Mapped[str | None] = mapped_column(Text)
    released_at: Mapped[datetime | None]
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
