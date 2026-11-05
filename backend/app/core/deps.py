from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import Forbidden, Unauthorized
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


def require_permission(perm: str):
    def checker(user: CurrentUser) -> User:
        if not user.has_permission(perm):
            raise Forbidden("You do not have permission to perform this action")
        return user

    return checker


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return (fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown"))[:64]
