import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import OtpPurpose, UserRole, VerificationLevel
from app.modules.common import Schema

PHONE_RE = re.compile(r"^\+234[789][01]\d{8}$")


def normalize_ng_phone(v: str) -> str:
    digits = re.sub(r"[^\d+]", "", v or "")
    if digits.startswith("+"):
        digits = digits[1:]
    if digits.startswith("0") and len(digits) == 11:
        digits = "234" + digits[1:]
    phone = "+" + digits
    if not PHONE_RE.match(phone):
        raise ValueError("Enter a valid Nigerian mobile number, e.g. 0803 123 4567")
    return phone


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8, max_length=128)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return normalize_ng_phone(v) if v else None

    @field_validator("password")
    @classmethod
    def _strength(cls, v):
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
            raise ValueError("Password must contain letters and numbers")
        return v

    @field_validator("email")
    @classmethod
    def _lower(cls, v):
        return v.lower()


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class OtpRequestIn(BaseModel):
    purpose: OtpPurpose = OtpPurpose.PHONE_VERIFY
    phone: str | None = None

    @field_validator("phone")
    @classmethod
    def _phone(cls, v):
        return normalize_ng_phone(v) if v else None


class OtpVerifyIn(BaseModel):
    code: str = Field(pattern=r"^\d{6}$")
    purpose: OtpPurpose = OtpPurpose.PHONE_VERIFY


class PasswordResetRequestIn(BaseModel):
    email: EmailStr


class PasswordResetIn(BaseModel):
    email: EmailStr
    code: str = Field(pattern=r"^\d{6}$")
    new_password: str = Field(min_length=8, max_length=128)


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class SellerSummary(Schema):
    id: uuid.UUID
    store_name: str
    slug: str
    verification_level: VerificationLevel
    is_premium: bool = False


class UserOut(Schema):
    id: uuid.UUID
    email: str
    phone: str | None
    full_name: str
    role: UserRole
    admin_permissions: list[str]
    email_verified: bool
    phone_verified: bool
    created_at: datetime
    avatar_url: str | None = None
    state: str | None = None
    city: str | None = None
    seller: SellerSummary | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut
