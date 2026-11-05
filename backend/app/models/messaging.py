import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, StrEnum, Timestamps, UUIDPk
from app.models.enums import NegotiationStatus, OfferParty, OfferStatus, ReportStatus


class Conversation(UUIDPk, Timestamps, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("product_id", "buyer_id", name="product_buyer"),
        CheckConstraint("buyer_id <> seller_user_id", name="distinct_parties"),
    )

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    seller_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(index=True)
    last_message_preview: Mapped[str | None] = mapped_column(String(200))
    buyer_archived: Mapped[bool] = mapped_column(default=False)
    seller_archived: Mapped[bool] = mapped_column(default=False)

    product = relationship("Product")
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller_user = relationship("User", foreign_keys=[seller_user_id])


class Message(UUIDPk, Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_conversation_created", "conversation_id", "created_at"),)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE")
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), default="text")  # text | offer | system
    offer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("offers.id"))
    read_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class MessageReport(UUIDPk, Base):
    __tablename__ = "message_reports"
    __table_args__ = (UniqueConstraint("message_id", "reporter_id"),)

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE")
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[ReportStatus] = mapped_column(StrEnum(ReportStatus), default=ReportStatus.OPEN)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Negotiation(UUIDPk, Timestamps, Base):
    """A buyer/seller price negotiation for one product. Never changes the public listing price."""

    __tablename__ = "negotiations"
    __table_args__ = (
        Index("ix_negotiations_product_buyer", "product_id", "buyer_id"),
        # At most one live negotiation per buyer per product.
        Index(
            "uq_negotiations_live",
            "product_id",
            "buyer_id",
            unique=True,
            postgresql_where="status IN ('open', 'accepted')",
        ),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id"), index=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id")
    )
    listed_price: Mapped[Decimal]  # snapshot at start
    status: Mapped[NegotiationStatus] = mapped_column(
        StrEnum(NegotiationStatus), default=NegotiationStatus.OPEN
    )
    agreed_price: Mapped[Decimal | None]
    accepted_at: Mapped[datetime | None]
    checkout_expires_at: Mapped[datetime | None]
    # Optimistic concurrency token; every state change increments it.
    version: Mapped[int] = mapped_column(Integer, default=1)

    offers: Mapped[list["Offer"]] = relationship(back_populates="negotiation", order_by="Offer.created_at")
    product = relationship("Product")

    __mapper_args__ = {"version_id_col": version}


class Offer(UUIDPk, Base):
    __tablename__ = "offers"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    negotiation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("negotiations.id", ondelete="CASCADE"), index=True
    )
    made_by: Mapped[OfferParty] = mapped_column(StrEnum(OfferParty))
    made_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    amount: Mapped[Decimal]
    note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[OfferStatus] = mapped_column(StrEnum(OfferStatus), default=OfferStatus.PENDING)
    expires_at: Mapped[datetime]
    responded_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    negotiation: Mapped[Negotiation] = relationship(back_populates="offers")
