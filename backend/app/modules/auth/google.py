"""Sign in with Google (OpenID Connect, authorization-code flow with PKCE).

    browser ── GET /auth/google/start?next=/x ──▶ 302 to Google (state + nonce + S256 code challenge)
    Google  ── GET /auth/google/callback?code&state ──▶ verify state cookie, exchange code, verify ID token
            ──▶ find/link/create the customer account ──▶ refresh cookie + 302 to /x
                (or /login#mfa=<ticket> when the account has two-factor auth on)

Security notes
* `state` is bound to the browser with a short-lived httpOnly cookie and is single-use (login-CSRF safe).
* The ID token's signature is checked against Google's published keys, plus aud / iss / exp / nonce.
* Accounts are linked by email only when Google says the email is verified.
* Staff accounts can't use Google sign-in: they keep password + 2FA on the admin console.

Without GOOGLE_CLIENT_ID/SECRET, development and test use a MOCK consent page (clearly labelled) so the
whole flow can be exercised locally; staging/production simply hide the button.
"""

import base64
import hashlib
import hmac
import html
import json
import logging
import secrets
from functools import lru_cache
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.cache import cache, check_rate_limit
from app.core.config import settings
from app.core.deps import DB, client_ip
from app.core.errors import NotFound
from app.core.security import hash_password
from app.core.time import utcnow
from app.models import Profile, User
from app.modules.auth import captcha
from app.modules.notifications.service import notify

log = logging.getLogger("goodsng.auth.google")
router = APIRouter(prefix="/google", tags=["auth"])

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
STATE_COOKIE = "gng_oauth"
STATE_TTL = 600


class OAuthFailure(Exception):
    def __init__(self, reason: str):
        self.reason = reason


def provider() -> str:
    if settings.google_client_id and settings.google_client_secret:
        return "google"
    if settings.environment in ("development", "test"):
        return "mock"
    return "disabled"


def _cookie_path() -> str:
    return f"{settings.api_prefix}/auth/google"


