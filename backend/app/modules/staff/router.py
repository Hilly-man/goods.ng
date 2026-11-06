"""Staff (admin) accounts and admin roles — super admin only.

Staff accounts are separate from customer accounts: they can only be created here by a super admin, are
invited by email to set their own password, can't use marketplace features, and get their permissions from
an admin role. Customers can never be promoted to staff.
"""

import re
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field, field_validator
from slugify import slugify
from sqlalchemy import func, select

from app.core.cache import check_rate_limit
from app.core.config import settings
from app.core.deps import DB, CurrentUser, client_ip, require_admin_2fa
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.security import CleanStr, StrongPassword, clean_text, hash_password, new_opaque_token, sha256
from app.core.time import utcnow
from app.models import AdminRole, Profile, User
from app.models.enums import AccountType, AdminPermission, UserRole
from app.modules.audit import audit
from app.modules.auth.service import revoke_all_sessions
from app.modules.notifications.service import send_direct
from app.modules.staff.roles import PERMISSION_LABELS, SUPER_ADMIN, ensure_system_roles

INVITE_TTL_HOURS = 72

admin_router = APIRouter(prefix="/admin", tags=["admin: staff & roles"], dependencies=[Depends(require_admin_2fa)])
public_router = APIRouter(prefix="/auth/staff-invite", tags=["auth"])


def super_admin(user: CurrentUser) -> User:
    if not user.is_super_admin:
        raise Forbidden("Only a super admin can manage staff accounts and roles", code="super_admin_required")
    return user


SuperAdmin = Depends(super_admin)


def role_out(r: AdminRole, members: int | None = None) -> dict:
    return {"id": str(r.id), "code": r.code, "name": r.name, "description": r.description,
            "permissions": sorted(r.permissions or []), "is_system": r.is_system,
            **({"members": members} if members is not None else {})}


def staff_out(u: User) -> dict:
    role = u.admin_role
    status = "deactivated" if not u.is_active else "invited" if u.invite_token_hash else "active"
    return {
        "id": str(u.id), "full_name": u.full_name, "email": u.email, "status": status,
        "role": role_out(role) if role else ({"code": SUPER_ADMIN, "name": "Super Admin"} if u.is_super_admin else None),
        "is_super_admin": u.is_super_admin, "two_factor_enabled": u.totp_enabled_at is not None,
        "last_login_at": u.last_login_at, "created_at": u.created_at,
        "invite_expires_at": u.invite_expires_at if u.invite_token_hash else None,
    }


def _invite_link(token: str) -> str:
    base = (settings.admin_url or settings.frontend_url).rstrip("/")
    return f"{base}/accept-invite?token={token}"


def _send_invite(db, u: User, inviter: User) -> str:
    token = new_opaque_token()
    u.invite_token_hash = sha256(token)
    u.invite_expires_at = utcnow() + timedelta(hours=INVITE_TTL_HOURS)
    link = _invite_link(token)
    role_name = u.admin_role.name if u.admin_role else "Super Admin"
    send_direct(db, "email", u.email,
                f"Hello {u.full_name},\n\n{inviter.full_name} has invited you to the Goods.ng admin console as "
                f"{role_name}.\n\nSet your password here (valid for {INVITE_TTL_HOURS} hours): {link}\n\n"
                "If you weren't expecting this, ignore this email.",
                subject="You've been invited to the Goods.ng admin console")
    return link


def _dev(link: str) -> dict:
    # Development convenience ONLY: email isn't connected, so return the invite link.
    return {"dev_invite_link": link} if settings.environment in ("development", "test") else {}


def _apply_role(u: User, role: AdminRole) -> None:
    u.admin_role_id = role.id
    u.admin_role = role
    u.role = UserRole.SUPER_ADMIN if role.code == SUPER_ADMIN else UserRole.ADMIN
    u.admin_permissions = []  # permissions come from the role only


def _other_active_super_admins(db, exclude_id) -> int:
    return db.scalar(select(func.count()).select_from(User).where(
        User.account_type == AccountType.STAFF, User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True),
        User.deleted_at.is_(None), User.invite_token_hash.is_(None), User.id != exclude_id)) or 0


def _get_role(db, role_id) -> AdminRole:
    r = db.get(AdminRole, role_id)
    if not r:
        raise NotFound("Role not found")
    return r


