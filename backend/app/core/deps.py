import ipaddress
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.core.errors import AppError, Forbidden, Unauthorized
from app.core.security import decode_access_token
from app.models import SellerProfile, User

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def _load_user(db: Session, creds: HTTPAuthorizationCredentials | None) -> User | None:
    if not creds:
        return None
    payload = decode_access_token(creds.credentials)
    user = db.get(User, payload["sub"])
    if not user or not user.is_active or user.deleted_at is not None:
        raise Unauthorized("Account unavailable")
    if payload.get("tv") != user.token_version:
        raise Unauthorized("Session revoked", code="token_revoked")
    return user


def optional_user(db: DB, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User | None:
    return _load_user(db, creds)


def current_user(db: DB, creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> User:
    user = _load_user(db, creds)
    if not user:
        raise Unauthorized("Authentication required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
OptionalUser = Annotated[User | None, Depends(optional_user)]


def current_seller(user: CurrentUser, db: DB) -> SellerProfile:
    seller = db.query(SellerProfile).filter_by(user_id=user.id).one_or_none()
    if not seller:
        raise Forbidden("Create a seller profile first", code="seller_profile_required")
    if seller.is_suspended:
        raise Forbidden("Your seller account is suspended", code="seller_suspended")
    return seller


CurrentSeller = Annotated[SellerProfile, Depends(current_seller)]


def ensure_customer(user: User) -> None:
    """Staff accounts are for administration only and can't buy, sell, chat or take credit."""
    if user.is_staff:
        raise Forbidden("Staff accounts can't use marketplace features. Use a separate customer account.",
                        code="staff_account")


def require_permission(perm: str):
    def checker(user: CurrentUser) -> User:
        if not user.has_permission(perm):
            raise Forbidden("You do not have permission to perform this action")
        return user

    return checker


def require_admin_2fa(user: CurrentUser) -> User:
    if settings.admin_2fa_required and user.is_admin and not user.totp_enabled_at:
        raise Forbidden("Enable two-factor authentication on your account before using the admin API",
                        code="admin_2fa_required")
    return user


def _ip_in(ip: str, networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def resolve_client_ip(remote: str | None, forwarded: str | None, trusted_cidrs: list[str] | None) -> str:
    """Return the real client IP without trusting spoofable X-Forwarded-For values.

    The header is only considered when the direct peer is a configured trusted proxy. We then walk
    the chain from right to left and return the first address that is not itself a trusted proxy.
    """
    remote = (remote or "unknown").strip()
    networks = []
    for cidr in trusted_cidrs or []:
        try:
            networks.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:
            continue
    if not forwarded or not networks or not _ip_in(remote, networks):
        return remote[:64]
    chain = [ip.strip() for ip in forwarded.split(",") if ip.strip()]
    for ip in reversed(chain):
        if not _ip_in(ip, networks):
            return ip[:64]
    return (chain[0] if chain else remote)[:64]


def client_ip(request: Request) -> str:
    return resolve_client_ip(request.client.host if request.client else None,
                             request.headers.get("x-forwarded-for"), settings.trusted_proxy_cidrs)


def rate_limit_identity(request: Request) -> str:
    """Bucket requests per signed-in user or anonymous device rather than per IP alone.

    Mobile networks put thousands of people behind one carrier-grade NAT address, so an
    IP-only bucket throttles unrelated users. X-Anon-Id is client-supplied and can be rotated,
    so callers must also keep a coarse per-IP ceiling.
    """
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            sub = decode_access_token(auth[7:]).get("sub")
        except AppError:
            sub = None
        if sub:
            return f"user:{sub}"
    anon = request.headers.get("x-anon-id")
    if anon and 8 <= len(anon) <= 64:
        return f"anon:{anon}"
    return f"ip:{client_ip(request)}"
