import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, StrEnum, Timestamps, UUIDPk
from app.models.enums import (
    DeliveryStatus,
    DisputeReason,
    DisputeStatus,
    EscrowStatus,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    RefundStatus,
)


class Order(UUIDPk, Timestamps, Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal > 0", name="subtotal_positive"),
        CheckConstraint("delivery_fee >= 0", name="delivery_fee_non_negative"),
        CheckConstraint("protection_fee >= 0", name="protection_fee_non_negative"),
        CheckConstraint("total = subtotal + delivery_fee + protection_fee", name="total_consistent"),
        Index("ix_orders_buyer_created", "buyer_id", "created_at"),
        Index("ix_orders_seller_created", "seller_id", "created_at"),
        UniqueConstraint("buyer_id", "idempotency_key", name="buyer_idem"),
        # An accepted offer can back at most one non-cancelled order.
        Index("uq_orders_negotiation_live", "negotiation_id", unique=True,
              postgresql_where="negotiation_id IS NOT NULL AND status <> 'cancelled'"),
    )

    order_number: Mapped[str] = mapped_column(String(20), unique=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seller_profiles.id"))
    negotiation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("negotiations.id"), index=True
    )
    status: Mapped[EscrowStatus] = mapped_column(
        StrEnum(EscrowStatus), default=EscrowStatus.PENDING_PAYMENT, index=True
    )
    payment_method: Mapped[PaymentMethod] = mapped_column(StrEnum(PaymentMethod), default=PaymentMethod.FULL)
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    subtotal: Mapped[Decimal]
    delivery_fee: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    protection_fee: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    total: Mapped[Decimal]
    commission_rate: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    delivery_option: Mapped[dict] = mapped_column(JSONB, default=dict)
    delivery_address: Mapped[dict] = mapped_column(JSONB, default=dict)
    buyer_note: Mapped[str | None] = mapped_column(String(500))
    stock_reserved: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None]
    paid_at: Mapped[datetime | None]
    completed_at: Mapped[datetime | None]
    # Ads measurement: did the buyer accept marketing cookies at checkout? Server-side purchase events
    # (Meta Conversions API) are only ever sent for orders where this is true.
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    capi_sent_at: Mapped[datetime | None]
    cancelled_at: Mapped[datetime | None]
    cancellation_reason: Mapped[str | None] = mapped_column(String(300))
    # Client-supplied key making checkout creation idempotent per buyer.
    idempotency_key: Mapped[str | None] = mapped_column(String(80))

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    escrow: Mapped["EscrowTransaction"] = relationship(back_populates="order", uselist=False)
    delivery: Mapped["DeliveryRecord"] = relationship(back_populates="order", uselist=False)
    seller = relationship("SellerProfile")
    buyer = relationship("User")


class OrderItem(UUIDPk, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("unit_price > 0", name="unit_price_positive"),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"), index=True)
    title: Mapped[str] = mapped_column(String(140))  # snapshot
    image_url: Mapped[str | None] = mapped_column(String(500))
    unit_price: Mapped[Decimal]
    listed_price: Mapped[Decimal]
    quantity: Mapped[int] = mapped_column(Integer)
    line_total: Mapped[Decimal]

    order: Mapped[Order] = relationship(back_populates="items")


class Payment(UUIDPk, Timestamps, Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("amount_refunded >= 0 AND amount_refunded <= amount", name="refund_bounds"),
    )

    reference: Mapped[str] = mapped_column(String(64), unique=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_reference: Mapped[str | None] = mapped_column(String(120), index=True)
    purpose: Mapped[PaymentPurpose] = mapped_column(StrEnum(PaymentPurpose))
    status: Mapped[PaymentStatus] = mapped_column(
        StrEnum(PaymentStatus), default=PaymentStatus.INITIALIZED, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), index=True
    )
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    installment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    bnpl_application_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    amount: Mapped[Decimal]
    amount_refunded: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    channel: Mapped[str | None] = mapped_column(String(30))
    authorization_url: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None]
    failure_reason: Mapped[str | None] = mapped_column(String(300))
    # Raw provider payloads, internal only (never returned to clients).
    provider_data: Mapped[dict] = mapped_column(JSONB, default=dict)


