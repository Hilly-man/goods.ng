from fastapi import APIRouter, Request, Response

from app.core.config import settings
from app.core.deps import DB, CurrentUser, client_ip
from app.core.errors import Forbidden
from app.models import User
from app.modules.auth import service
from app.modules.auth.schemas import (
    ChangePasswordIn,
    LoginIn,
    OtpRequestIn,
    OtpVerifyIn,
    PasswordResetIn,
    PasswordResetRequestIn,
    RegisterIn,
    SellerSummary,
    TokenOut,
    UserOut,
)
from app.modules.subscriptions.premium import is_premium

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "gng_rt"
CSRF_HEADER = "x-requested-with"


def user_out(db, user: User) -> UserOut:
    out = UserOut.model_validate(user)
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


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, response: Response, db: DB):
    user = service.authenticate(db, data.email, data.password, client_ip(request))
    return _token_response(db, response, user, request)


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db: DB):
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
    service.logout(db, request.cookies.get(REFRESH_COOKIE))
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
