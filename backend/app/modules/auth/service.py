import secrets
import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.cache import check_rate_limit
from app.core.config import settings
from app.core.errors import AppError, Conflict, Unauthorized
from app.core.security import (
    burn_password_check,
    create_access_token,
    create_mfa_ticket,
    decode_mfa_ticket,
    decrypt_field,
    encrypt_field,
    generate_otp,
    generate_totp_secret,
    hash_otp,
    hash_password,
    match_totp_counter,
    new_opaque_token,
    password_needs_rehash,
    sha256,
    totp_uri,
    verify_password,
)
from app.core.time import utcnow
from app.models import OtpCode, Profile, RefreshToken, User
from app.models.enums import OtpPurpose, VerificationLevel
from app.modules.audit import audit_auth
from app.modules.notifications.service import notify, send_direct

MAX_FAILED_LOGINS = 5
REUSE_GRACE_SECONDS = 20
LOCKOUT_MINUTES = 15


def register(db: Session, data, ip: str) -> User:
    check_rate_limit(f"register:{ip}", 10, 3600)
    if db.query(User).filter(User.email == data.email).first():
        raise Conflict("An account with this email already exists", code="email_taken")
    if data.phone and db.query(User).filter(User.phone == data.phone).first():
        raise Conflict("An account with this phone number already exists", code="phone_taken")
    user = User(email=data.email, phone=data.phone, full_name=data.full_name.strip(),
                password_hash=hash_password(data.password), admin_permissions=[])
    user.profile = Profile()
    db.add(user)
    db.flush()
    request_email_verification(db, user)
    notify(db, user.id, "registration", "Welcome to Goods.ng",
           "Your account is ready. Buy. Sell. Trade with Confidence.", link="/account")
    db.commit()
    return user


def authenticate(db: Session, email: str, password: str, ip: str) -> User:
    check_rate_limit(f"login:ip:{ip}", 30, 300)
    check_rate_limit(f"login:email:{email.lower()}", 10, 300)
    user = db.query(User).filter(User.email == email.lower()).one_or_none()
    now = utcnow()
    if user and user.locked_until and user.locked_until > now:
        raise Unauthorized("Too many failed attempts. Try again later.", code="account_locked")
    if not user:
        burn_password_check(password)  # same response time whether or not the email exists
    if not user or not verify_password(password, user.password_hash):
        if user:
            user.failed_login_count += 1
            locked = user.failed_login_count >= MAX_FAILED_LOGINS
            if locked:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
                user.failed_login_count = 0
            audit_auth(db, user, "auth.sign_in_failed", outcome="failed",
                       details={"reason": "wrong password", **({"locked_for_minutes": LOCKOUT_MINUTES} if locked else {})}, ip=ip)
            db.commit()
        raise Unauthorized("Incorrect email or password", code="invalid_credentials")
    if not user.is_active or user.deleted_at:
        raise Unauthorized("This account has been disabled", code="account_disabled")
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    db.commit()
    return user


# ---------------- two-factor authentication ----------------
RECOVERY_CODE_COUNT = 8
RECOVERY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def issue_mfa_ticket(user: User) -> str:
    return create_mfa_ticket(user.id, user.token_version)


def start_totp(db: Session, user: User) -> tuple[str, str]:
    if user.totp_enabled_at:
        raise Conflict("Two-factor authentication is already enabled", code="totp_already_enabled")
    secret = generate_totp_secret()
    user.totp_secret_enc = encrypt_field(secret)
    db.commit()
    return secret, totp_uri(secret, user.email)


def enable_totp(db: Session, user: User, code: str, keep_refresh_hash: str | None = None) -> list[str]:
    if user.totp_enabled_at:
        raise Conflict("Two-factor authentication is already enabled", code="totp_already_enabled")
    if not user.totp_secret_enc:
        raise AppError("Start two-factor setup first", code="totp_not_started")
    counter = match_totp_counter(decrypt_field(user.totp_secret_enc), code)
    if counter is None:
        raise Unauthorized("Incorrect authentication code", code="totp_invalid")
    codes = ["".join(secrets.choice(RECOVERY_ALPHABET) for _ in range(10)) for _ in range(RECOVERY_CODE_COUNT)]
    user.totp_recovery_hashes = [sha256(c) for c in codes]
    user.totp_enabled_at = utcnow()
    user.totp_last_counter = counter
    # A session created before 2FA should not be able to refresh forever. Keep this browser's
    # refresh token (if provided) and revoke every other session.
    query = db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    if keep_refresh_hash:
        query = query.filter(RefreshToken.token_hash != keep_refresh_hash)
    query.update({"revoked_at": utcnow()}, synchronize_session=False)
    db.commit()
    return codes