def _get_staff(db, staff_id) -> User:
    u = db.get(User, staff_id)
    if not u or not u.is_staff or u.deleted_at:
        raise NotFound("Staff account not found")
    return u


# ---------------- permissions & roles ----------------
@admin_router.get("/permissions")
def permissions(admin: User = SuperAdmin):
    return [{"code": str(getattr(c, "value", c)), "group": g, "label": label} for c, (g, label) in PERMISSION_LABELS.items()]


@admin_router.get("/roles")
def list_roles(db: DB, admin: User = SuperAdmin):
    ensure_system_roles(db)
    counts = dict(db.execute(select(User.admin_role_id, func.count()).where(User.account_type == AccountType.STAFF,
                                                                            User.deleted_at.is_(None))
                             .group_by(User.admin_role_id)).all())
    db.commit()
    return [role_out(r, counts.get(r.id, 0))
            for r in db.scalars(select(AdminRole).order_by(AdminRole.sort_order, AdminRole.name))]


class RoleIn(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    description: str | None = Field(None, max_length=300)
    permissions: list[AdminPermission] = Field(min_length=1)


@admin_router.post("/roles", status_code=201)
def create_role(data: RoleIn, request: Request, db: DB, admin: User = SuperAdmin):
    code = slugify(data.name, separator="_")[:50]
    if not code or db.scalars(select(AdminRole).where(AdminRole.code == code)).first():
        raise Conflict("A role with this name already exists")
    r = AdminRole(code=code, name=clean_text(data.name), description=clean_text(data.description),
                  permissions=sorted(p.value for p in data.permissions), is_system=False)
    db.add(r)
    db.flush()
    audit(db, admin, "role.create", "admin_role", r.id, {"name": r.name, "permissions": r.permissions}, client_ip(request))
    db.commit()
    return role_out(r, 0)


@admin_router.put("/roles/{role_id}")
def update_role(role_id: uuid.UUID, data: RoleIn, request: Request, db: DB, admin: User = SuperAdmin):
    r = _get_role(db, role_id)
    if r.is_system:
        raise Forbidden("Built-in roles can't be edited. Create a custom role instead.", code="system_role")
    before = list(r.permissions)
    r.name, r.description = clean_text(data.name), clean_text(data.description)
    r.permissions = sorted(p.value for p in data.permissions)
    # Anyone holding this role must sign in again so new permissions apply everywhere.
    for u in db.scalars(select(User).where(User.admin_role_id == r.id)):
        revoke_all_sessions(db, u)
    audit(db, admin, "role.update", "admin_role", r.id, {"before": before, "after": r.permissions}, client_ip(request))
    db.commit()
    return role_out(r)


@admin_router.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: uuid.UUID, request: Request, db: DB, admin: User = SuperAdmin):
    r = _get_role(db, role_id)
    if r.is_system:
        raise Forbidden("Built-in roles can't be deleted", code="system_role")
    if db.scalar(select(func.count()).select_from(User).where(User.admin_role_id == r.id)):
        raise Conflict("Move staff off this role before deleting it", code="role_in_use")
    audit(db, admin, "role.delete", "admin_role", r.id, {"name": r.name}, client_ip(request))
    db.delete(r)
    db.commit()
    return Response(status_code=204)


# ---------------- staff accounts ----------------
@admin_router.get("/staff")
def list_staff(db: DB, admin: User = SuperAdmin):
    rows = db.scalars(select(User).where(User.account_type == AccountType.STAFF, User.deleted_at.is_(None))
                      .order_by(User.created_at)).all()
    return [staff_out(u) for u in rows]


class StaffIn(BaseModel):
    full_name: CleanStr = Field(min_length=2, max_length=120)
    email: EmailStr
    role_id: uuid.UUID

    @field_validator("email")
    @classmethod
    def _lower(cls, v):
        return v.lower()


@admin_router.post("/staff", status_code=201)
def create_staff(data: StaffIn, request: Request, db: DB, admin: User = SuperAdmin):
    check_rate_limit(f"staff-invite:{admin.id}", 30, 3600)
    if db.scalars(select(User).where(User.email == data.email)).first():
        raise Conflict("This email already has a Goods.ng account. Staff need their own (work) email address.",
                       code="email_taken")
    role = _get_role(db, data.role_id)
    u = User(email=data.email, full_name=clean_text(data.full_name), account_type=AccountType.STAFF,
             password_hash=hash_password(new_opaque_token()),  # unusable until the invite is accepted
             admin_permissions=[], invited_by_id=admin.id, email_verified=False)
    u.profile = Profile()
    _apply_role(u, role)
    db.add(u)
    db.flush()
    link = _send_invite(db, u, admin)
    audit(db, admin, "staff.create", "user", u.id, {"email": u.email, "role": role.code}, client_ip(request))
    db.commit()
    return {**staff_out(u), **_dev(link)}