class WebhookEvent(UUIDPk, Base):
    """Every inbound webhook is recorded; (provider, event_key) uniqueness gives idempotency."""

    __tablename__ = "webhook_events"
    __table_args__ = (UniqueConstraint("provider", "event_key", name="provider_event"),)

    provider: Mapped[str] = mapped_column(String(30))
    event_key: Mapped[str] = mapped_column(String(200))
    event_type: Mapped[str] = mapped_column(String(80))
    signature_valid: Mapped[bool] = mapped_column(Boolean)
    payload: Mapped[dict] = mapped_column(JSONB)
    processed_at: Mapped[datetime | None]
    processing_error: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(default=utcnow)


class EscrowTransaction(UUIDPk, Timestamps, Base):
    __tablename__ = "escrow_transactions"
    __table_args__ = (CheckConstraint("amount = seller_amount + platform_amount", name="split_consistent"),)

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_escrow_ref: Mapped[str | None] = mapped_column(String(120), unique=True)
    status: Mapped[EscrowStatus] = mapped_column(
        StrEnum(EscrowStatus), default=EscrowStatus.PENDING_PAYMENT, index=True
    )
    amount: Mapped[Decimal]  # total held
    seller_amount: Mapped[Decimal]
    platform_amount: Mapped[Decimal]  # commission + protection fee
    funded_at: Mapped[datetime | None]
    release_eligible_at: Mapped[datetime | None]  # auto-release time if buyer silent
    released_at: Mapped[datetime | None]
    refunded_at: Mapped[datetime | None]
    version: Mapped[int] = mapped_column(Integer, default=1)

    order: Mapped[Order] = relationship(back_populates="escrow")
    events: Mapped[list["EscrowEvent"]] = relationship(order_by="EscrowEvent.created_at")

    __mapper_args__ = {"version_id_col": version}


class EscrowEvent(UUIDPk, Base):
    """Append-only status history. Protected from UPDATE/DELETE by a database trigger."""

    __tablename__ = "escrow_events"

    escrow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("escrow_transactions.id"), index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    actor_role: Mapped[str] = mapped_column(String(20))  # buyer | seller | admin | system | provider
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class DeliveryRecord(UUIDPk, Timestamps, Base):
    __tablename__ = "delivery_records"

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), unique=True)
    status: Mapped[DeliveryStatus] = mapped_column(StrEnum(DeliveryStatus), default=DeliveryStatus.PENDING)
    method: Mapped[str] = mapped_column(String(30))
    carrier: Mapped[str | None] = mapped_column(String(80))
    tracking_reference: Mapped[str | None] = mapped_column(String(120))
    tracking_url: Mapped[str | None] = mapped_column(String(500))
    evidence_urls: Mapped[list] = mapped_column(JSONB, default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    dispatched_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]
    updates: Mapped[list] = mapped_column(JSONB, default=list)  # [{at, status, note}]

    order: Mapped[Order] = relationship(back_populates="delivery")


class Refund(UUIDPk, Timestamps, Base):
    __tablename__ = "refunds"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        # Only one refund in flight or completed per order (duplicate-refund guard).
        Index(
            "uq_refunds_active_per_order",
            "order_id",
            unique=True,
            postgresql_where="status NOT IN ('rejected', 'failed')",
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), index=True)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"))
    dispute_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("disputes.id"))
    amount: Mapped[Decimal]
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[RefundStatus] = mapped_column(StrEnum(RefundStatus), default=RefundStatus.PENDING_APPROVAL)
    requested_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[datetime | None]
    provider_refund_ref: Mapped[str | None] = mapped_column(String(120))
    completed_at: Mapped[datetime | None]
    failure_reason: Mapped[str | None] = mapped_column(String(300))


class Dispute(UUIDPk, Timestamps, Base):
    __tablename__ = "disputes"
    __table_args__ = (
        Index(
            "uq_disputes_open_per_order",
            "order_id",
            unique=True,
            postgresql_where="status IN ('open', 'under_review')",
        ),
    )

    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), index=True)
    opened_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    opened_by_role: Mapped[str] = mapped_column(String(10))  # buyer | seller
    reason: Mapped[DisputeReason] = mapped_column(StrEnum(DisputeReason))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[DisputeStatus] = mapped_column(
        StrEnum(DisputeStatus), default=DisputeStatus.OPEN, index=True
    )
    previous_order_status: Mapped[str] = mapped_column(String(40))
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None]

    messages: Mapped[list["DisputeMessage"]] = relationship(order_by="DisputeMessage.created_at")
    order = relationship("Order")


class DisputeMessage(UUIDPk, Base):
    __tablename__ = "dispute_messages"

    dispute_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("disputes.id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    author_role: Mapped[str] = mapped_column(String(10))
    body: Mapped[str] = mapped_column(Text)
    evidence_urls: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
