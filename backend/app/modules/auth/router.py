import segno
from fastapi import APIRouter, Request, Response

from app.core.cache import check_rate_limit
from app.core.config import settings
from app.core.deps import DB, CurrentUser, client_ip
from app.core.errors import AppError, Forbidden
from app.core.security import decode_mfa_ticket, sha256
from app.models import User
from app.modules.audit import audit_auth
from app.modules.auth import captcha, service
from app.modules.auth.schemas import (
    ChangePasswordIn,
    LoginIn,
    MfaChallengeOut,
    MfaVerifyIn,
    OtpRequestIn,
    OtpVerifyIn,
    PasswordResetIn,
    PasswordResetRequestIn,
    RegisterIn,
    SellerSummary,
    TokenOut,
    TotpDisableIn,
    TotpEnableIn,
    TotpEnableOut,
    TotpSetupOut,
    UserOut,
)
from app.modules.subscriptions.premium import is_premium

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "gng_rt"
CSRF_HEADER = "x-requested-with"


def user_out(db, user: User) -> UserOut:
    out = UserOut.model_validate(user)
    out.account_type = user.account_type.value if hasattr(user.account_type, "value") else str(user.account_type)
    if user.is_admin:
        out.admin_role_name = user.admin_role.name if user.admin_role else ("Super Admin" if user.is_super_admin else "Admin")
    out.two_factor_enabled = user.totp_enabled_at is not None
    out.google_linked = user.google_sub is not None
    if user.profile:
        out.avatar_url, out.state, out.city = user.profile.avatar_url, user.profile.state, user.profile.city
    if user.seller_profile:
        s = SellerSummary.model_validate(user.seller_profile)
        s.is_premium = is_premium(db, user.seller_profile.id)
        out.seller = s
    return out


def _set_cookie(resp: Response, raw: str):
    resp.set_cookie(
        REFRESH_COOKIE, raw, max_age=settings.refresh_token_days * 86400, httponly=True,
        secure=settings.environment in ("production", "staging"), samesite="lax", path=f"{settings.api_prefix}/auth",
    )


def _require_csrf(request: Request):
    # Cookie-authenticated endpoints require a custom header, which cross-site forms cannot send.
    if request.headers.get(CSRF_HEADER, "").lower() != "goodsng":
        raise Forbidden("Missing CSRF header", code="csrf")


def _token_response(db, resp: Response, user: User, request: Request) -> TokenOut:
    access, raw, _ = service.issue_tokens(db, user, user_agent=request.headers.get("user-agent"), ip=client_ip(request))
    db.commit()
    _set_cookie(resp, raw)
    return TokenOut(access_token=access, expires_in=settings.access_token_minutes * 60, user=user_out(db, user))


@router.post("/register", response_model=TokenOut, status_code=201)
def register(data: RegisterIn, request: Request, response: Response, db: DB):
    user = service.register(db, data, client_ip(request))
    return _token_response(db, response, user, request)


@router.get("/captcha")
def captcha_status(request: Request):
    """Does this browser need the "I'm not a robot" check to sign in? (and which widget to show)"""
    return captcha.public_config(request)


@router.post("/login", response_model=TokenOut | MfaChallengeOut)
def login(data: LoginIn, request: Request, response: Response, db: DB):
    # Bot check happens before the password is looked at.
    existing = db.query(User).filter(User.email == data.email.lower()).one_or_none()
    captcha.enforce(request, existing, data.captcha_token, client_ip(request))
    user = service.authenticate(db, data.email, data.password, client_ip(request))
    if user.totp_enabled_at:
        return MfaChallengeOut(mfa_ticket=service.issue_mfa_ticket(user))
    audit_auth(db, user, "auth.sign_in", details={"method": "password"})
    captcha.mark_seen(response)
    return _token_response(db, response, user, request)


