import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, StrEnum, Timestamps, UUIDPk
from app.models.enums import SubscriptionStatus, VerificationLevel, VerificationStatus


class SellerProfile(UUIDPk, Timestamps, Base):
    __tablename__ = "seller_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    store_name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    banner_url: Mapped[str | None] = mapped_column(String(500))
    business_phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(80))
    address: Mapped[str | None] = mapped_column(String(300))
    business_hours: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(300))
    verification_level: Mapped[VerificationLevel] = mapped_column(
        StrEnum(VerificationLevel), default=VerificationLevel.UNVERIFIED, index=True
    )
    # Denormalised; recomputed from reviews by the review service only.
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0"))
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_sales: Mapped[int] = mapped_column(Integer, default=0)
    is_suspended: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="seller_profile")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="seller")


class SellerVerification(UUIDPk, Timestamps, Base):
    __tablename__ = "seller_verifications"

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE"), index=True
    )
    level_requested: Mapped[VerificationLevel] = mapped_column(StrEnum(VerificationLevel))
    document_type: Mapped[str] = mapped_column(String(40))  # nin, bvn, drivers_licence, passport, cac
    # Encrypted at rest (Fernet). Only a masked form is ever returned through the API.
    document_number_enc: Mapped[str] = mapped_column(Text)
    document_number_last4: Mapped[str] = mapped_column(String(4))
    document_file_key: Mapped[str | None] = mapped_column(String(500))  # private storage key
    business_name: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[VerificationStatus] = mapped_column(
        StrEnum(VerificationStatus), default=VerificationStatus.PENDING, index=True
    )
    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None]
    review_notes: Mapped[str | None] = mapped_column(Text)


class SubscriptionPlan(UUIDPk, Timestamps, Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (CheckConstraint("price >= 0", name="price_non_negative"),)

    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    price: Mapped[Decimal]
    interval_days: Mapped[int] = mapped_column(Integer)
    featured_listing_quota: Mapped[int] = mapped_column(Integer, default=0)
    features: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Subscription(UUIDPk, Timestamps, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_seller_status", "seller_id", "status"),)

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE")
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"))
    status: Mapped[SubscriptionStatus] = mapped_column(
        StrEnum(SubscriptionStatus), default=SubscriptionStatus.PENDING_PAYMENT
    )
    amount: Mapped[Decimal]
    current_period_start: Mapped[datetime | None]
    current_period_end: Mapped[datetime | None]
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"))
    granted_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    seller: Mapped[SellerProfile] = relationship(back_populates="subscriptions")
    plan: Mapped[SubscriptionPlan] = relationship()