class StaffUpdateIn(BaseModel):
    role_id: uuid.UUID | None = None
    is_active: bool | None = None
    full_name: CleanStr | None = Field(None, min_length=2, max_length=120)


@admin_router.patch("/staff/{staff_id}")
def update_staff(staff_id: uuid.UUID, data: StaffUpdateIn, request: Request, db: DB, admin: User = SuperAdmin):
    u = _get_staff(db, staff_id)
    changes: dict = {}
    if u.id == admin.id and (data.role_id is not None or data.is_active is False):
        raise Forbidden("You can't change your own role or deactivate yourself", code="self_change")
    losing_super = u.is_super_admin and (
        data.is_active is False or (data.role_id is not None and _get_role(db, data.role_id).code != SUPER_ADMIN))
    if losing_super and not _other_active_super_admins(db, u.id):
        raise Forbidden("There must always be at least one active super admin", code="last_super_admin")
    if data.role_id is not None:
        role = _get_role(db, data.role_id)
        changes["role"] = {"from": u.admin_role.code if u.admin_role else u.role.value, "to": role.code}
        _apply_role(u, role)
        revoke_all_sessions(db, u)
    if data.is_active is not None and data.is_active != u.is_active:
        changes["is_active"] = data.is_active
        u.is_active = data.is_active
        if not data.is_active:
            revoke_all_sessions(db, u)
    if data.full_name:
        changes["full_name"] = data.full_name
        u.full_name = clean_text(data.full_name)
    if changes:
        audit(db, admin, "staff.update", "user", u.id, changes, client_ip(request))
    db.commit()
    return staff_out(u)


@admin_router.post("/staff/{staff_id}/resend-invite")
def resend_invite(staff_id: uuid.UUID, request: Request, db: DB, admin: User = SuperAdmin):
    u = _get_staff(db, staff_id)
    if not u.invite_token_hash:
        raise AppError("This staff member has already set up their account", code="already_active")
    link = _send_invite(db, u, admin)
    audit(db, admin, "staff.resend_invite", "user", u.id, {}, client_ip(request))
    db.commit()
    return {**staff_out(u), **_dev(link)}


# ---------------- invite acceptance (public) ----------------
def _invited_user(db, token: str) -> User:
    u = db.scalars(select(User).where(User.invite_token_hash == sha256(token))).first()
    if not u or not u.is_staff or not u.is_active:
        raise NotFound("This invitation is invalid or has been withdrawn")
    if u.invite_expires_at and u.invite_expires_at < utcnow():
        raise AppError("This invitation has expired. Ask a super admin to resend it.", code="invite_expired")
    return u


@public_router.get("/{token}")
def view_invite(token: str, db: DB):
    u = _invited_user(db, token)
    return {"full_name": u.full_name, "email": u.email,
            "role": u.admin_role.name if u.admin_role else "Super Admin", "expires_at": u.invite_expires_at}


class AcceptIn(BaseModel):
    password: StrongPassword = Field(min_length=10)

    @field_validator("password")
    @classmethod
    def _strength(cls, v):
        if not (re.search(r"[A-Za-z]", v) and re.search(r"\d", v) and re.search(r"[^A-Za-z0-9]", v)):
            raise ValueError("Use at least 10 characters with letters, numbers and a symbol")
        return v


@public_router.post("/{token}")
def accept_invite(token: str, data: AcceptIn, request: Request, db: DB):
    check_rate_limit(f"staff-accept:{client_ip(request)}", 20, 3600)
    u = _invited_user(db, token)
    u.password_hash = hash_password(data.password)
    u.invite_token_hash = u.invite_expires_at = None
    u.email_verified = True
    db.commit()
    return {"message": "Your password is set. You can now sign in to the admin console.", "email": u.email}


router = APIRouter()
router.include_router(admin_router)
router.include_router(public_router)