@router.post("/mfa/verify", response_model=TokenOut)
def mfa_verify(data: MfaVerifyIn, request: Request, response: Response, db: DB):
    check_rate_limit(f"mfa:{client_ip(request)}", 20, 300)
    try:
        user = service.verify_login_mfa(db, data.mfa_ticket, data.code)
    except AppError:
        db.rollback()
        try:
            who = db.get(User, decode_mfa_ticket(data.mfa_ticket)["sub"])
        except AppError:
            who = None
        audit_auth(db, who, "auth.2fa_failed", outcome="failed")
        db.commit()
        raise
    audit_auth(db, user, "auth.sign_in", details={"method": "password + 2FA"})
    captcha.mark_seen(response)
    return _token_response(db, response, user, request)


@router.post("/2fa/setup", response_model=TotpSetupOut)
def totp_setup(user: CurrentUser, db: DB):
    check_rate_limit(f"2fa-setup:{user.id}", 5, 3600)
    secret, uri = service.start_totp(db, user)
    qr = segno.make(uri, error="m").svg_data_uri(scale=6, border=2, dark="#063d27", light="#ffffff")
    return TotpSetupOut(secret=secret, otpauth_url=uri, qr_svg=qr)


@router.post("/2fa/enable", response_model=TotpEnableOut)
def totp_enable(data: TotpEnableIn, request: Request, user: CurrentUser, db: DB):
    check_rate_limit(f"2fa-enable:{user.id}", 10, 3600)
    raw = request.cookies.get(REFRESH_COOKIE, "")
    return TotpEnableOut(recovery_codes=service.enable_totp(db, user, data.code,
                                                           keep_refresh_hash=sha256(raw) if raw else None))


@router.post("/2fa/disable")
def totp_disable(data: TotpDisableIn, user: CurrentUser, db: DB):
    check_rate_limit(f"2fa-disable:{user.id}", 10, 3600)
    service.disable_totp(db, user, data.password, data.code)
    return {"message": "Two-factor authentication disabled"}


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: DB):
    check_rate_limit(f"refresh:{client_ip(request)}", 120, 60)
    _require_csrf(request)
    try:
        user, access, raw = service.rotate_refresh(
            db, request.cookies.get(REFRESH_COOKIE, ""), request.headers.get("user-agent"), client_ip(request)
        )
    except Exception:
        response.delete_cookie(REFRESH_COOKIE, path=f"{settings.api_prefix}/auth")
        raise
    _set_cookie(response, raw)
    return TokenOut(access_token=access, expires_in=settings.access_token_minutes * 60, user=user_out(db, user))


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: DB):
    _require_csrf(request)
    who = service.logout(db, request.cookies.get(REFRESH_COOKIE))
    if who:
        audit_auth(db, who, "auth.sign_out")
        db.commit()
    response.delete_cookie(REFRESH_COOKIE, path=f"{settings.api_prefix}/auth")


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser, db: DB):
    return user_out(db, user)


def _dev_echo(code):
    # Development convenience ONLY: echo OTP so flows can be tested without an SMS provider.
    return {"dev_code": code} if settings.environment in ("development", "test") else {}


@router.post("/otp/request")
def otp_request(data: OtpRequestIn, user: CurrentUser, db: DB):
    code = service.request_phone_otp(db, user, data.phone)
    return {"message": "Verification code sent", **_dev_echo(code)}


@router.post("/otp/verify", response_model=UserOut)
def otp_verify(data: OtpVerifyIn, user: CurrentUser, db: DB):
    service.verify_phone_otp(db, user, data.code)
    return user_out(db, user)


@router.post("/password/forgot")
def forgot(data: PasswordResetRequestIn, request: Request, db: DB):
    code = service.request_password_reset(db, data.email, client_ip(request))
    return {"message": "If an account exists for this email, a reset code has been sent", **_dev_echo(code)}


@router.post("/password/reset")
def reset(data: PasswordResetIn, db: DB):
    service.reset_password(db, data.email, data.code, data.new_password)
    return {"message": "Password updated. Please log in."}


@router.post("/password/change")
def change(data: ChangePasswordIn, user: CurrentUser, db: DB, response: Response, request: Request):
    service.change_password(db, user, data.current_password, data.new_password)
    return _token_response(db, response, user, request)


from app.modules.auth.google import router as google_router  # noqa: E402

router.include_router(google_router)
