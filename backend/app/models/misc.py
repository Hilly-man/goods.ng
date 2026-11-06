import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, StrEnum, Timestamps, UUIDPk
from app.models.enums import BnplStatus, InstallmentStatus, ReportStatus, ReviewStatus


# ---------------- Reviews ----------------
class Review(UUIDPk, Timestamps, Base):
    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),
        # One review per completed order (manipulation guard).
        UniqueConstraint("order_id", name="one_per_order"),
        # Unverified (no-order) reviews: one per reviewer per seller.
        Index("uq_reviews_unverified_per_seller", "reviewer_id", "seller_id", unique=True,
              postgresql_where="order_id IS NULL"),
        Index("ix_reviews_seller_status", "seller_id", "status"),
    )

    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seller_profiles.id"))
    reviewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    title: Mapped[str | None] = mapped_column(String(120))
    comment: Mapped[str | None] = mapped_column(Text)
    is_verified_purchase: Mapped[bool] = mapped_column(default=False)
    status: Mapped[ReviewStatus] = mapped_column(StrEnum(ReviewStatus), default=ReviewStatus.PUBLISHED)
    seller_reply: Mapped[str | None] = mapped_column(Text)
    moderation_note: Mapped[str | None] = mapped_column(String(300))

    reviewer = relationship("User")


class ReviewReport(UUIDPk, Base):
    __tablename__ = "review_reports"
    __table_args__ = (UniqueConstraint("review_id", "reporter_id"),)

    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("reviews.id", ondelete="CASCADE")
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[ReportStatus] = mapped_column(StrEnum(ReportStatus), default=ReportStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# ---------------- BNPL (Goods Flex) ----------------
class BnplApplication(UUIDPk, Timestamps, Base):
    __tablename__ = "bnpl_applications"
    __table_args__ = (
        # One running Goods Flex plan per customer, enforced by the database (race-proof).
        Index("uq_bnpl_one_running_plan", "user_id", unique=True,
              postgresql_where="status IN ('approved', 'accepted', 'active', 'defaulted')"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), unique=True
    )
    negotiation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("negotiations.id")
    )
    provider: Mapped[str] = mapped_column(String(30))
    provider_application_ref: Mapped[str | None] = mapped_column(String(120), unique=True)
    credit_decision_ref: Mapped[str | None] = mapped_column(String(120))
    purchase_amount: Mapped[Decimal]
    tenor_months: Mapped[int] = mapped_column(Integer)
    status: Mapped[BnplStatus] = mapped_column(StrEnum(BnplStatus), default=BnplStatus.SUBMITTED, index=True)
    decline_reason: Mapped[str | None] = mapped_column(String(300))
    monthly_income_declared: Mapped[Decimal | None]
    employment_status: Mapped[str | None] = mapped_column(String(40))
    # Partner-provided offer (down payment, charges, schedule). Displayed verbatim before acceptance.
    offer_terms: Mapped[dict] = mapped_column(JSONB, default=dict)
    offer_expires_at: Mapped[datetime | None]
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("credit_assessments.id"))
    credit_limit_at_application: Mapped[Decimal | None]

    agreement: Mapped["FinancingAgreement"] = relationship(back_populates="application", uselist=False)


class FinancingAgreement(UUIDPk, Timestamps, Base):
    __tablename__ = "financing_agreements"
    __table_args__ = (
        CheckConstraint("total_payable = down_payment + financed_amount + financing_charge", name="totals"),
    )

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bnpl_applications.id"), unique=True
    )
    provider_agreement_ref: Mapped[str] = mapped_column(String(120), unique=True)
    purchase_amount: Mapped[Decimal]
    down_payment: Mapped[Decimal]
    financed_amount: Mapped[Decimal]
    financing_charge: Mapped[Decimal]
    total_payable: Mapped[Decimal]
    tenor_months: Mapped[int] = mapped_column(Integer)
    terms_snapshot: Mapped[dict] = mapped_column(JSONB)  # exactly what the buyer accepted
    accepted_at: Mapped[datetime]
    accepted_ip: Mapped[str | None] = mapped_column(String(64))
    outstanding_balance: Mapped[Decimal]
    status: Mapped[BnplStatus] = mapped_column(StrEnum(BnplStatus), default=BnplStatus.ACCEPTED)

    application: Mapped[BnplApplication] = relationship(back_populates="agreement")
    installments: Mapped[list["Installment"]] = relationship(order_by="Installment.sequence")


class Installment(UUIDPk, Base):
    __tablename__ = "installments"
    __table_args__ = (
        UniqueConstraint("agreement_id", "sequence"),
        CheckConstraint("amount > 0", name="amount_positive"),
    )

    agreement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("financing_agreements.id"), index=True
    )
    sequence: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal]
    amount_paid: Mapped[Decimal] = mapped_column(default=Decimal("0"))
    status: Mapped[InstallmentStatus] = mapped_column(
        StrEnum(InstallmentStatus), default=InstallmentStatus.SCHEDULED
    )
    paid_at: Mapped[datetime | None]
    reminder_sent_at: Mapped[datetime | None]


