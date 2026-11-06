"""I'm not a robot" verification on sign-in.

Required when:
* this browser hasn't completed a successful sign-in in the last 24 hours (tracked by a signed, httpOnly
  `gng_seen` cookie set after every successful sign-in), or
* the account has 3+ recent wrong-password attempts.

The check runs on the server *before* the password is verified, so bots can't use the login endpoint to
test passwords without solving it. Providers: Google reCAPTCHA v2 (checkbox) or Cloudflare Turnstile;
a clearly-labelled mock in development/test.
"""

import hashlib
import hmac
import logging
import time

import httpx
from fastapi import Request, Response

from app.core.config import settings
from app.core.errors import AppError

log = logging.getLogger("goodsng.captcha")

SEEN_COOKIE = "gng_seen"
WINDOW_SECONDS = 24 * 3600
FAILED_ATTEMPTS_THRESHOLD = 3
MOCK_TOKEN = "mock-ok"
VERIFY_URL = {
    "recaptcha": "https://www.google.com/recaptcha/api/siteverify",
    "turnstile": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
}


class CaptchaRequired(AppError):
    status_code = 400
    code = "captcha_required"


def _sig(ts: int) -> str:
    return hmac.new(f"{settings.jwt_secret}:seen".encode(), str(ts).encode(), hashlib.sha256).hexdigest()[:32]


def last_seen(request: Request) -> int | None:
    raw = request.cookies.get(SEEN_COOKIE, "")
    ts, _, sig = raw.partition(".")
    if not ts.isdigit() or not hmac.compare_digest(sig, _sig(int(ts))):
        return None
    return int(ts)


def mark_seen(response: Response) -> None:
    ts = int(time.time())
    response.set_cookie(SEEN_COOKIE, f"{ts}.{_sig(ts)}", max_age=400 * 86400, httponly=True, samesite="lax",
                        secure=settings.environment in ("production", "staging"), path=f"{settings.api_prefix}/auth")


def enabled() -> bool:
    return settings.captcha_provider != "off"


def required(request: Request, user=None) -> bool:
    if not enabled():
        return False
    seen = last_seen(request)
    if seen is None or time.time() - seen > WINDOW_SECONDS:
        return True
    return bool(user is not None and (user.failed_login_count or 0) >= FAILED_ATTEMPTS_THRESHOLD)


def public_config(request: Request) -> dict:
    return {"required": required(request), "provider": settings.captcha_provider if enabled() else None,
            "site_key": settings.captcha_site_key if settings.captcha_provider in VERIFY_URL else None}


def verify(token: str | None, ip: str | None) -> bool:
    if not token:
        return False
    provider = settings.captcha_provider
    if provider == "mock":
        return settings.environment in ("development", "test") and token == MOCK_TOKEN
    if provider not in VERIFY_URL or not settings.captcha_secret_key:
        return False
    try:
        r = httpx.post(VERIFY_URL[provider], timeout=8,
                       data={"secret": settings.captcha_secret_key, "response": token, **({"remoteip": ip} if ip else {})})
        ok = bool(r.json().get("success"))
    except (httpx.HTTPError, ValueError):
        log.warning("captcha_verify_unreachable", extra={"provider": provider})
        return False
    return ok


def enforce(request: Request, user, token: str | None, ip: str | None) -> None:
    if required(request, user) and not verify(token, ip):
        raise CaptchaRequired("Please confirm you're not a robot to sign in.", details={"config": public_config(request) | {"required": True}})
