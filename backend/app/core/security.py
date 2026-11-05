import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta

import jwt
import nh3
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.errors import Unauthorized
from app.core.time import utcnow

_hasher = PasswordHasher()


# ---------- passwords ----------
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


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


def constant_time_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
