"""Goods Flex (BNPL) credit profile: identity, bank-statement assessments, employment and guarantors."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, Timestamps, UUIDPk


class FlexProfile(UUIDPk, Timestamps, Base):
    __tablename__ = "flex_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    # BVN — encrypted at rest; only last 4 digits are ever shown.
    bvn_enc: Mapped[str | None] = mapped_column(Text)
    bvn_last4: Mapped[str | None] = mapped_column(String(4))
    # Keyed HMAC of the BVN: lets us block one BVN being used on several accounts without storing it in clear.
    bvn_fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True)
    bvn_name: Mapped[str | None] = mapped_column(String(160))
    bvn_phone_match: Mapped[bool | None]
    bvn_reference: Mapped[str | None] = mapped_column(String(80))
    bvn_verified_at: Mapped[datetime | None]
    # Employment
    employment_type: Mapped[str | None] = mapped_column(String(30))  # employed | self_employed | business_owner
    employer_name: Mapped[str | None] = mapped_column(String(160))
    job_title: Mapped[str | None] = mapped_column(String(120))
    work_email: Mapped[str | None] = mapped_column(String(255))
    work_email_token_hash: Mapped[str | None] = mapped_column(String(64))
    work_email_token_expires: Mapped[datetime | None]
    cac_number: Mapped[str | None] = mapped_column(String(30))
    monthly_income_declared: Mapped[Decimal | None]
    employment_verified_at: Mapped[datetime | None]
    employment_method: Mapped[str | None] = mapped_column(String(40))  # work_email | cac_and_statement


class BankConnection(UUIDPk, Base):
    __tablename__ = "bank_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    provider_account_ref: Mapped[str] = mapped_column(String(160))
    bank_name: Mapped[str] = mapped_column(String(80))
    account_name: Mapped[str] = mapped_column(String(160))
    account_number_last4: Mapped[str] = mapped_column(String(4))
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class CreditAssessment(UUIDPk, Base):
    """Immutable snapshot of one bank-statement analysis and the limit it produced."""

    __tablename__ = "credit_assessments"
    __table_args__ = (Index("ix_credit_assessments_user_created", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    bank_connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("bank_connections.id"))
    engine_version: Mapped[str] = mapped_column(String(30))
    months_analysed: Mapped[int] = mapped_column(Integer)
    monthly_income: Mapped[Decimal]
    income_source: Mapped[str] = mapped_column(String(30))
    monthly_debt: Mapped[Decimal]
    affordable_instalment: Mapped[Decimal]
    statement_limit: Mapped[Decimal]
    score: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]

    bank_connection: Mapped[BankConnection] = relationship()


class Guarantor(UUIDPk, Timestamps, Base):
    __tablename__ = "guarantors"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(20))
    relationship_to_user: Mapped[str] = mapped_column(String(40))
    bvn_enc: Mapped[str] = mapped_column(Text)
    bvn_last4: Mapped[str] = mapped_column(String(4))
    bvn_reference: Mapped[str] = mapped_column(String(80))
    # Keyed HMAC of the guarantor's BVN: caps how many borrowers one person can guarantee.
    bvn_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    # Amount shown to the guarantor when they consented. The borrower's limit cannot exceed it.
    amount_guaranteed: Mapped[Decimal | None]
    status: Mapped[str] = mapped_column(String(20), default="pending_consent")  # pending_consent|consented|declined|expired|revoked
    consent_token_hash: Mapped[str | None] = mapped_column(String(64))
    consent_expires_at: Mapped[datetime | None]
    consented_at: Mapped[datetime | None]
    consent_ip: Mapped[str | None] = mapped_column(String(64))