def _check_second_factor(user: User, code: str) -> None:
    code = (code or "").strip().upper()
    hashes = list(user.totp_recovery_hashes or [])
    recovery_hash = sha256(code)
    if recovery_hash in hashes:
        # Recovery codes are single-use.
        user.totp_recovery_hashes = [h for h in hashes if h != recovery_hash]
        return
    if not user.totp_secret_enc:
        raise Unauthorized("Incorrect authentication code", code="totp_invalid")
    counter = match_totp_counter(decrypt_field(user.totp_secret_enc), code)
    if counter is None or (user.totp_last_counter is not None and counter <= user.totp_last_counter):
        raise Unauthorized("Incorrect or already-used authentication code", code="totp_invalid")
    user.totp_last_counter = counter


def verify_login_mfa(db: Session, ticket: str, code: str) -> User:
    payload = decode_mfa_ticket(ticket)
    user = db.get(User, payload["sub"])
    if not user or not user.is_active or user.deleted_at:
        raise Unauthorized("Account unavailable")
    if payload.get("tv") != user.token_version:
        raise Unauthorized("Session revoked", code="token_revoked")
    if not user.totp_enabled_at:
        raise Unauthorized("Two-factor authentication is not enabled for this account")
    _check_second_factor(user, code)
    db.commit()
    return user


def disable_totp(db: Session, user: User, password: str, code: str) -> None:
    if not verify_password(password, user.password_hash):
        raise AppError("Password is incorrect", code="invalid_password")
    if not user.totp_enabled_at:
        raise AppError("Two-factor authentication is not enabled", code="totp_not_enabled")
    _check_second_factor(user, code)
    user.totp_secret_enc = None
    user.totp_enabled_at = None
    user.totp_recovery_hashes = []
    user.totp_last_counter = None
    db.commit()


def issue_tokens(db: Session, user: User, *, family_id: uuid.UUID | None = None, user_agent: str | None = None,
                 ip: str | None = None) -> tuple[str, str, RefreshToken]:
    raw = new_opaque_token()
    now = utcnow()
    rt = RefreshToken(user_id=user.id, token_hash=sha256(raw), family_id=family_id or uuid.uuid4(), created_at=now,
                      expires_at=now + timedelta(days=settings.refresh_token_days),
                      user_agent=(user_agent or "")[:300], ip=ip)
    db.add(rt)
    db.flush()
    access = create_access_token(user.id, user.role.value, user.token_version)
    return access, raw, rt


def rotate_refresh(db: Session, raw: str, user_agent: str | None, ip: str) -> tuple[User, str, str]:
    """Rotate a refresh token. Reuse of a rotated token revokes the whole token family."""
    if not raw:
        raise Unauthorized("No session")
    rt = db.query(RefreshToken).filter_by(token_hash=sha256(raw)).with_for_update().one_or_none()
    now = utcnow()
    if not rt:
        raise Unauthorized("Invalid session")
    if rt.revoked_at is not None and rt.replaced_by_id is not None and (now - rt.revoked_at).total_seconds() <= REUSE_GRACE_SECONDS:
        # Benign race: several tabs (or a double-mounted effect) refreshed with the same token at once.
        # Issue another token in the same family instead of treating it as theft.
        user = db.get(User, rt.user_id)
        if user and user.is_active and not user.deleted_at:
            access, new_raw, _ = issue_tokens(db, user, family_id=rt.family_id, user_agent=user_agent, ip=ip)
            db.commit()
            return user, access, new_raw
    if rt.revoked_at is not None:
        # Token replay outside the grace window => assume theft; kill the family.
        db.query(RefreshToken).filter(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None)).update(
            {"revoked_at": now}
        )
        db.commit()
        raise Unauthorized("Session reuse detected. Please log in again.", code="refresh_reuse")
    if rt.expires_at < now:
        raise Unauthorized("Session expired", code="session_expired")
    user = db.get(User, rt.user_id)
    if not user or not user.is_active or user.deleted_at:
        raise Unauthorized("Account unavailable")
    access, new_raw, new_rt = issue_tokens(db, user, family_id=rt.family_id, user_agent=user_agent, ip=ip)
    rt.revoked_at = now
    rt.replaced_by_id = new_rt.id
    db.commit()
    return user, access, new_raw


def logout(db: Session, raw: str | None) -> User | None:
    """Revoke the session's refresh-token family. Returns the user it belonged to (for the activity log)."""
    if not raw:
        return None
    rt = db.query(RefreshToken).filter_by(token_hash=sha256(raw)).one_or_none()
    if rt:
        db.query(RefreshToken).filter(RefreshToken.family_id == rt.family_id, RefreshToken.revoked_at.is_(None)).update(
            {"revoked_at": utcnow()}
        )
        db.commit()
        return db.get(User, rt.user_id)
    return None


def revoke_all_sessions(db: Session, user: User) -> None:
    user.token_version += 1
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)).update(
        {"revoked_at": utcnow()}
    )


