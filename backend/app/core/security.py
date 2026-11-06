import base64
import hashlib
import hmac
import re
import secrets
import struct
import time
import uuid
from datetime import timedelta
from typing import Annotated
from urllib.parse import quote, urlencode

import jwt
import nh3
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet
from pydantic import AfterValidator, Field

from app.core.config import settings
from app.core.errors import Unauthorized
from app.core.time import utcnow

_hasher = PasswordHasher()


# ---------- passwords ----------
def hash_password(password: str) -> str:
    """Argon2id with argon2-cffi's RFC 9106 defaults (salted, memory-hard)."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """True when the stored hash used weaker/older parameters — re-hash on the next successful login."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")


def burn_password_check(password: str) -> None:
    """Spend the same time as a real check, so unknown emails can't be detected by response timing."""
    verify_password(password, _DUMMY_HASH)


_COMMON_PASSWORDS = {
    "password1", "password12", "password123", "passw0rd1", "12345678a", "123456789a", "qwerty123", "qwertyuiop1",
    "abc12345", "abcd1234", "1q2w3e4r", "1qaz2wsx", "iloveyou1", "welcome1", "welcome123", "admin123", "admin1234",
    "letmein1", "monkey123", "football1", "goodsng123", "goods.ng1", "nigeria123", "lagos1234", "changeme1",
}


def _check_password_strength(v: str) -> str:
    if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v)):
        raise ValueError("Password must contain letters and numbers")
    if v.lower() in _COMMON_PASSWORDS or len(set(v.lower())) < 4:
        raise ValueError("That password is too easy to guess — choose something less common")
    return v


# Use for every *new* password (register, reset, change, staff invite). Max 128 keeps hashing cost bounded.
StrongPassword = Annotated[str, Field(min_length=8, max_length=128), AfterValidator(_check_password_strength)]


# ---------- JWT access tokens ----------
def create_access_token(user_id: uuid.UUID, role: str, token_version: int) -> str:
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "tv": token_version,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise Unauthorized("Session expired", code="token_expired") from e
    except jwt.PyJWTError as e:
        raise Unauthorized("Invalid token") from e
    if payload.get("type") != "access":
        raise Unauthorized("Invalid token")
    return payload


# ---------- opaque tokens (refresh tokens, etc.) ----------
# ---------- MFA login tickets ----------
MFA_TICKET_MINUTES = 5


def create_mfa_ticket(user_id: uuid.UUID, token_version: int) -> str:
    now = utcnow()
    payload = {"sub": str(user_id), "tv": token_version, "type": "mfa",
               "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=MFA_TICKET_MINUTES)).timestamp()),
               "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_mfa_ticket(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as e:
        raise Unauthorized("This verification window has expired. Please log in again.", code="mfa_expired") from e
    except jwt.PyJWTError as e:
        raise Unauthorized("Invalid verification ticket") from e
    if payload.get("type") != "mfa":
        raise Unauthorized("Invalid verification ticket")
    return payload


# ---------- TOTP (RFC 6238) ----------
def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


def _b32decode(secret: str) -> bytes:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded)


def totp_at(secret: str, counter: int) -> str:
    digest = hmac.new(_b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code:06d}"


def totp_now(secret: str, at: float | None = None) -> str:
    return totp_at(secret, int((time.time() if at is None else at) // 30))


def match_totp_counter(secret: str, code: str, window: int = 1, at: float | None = None) -> int | None:
    code = (code or "").strip()
    if not code.isdigit() or len(code) != 6:
        return None
    counter = int((time.time() if at is None else at) // 30)
    for offset in range(-window, window + 1):
        candidate = counter + offset
        if hmac.compare_digest(totp_at(secret, candidate), code):
            return candidate
    return None


def verify_totp(secret: str, code: str, window: int = 1, at: float | None = None) -> bool:
    return match_totp_counter(secret, code, window=window, at=at) is not None


def totp_uri(secret: str, account_name: str, issuer: str = "Goods.ng") -> str:
    label = quote(f"{issuer}:{account_name}")
    query = urlencode({"secret": secret, "issuer": issuer, "algorithm": "SHA1", "digits": 6, "period": 30})
    return f"otpauth://totp/{label}?{query}"


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------- OTP ----------
def generate_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(code: str, subject: str) -> str:
    return hmac.new(settings.otp_secret.encode(), f"{subject}:{code}".encode(), hashlib.sha256).hexdigest()


# ---------- field encryption (KYC identifiers etc.) ----------
def _fernet() -> Fernet:
    key = settings.data_encryption_key.removeprefix("dev-only:")
    return Fernet(key.encode())


def encrypt_field(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_field(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def mask(value: str, keep: int = 4) -> str:
    return "•" * max(len(value) - keep, 0) + value[-keep:]


# ---------- input sanitisation ----------
def clean_text(value: str | None) -> str | None:
    """Strip all HTML from user-supplied text. Rendering layers must still escape output."""
    if value is None:
        return None
    return nh3.clean(value, tags=set()).strip()


def _clean_field(value: str) -> str:
    cleaned = clean_text(value) or ""
    if value.strip() and not cleaned:
        raise ValueError("Please enter plain text (HTML isn't allowed)")
    return cleaned


# Request-schema type: HTML is stripped as the data arrives, so it's clean everywhere it's later used
# (pages, emails, SMS, PDFs, CSV exports). Pair with Field(min_length/max_length) as usual.
CleanStr = Annotated[str, AfterValidator(_clean_field)]


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
