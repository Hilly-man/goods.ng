"""Double-entry ledger. Independent of product/listing tables; references are opaque strings.

Rules (enforced in app.modules.ledger.service and by DB triggers in the migration):
* every LedgerTransaction has >= 2 entries and debits == credits
* entries and transactions are append-only (UPDATE/DELETE blocked by trigger)
* LedgerTransaction.idempotency_key is unique -> the same settlement can never post twice
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, StrEnum, UUIDPk
from app.models.enums import EntryDirection, LedgerAccountType


class LedgerAccount(UUIDPk, Base):
    __tablename__ = "ledger_accounts"

    code: Mapped[str] = mapped_column(String(120), unique=True)  # e.g. "liability:seller_payable:<uuid>"
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[LedgerAccountType] = mapped_column(StrEnum(LedgerAccountType))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    owner_ref: Mapped[str | None] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class LedgerTransaction(UUIDPk, Base):
    __tablename__ = "ledger_transactions"

    idempotency_key: Mapped[str] = mapped_column(String(160), unique=True)
    kind: Mapped[str] = mapped_column(String(50), index=True)  # escrow_funded, escrow_released, refund, ...
    description: Mapped[str] = mapped_column(String(300))
    reference: Mapped[str | None] = mapped_column(String(120), index=True)  # e.g. order number
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    entries: Mapped[list["LedgerEntry"]] = relationship(back_populates="transaction")


class LedgerEntry(UUIDPk, Base):
    __tablename__ = "ledger_entries"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ledger_transactions.id"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ledger_accounts.id"), index=True
    )
    direction: Mapped[EntryDirection] = mapped_column(StrEnum(EntryDirection))
    amount: Mapped[Decimal]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    transaction: Mapped[LedgerTransaction] = relationship(back_populates="entries")
    account: Mapped[LedgerAccount] = relationship()