# ---------------- OTP ----------------
def _create_otp(db: Session, subject: str, purpose: OtpPurpose, user_id=None) -> str:
    check_rate_limit(f"otp:{purpose}:{subject}", 3, 600)  # 3 codes / 10 min per subject
    check_rate_limit(f"otp:daily:{subject}", 10, 86400)
    now = utcnow()
    db.query(OtpCode).filter(OtpCode.subject == subject, OtpCode.purpose == purpose,
                             OtpCode.consumed_at.is_(None)).update({"consumed_at": now})
    code = generate_otp()
    db.add(OtpCode(user_id=user_id, subject=subject, purpose=purpose, code_hash=hash_otp(code, subject),
                   created_at=now, expires_at=now + timedelta(minutes=settings.otp_ttl_minutes)))
    return code


def _consume_otp(db: Session, subject: str, purpose: OtpPurpose, code: str) -> None:
    now = utcnow()
    otp = (
        db.query(OtpCode)
        .filter(OtpCode.subject == subject, OtpCode.purpose == purpose, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .with_for_update()
        .first()
    )
    if not otp or otp.expires_at < now:
        raise AppError("Code expired or not found. Request a new one.", code="otp_invalid")
    if otp.attempts >= settings.otp_max_attempts:
        otp.consumed_at = now
        db.commit()
        raise AppError("Too many incorrect attempts. Request a new code.", code="otp_locked")
    if otp.code_hash != hash_otp(code, subject):
        otp.attempts += 1
        db.commit()
        raise AppError("Incorrect code", code="otp_invalid")
    otp.consumed_at = now


def request_phone_otp(db: Session, user: User, phone: str | None) -> None:
    if phone and phone != user.phone:
        if db.query(User).filter(User.phone == phone, User.id != user.id).first():
            raise Conflict("Phone number already in use", code="phone_taken")
        user.phone = phone
        user.phone_verified = False
    if not user.phone:
        raise AppError("Add a phone number first", code="phone_required")
    code = _create_otp(db, user.phone, OtpPurpose.PHONE_VERIFY, user.id)
    send_direct(db, "sms", user.phone, f"Your Goods.ng verification code is {code}. It expires in "
                                       f"{settings.otp_ttl_minutes} minutes. Never share this code.")
    db.commit()
    return code  # returned only to the caller for dev echo; router decides whether to expose


def verify_phone_otp(db: Session, user: User, code: str) -> None:
    _consume_otp(db, user.phone or "", OtpPurpose.PHONE_VERIFY, code)
    user.phone_verified = True
    seller = user.seller_profile
    if seller and seller.verification_level == VerificationLevel.UNVERIFIED:
        seller.verification_level = VerificationLevel.PHONE
    db.commit()


def request_email_verification(db: Session, user: User) -> str | None:
    """Email the customer a 6-digit code. Returns the code for the router's dev echo only."""
    if user.email_verified:
        return None
    code = _create_otp(db, user.email, OtpPurpose.EMAIL_VERIFY, user.id)
    send_direct(
        db, "email", user.email,
        f"Your Goods.ng email verification code is {code}. It expires in {settings.otp_ttl_minutes} minutes.",
        subject="Verify your email", event_type="email_verification",
        link=f"{settings.frontend_url}/account", code=code, recipient_name=user.full_name,
    )
    return code


def verify_email(db: Session, user: User, code: str) -> None:
    _consume_otp(db, user.email, OtpPurpose.EMAIL_VERIFY, code)
    user.email_verified = True
    db.commit()


def request_password_reset(db: Session, email: str, ip: str) -> str | None:
    check_rate_limit(f"pwreset:{ip}", 10, 3600)
    user = db.query(User).filter(User.email == email.lower()).one_or_none()
    if not user:
        return None  # don't reveal account existence
    code = _create_otp(db, user.email, OtpPurpose.PASSWORD_RESET, user.id)
    send_direct(
        db, "email", user.email, f"Your Goods.ng password reset code is {code}.",
        subject="Reset your password", event_type="password_reset",
        link=f"{settings.frontend_url}/forgot-password", code=code, recipient_name=user.full_name,
    )
    db.commit()
    return code


def reset_password(db: Session, email: str, code: str, new_password: str) -> None:
    user = db.query(User).filter(User.email == email.lower()).one_or_none()
    if not user:
        raise AppError("Code expired or not found. Request a new one.", code="otp_invalid")
    _consume_otp(db, user.email, OtpPurpose.PASSWORD_RESET, code)
    user.password_hash = hash_password(new_password)
    revoke_all_sessions(db, user)
    db.commit()


def change_password(db: Session, user: User, current: str, new: str) -> None:
    if not verify_password(current, user.password_hash):
        raise AppError("Current password is incorrect", code="invalid_password")
    user.password_hash = hash_password(new)
    revoke_all_sessions(db, user)
    db.commit()