def _redirect_uri() -> str:
    return f"{settings.frontend_url.rstrip('/')}{settings.api_prefix}/auth/google/callback"


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def safe_next(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//") or "\\" in value or len(value) > 300:
        return "/"
    if value.split("?")[0] in ("/login", "/register"):
        return "/"
    return value


def _fail(reason: str) -> RedirectResponse:
    resp = RedirectResponse(f"/login?oauth_error={reason}", status_code=302)
    resp.delete_cookie(STATE_COOKIE, path=_cookie_path())
    return resp


@router.get("/config")
def google_config():
    p = provider()
    return {"enabled": p != "disabled", "mock": p == "mock"}


@router.get("/start")
def start(request: Request, next: str = "/"):
    p = provider()
    if p == "disabled":
        return _fail("unavailable")
    check_rate_limit(f"gstart:{client_ip(request)}", 30, 300)
    state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    cache.set_json(f"oauth:google:{state}", {"nonce": nonce, "verifier": verifier, "next": safe_next(next)}, ttl=STATE_TTL)
    if p == "google":
        url = AUTH_URL + "?" + urlencode({
            "client_id": settings.google_client_id, "redirect_uri": _redirect_uri(), "response_type": "code",
            "scope": "openid email profile", "state": state, "nonce": nonce, "prompt": "select_account",
            "code_challenge": _b64url(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256",
        })
    else:
        url = f"{settings.api_prefix}/auth/google/mock-consent?" + urlencode({"state": state, "nonce": nonce})
    resp = RedirectResponse(url, status_code=302)
    resp.set_cookie(STATE_COOKIE, state, max_age=STATE_TTL, httponly=True, samesite="lax", path=_cookie_path(),
                    secure=settings.environment in ("production", "staging"))
    return resp


@lru_cache(maxsize=1)
def _jwks() -> jwt.PyJWKClient:
    return jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)


def _exchange(code: str, verifier: str) -> dict:
    if provider() == "mock":
        if not code.startswith("mock."):
            raise OAuthFailure("google")
        try:
            return json.loads(base64.urlsafe_b64decode(code[5:] + "=" * (-len(code[5:]) % 4)))
        except ValueError as e:
            raise OAuthFailure("google") from e
    r = httpx.post(TOKEN_URL, timeout=10, data={
        "code": code, "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
        "redirect_uri": _redirect_uri(), "grant_type": "authorization_code", "code_verifier": verifier,
    })
    if r.status_code != 200:
        log.warning("google_token_exchange_failed", extra={"status": r.status_code})
        raise OAuthFailure("google")
    id_token = r.json().get("id_token")
    if not id_token:
        raise OAuthFailure("google")
    try:
        key = _jwks().get_signing_key_from_jwt(id_token)
        claims = jwt.decode(id_token, key.key, algorithms=["RS256"], audience=settings.google_client_id, leeway=30)
    except jwt.PyJWTError as e:
        log.warning("google_id_token_invalid", extra={"error": str(e)})
        raise OAuthFailure("google") from e
    if claims.get("iss") not in ISSUERS:
        raise OAuthFailure("google")
    return claims


def find_or_create_user(db: Session, claims: dict, ip: str) -> User:
    sub = str(claims.get("sub") or "")
    email = str(claims.get("email") or "").strip().lower()
    if not sub or not email:
        raise OAuthFailure("google")
    if claims.get("email_verified") not in (True, "true"):
        raise OAuthFailure("unverified")
    user = db.query(User).filter(User.google_sub == sub).one_or_none()
    if not user:
        user = db.query(User).filter(User.email == email).one_or_none()
        if user:
            if user.is_staff:
                raise OAuthFailure("staff")
            if user.google_sub and user.google_sub != sub:
                raise OAuthFailure("linked_elsewhere")
            user.google_sub = sub  # same verified email → link to the existing account
            user.email_verified = True
        else:
            check_rate_limit(f"register:{ip}", 10, 3600)
            name = str(claims.get("name") or email.split("@")[0]).strip()[:120]
            # Random password: the account signs in with Google, or the owner can set one via "Forgot password".
            user = User(email=email, full_name=name, password_hash=hash_password(secrets.token_urlsafe(32)),
                        google_sub=sub, email_verified=True, admin_permissions=[])
            user.profile = Profile()
            db.add(user)
            db.flush()
            notify(db, user.id, "registration", "Welcome to Goods.ng",
                   "Your account is ready. Buy. Sell. Trade with Confidence.", link="/account")
    if user.is_staff:
        raise OAuthFailure("staff")
    if not user.is_active or user.deleted_at:
        raise OAuthFailure("disabled")
    user.last_login_at = utcnow()
    return user


@router.get("/callback")
def callback(request: Request, db: DB, code: str | None = None, state: str | None = None, error: str | None = None):
    from app.modules.auth import service
    from app.modules.auth.router import _set_cookie

    if error:
        return _fail("cancelled")
    cookie_state = request.cookies.get(STATE_COOKIE)
    if not code or not state or not cookie_state or not hmac.compare_digest(state, cookie_state):
        return _fail("state")
    key = f"oauth:google:{state}"
    saved = cache.get_json(key)
    cache.delete(key)  # single use
    if not saved:
        return _fail("expired")
    try:
        claims = _exchange(code, saved["verifier"])
        if not hmac.compare_digest(str(claims.get("nonce") or ""), saved["nonce"]):
            raise OAuthFailure("state")
        user = find_or_create_user(db, claims, client_ip(request))
    except OAuthFailure as f:
        db.rollback()
        return _fail(f.reason)
    except httpx.HTTPError:
        db.rollback()
        log.exception("google_unreachable")
        return _fail("google")

    nxt = saved["next"]
    if user.totp_enabled_at:
        db.commit()
        ticket = service.issue_mfa_ticket(user)
        resp = RedirectResponse(f"/login?{urlencode({'next': nxt})}#mfa={ticket}", status_code=302)
    else:
        _, raw, _ = service.issue_tokens(db, user, user_agent=request.headers.get("user-agent"), ip=client_ip(request))
        db.commit()
        resp = RedirectResponse(nxt, status_code=302)
        _set_cookie(resp, raw)
        captcha.mark_seen(resp)  # Google sign-in counts as a verified sign-in on this device
    resp.delete_cookie(STATE_COOKIE, path=_cookie_path())
    return resp


# ---------------- development-only mock consent screen ----------------

@router.get("/mock-consent", response_class=HTMLResponse, include_in_schema=False)
def mock_consent(state: str, nonce: str):
    if provider() != "mock":
        raise NotFound()
    s, n = html.escape(state, quote=True), html.escape(nonce, quote=True)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MOCK Google sign-in</title><meta name="robots" content="noindex">
<style>body{{font-family:system-ui,sans-serif;background:#f1f5f9;display:grid;place-items:center;min-height:100vh;margin:0}}
.c{{background:#fff;border-radius:16px;padding:28px;max-width:380px;width:90%;box-shadow:0 10px 30px #0001}}
.b{{background:#fef3c7;color:#92400e;border-radius:8px;padding:8px 10px;font-size:13px;font-weight:600}}
label{{display:block;font-size:13px;margin-top:14px;color:#334155}}input{{width:100%;box-sizing:border-box;padding:10px;border:1px solid #cbd5e1;border-radius:8px;margin-top:4px;font-size:15px}}
button{{margin-top:18px;width:100%;padding:11px;border:0;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer}}
.go{{background:#1a73e8;color:#fff}}.no{{background:#e2e8f0;color:#334155}}</style></head><body><div class="c">
<p class="b">MOCK — development only. No data is sent to Google.</p>
<h1 style="font-size:20px;margin:16px 0 4px">Sign in with Google</h1><p style="margin:0;color:#64748b;font-size:14px">to continue to Goods.ng</p>
<form method="get" action="{settings.api_prefix}/auth/google/mock-approve">
<input type="hidden" name="state" value="{s}"><input type="hidden" name="nonce" value="{n}">
<label>Google account email<input name="email" type="email" required value="ada.google@example.com"></label>
<label>Name<input name="name" required value="Ada Okafor"></label>
<button class="go" type="submit">Continue</button></form>
<form method="get" action="{settings.api_prefix}/auth/google/callback"><input type="hidden" name="error" value="access_denied">
<button class="no" type="submit">Cancel</button></form></div></body></html>"""


@router.get("/mock-approve", include_in_schema=False)
def mock_approve(state: str, nonce: str, email: str, name: str):
    if provider() != "mock":
        raise NotFound()
    email = email.strip().lower()
    claims = {"sub": "mock-" + hashlib.sha256(email.encode()).hexdigest()[:24], "email": email,
              "email_verified": True, "name": name[:120], "nonce": nonce}
    code = "mock." + _b64url(json.dumps(claims).encode())
    return RedirectResponse(f"{settings.api_prefix}/auth/google/callback?" + urlencode({"code": code, "state": state}),
                            status_code=302)
