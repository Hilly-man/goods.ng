import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, SoftDelete, StrEnum, Timestamps, UUIDPk
from app.models.enums import AccountType, OtpPurpose, UserRole


class User(UUIDPk, Timestamps, SoftDelete, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    google_sub: Mapped[str | None] = mapped_column(String(64), unique=True)
    full_name: Mapped[str] = mapped_column(String(120))
    # Customers and staff are separate kinds of account: staff are created by a super admin, can't use the
    # marketplace, and customers can never be given admin access.
    account_type: Mapped[AccountType] = mapped_column(StrEnum(AccountType), default=AccountType.CUSTOMER,
                                                      server_default="customer", index=True)
    role: Mapped[UserRole] = mapped_column(StrEnum(UserRole), default=UserRole.USER)
    admin_role_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_roles.id"))
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    invite_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    invite_expires_at: Mapped[datetime | None]
    admin_permissions: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # Bumped on password change / forced logout to invalidate all access tokens.
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None]
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None]
    # TOTP two-factor authentication (encrypted secret, enabled timestamp, hashed recovery codes).
    totp_secret_enc: Mapped[str | None] = mapped_column(Text)
    totp_enabled_at: Mapped[datetime | None]
    totp_recovery_hashes: Mapped[list[str]] = mapped_column(ARRAY(String(64)), default=list, server_default="{}")
    # Last accepted TOTP counter, so the same 6-digit code cannot be replayed.
    totp_last_counter: Mapped[int | None] = mapped_column(Integer)

    profile: Mapped["Profile"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    seller_profile = relationship("SellerProfile", back_populates="user", uselist=False)
    admin_role = relationship("AdminRole", foreign_keys=[admin_role_id])

    @property
    def is_staff(self) -> bool:
        return self.account_type == AccountType.STAFF

    @property
    def is_admin(self) -> bool:
        return self.is_staff and self.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        return self.is_staff and self.role == UserRole.SUPER_ADMIN

    def permissions(self) -> set[str]:
        if not self.is_admin:
            return set()
        if self.role == UserRole.SUPER_ADMIN:
            from app.models.enums import AdminPermission

            return {p.value for p in AdminPermission}
        return set(self.admin_role.permissions if self.admin_role else []) | set(self.admin_permissions or [])

    def has_permission(self, perm: str) -> bool:
        return str(getattr(perm, "value", perm)) in self.permissions()


class AdminRole(UUIDPk, Timestamps, Base):
    """A named bundle of admin permissions. Built-in roles are is_system; super admins can add custom ones."""

    __tablename__ = "admin_roles"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(300))
    permissions: Mapped[list[str]] = mapped_column(ARRAY(String(50)), default=list, server_default="{}")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100)


class Profile(UUIDPk, Timestamps, Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    bio: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str | None] = mapped_column(String(60))
    city: Mapped[str | None] = mapped_column(String(80))
    address: Mapped[str | None] = mapped_column(String(300))

    user: Mapped[User] = relationship(back_populates="profile")


class RefreshToken(UUIDPk, Base):
    """Refresh tokens are stored hashed and rotated on every use.

    All tokens issued from one login share a ``family_id``. Presenting an already-rotated token
    indicates theft, and revokes the entire family.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    family_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    replaced_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    ip: Mapped[str | None] = mapped_column(String(64))


class OtpCode(UUIDPk, Base):
    __tablename__ = "otp_codes"
    __table_args__ = (Index("ix_otp_subject_purpose", "subject", "purpose"),)

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    subject: Mapped[str] = mapped_column(String(255))  # phone or email
    purpose: Mapped[OtpPurpose] = mapped_column(StrEnum(OtpPurpose))
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]
    consumed_at: Mapped[datetime | None]


class NotificationPreference(UUIDPk, Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "event_type"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50))
    in_app: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[bool] = mapped_column(Boolean, default=True)
    sms: Mapped[bool] = mapped_column(Boolean, default=False)