class Repayment(UUIDPk, Base):
    __tablename__ = "repayments"

    installment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("installments.id"), index=True
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"), unique=True)
    amount: Mapped[Decimal]
    status: Mapped[str] = mapped_column(String(20))  # success | failed
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


# ---------------- Notifications ----------------
class Notification(UUIDPk, Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(500))
    link: Mapped[str | None] = mapped_column(String(300))
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class OutboundMessage(UUIDPk, Base):
    """Outbox for email/SMS/push; drained by the background worker with retries."""

    __tablename__ = "outbound_messages"
    __table_args__ = (Index("ix_outbound_pending", "status", "next_attempt_at"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    channel: Mapped[str] = mapped_column(String(10))  # email | sms | push
    recipient: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(15), default="pending")  # pending | sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    next_attempt_at: Mapped[datetime]
    last_error: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    sent_at: Mapped[datetime | None]


# ---------------- Reports, audit, settings ----------------
class Report(UUIDPk, Timestamps, Base):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_target", "target_type", "target_id"),)

    reporter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(20))  # product | seller | user | message | review
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    reason: Mapped[str] = mapped_column(String(60))
    details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportStatus] = mapped_column(StrEnum(ReportStatus), default=ReportStatus.OPEN, index=True)
    handled_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    resolution: Mapped[str | None] = mapped_column(String(300))


class AdminAuditLog(UUIDPk, Base):
    """Append-only; protected from UPDATE/DELETE by a database trigger."""

    __tablename__ = "admin_audit_logs"
    __table_args__ = (
        Index("ix_audit_created", "created_at"),
        Index("ix_audit_target", "target_type", "target_id"),
        Index("ix_audit_actor_created", "actor_id", "created_at"),
        Index("ix_audit_category_created", "category", "created_at"),
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80))
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(80))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    ip: Mapped[str | None] = mapped_column(String(64))
    # action = a deliberate admin operation · auth = sign-in/out & 2FA · view = console page viewed
    # api = safety-net record of an admin write that didn't log itself (incl. refused attempts)
    category: Mapped[str] = mapped_column(String(16), default="action", server_default="action")
    outcome: Mapped[str] = mapped_column(String(16), default="success", server_default="success")  # success|denied|failed
    user_agent: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))


class MockProviderRecord(UUIDPk, Base):
    """DEVELOPMENT/TEST ONLY. State store for the mock payment/escrow/financing providers.

    Simulates what a real provider would hold on its side, so that our server-side verification
    path is exercised exactly as with a real provider. Never used when real providers are configured.
    """

    __tablename__ = "mock_provider_records"
    __table_args__ = (UniqueConstraint("kind", "reference"),)

    kind: Mapped[str] = mapped_column(String(20))  # payment | escrow | refund | bnpl
    reference: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30))
    amount: Mapped[Decimal]
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow)


class City(UUIDPk, Base):
    """Cities/towns/areas per Nigerian state; drives state → city dropdowns and server-side validation."""

    __tablename__ = "cities"
    __table_args__ = (UniqueConstraint("state", "name", name="state_name"), Index("ix_cities_state", "state"))

    state: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class InterestSignal(UUIDPk, Base):
    """A first-party interest signal used for "Recommended for you".

    kind: search (searched on Goods.ng) | view (opened a listing) | landing (arrived from an external site).
    source: goods | google | bing | yahoo | duckduckgo | facebook | instagram | tiktok | x | whatsapp | youtube | other.
    For landings we only ever store what the visitor's own click carried to us (referrer domain, UTM/ad keyword,
    the page they landed on) — never anything read from another site. Rows older than 90 days are purged.
    """

    __tablename__ = "interest_signals"
    __table_args__ = (
        Index("ix_interest_user_created", "user_id", "created_at"),
        Index("ix_interest_anon_created", "anon_id", "created_at"),
        Index("ix_interest_created", "created_at"),
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    anon_id: Mapped[str | None] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(20), default="goods")
    query: Mapped[str | None] = mapped_column(String(120))
    campaign: Mapped[str | None] = mapped_column(String(120))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AdEvent(UUIDPk, Base):
    """Sponsored-placement analytics: impression | click | bump. Viewer is a user id or anonymous id (no PII)."""

    __tablename__ = "ad_events"
    __table_args__ = (
        Index("ix_ad_events_seller_created", "seller_id", "created_at"),
        Index("ix_ad_events_product_kind_created", "product_id", "kind", "created_at"),
    )

    kind: Mapped[str] = mapped_column(String(12))  # impression | click | bump
    placement: Mapped[str] = mapped_column(String(16))  # search | category | item | for_you | home | seller
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("seller_profiles.id", ondelete="CASCADE"))
    viewer: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
