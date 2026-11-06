"""Admin activity log (append-only; UPDATE/DELETE are blocked by a database trigger).

Every staff action lands here:
* explicit `audit(...)` calls from admin endpoints (the rich, human-readable entries)
* sign-in / sign-out / failed sign-in / failed 2FA for staff accounts (category "auth")
* console pages viewed (category "view", de-duplicated)
* a safety net in the HTTP layer that records any admin write that did NOT log itself — including
  requests that were refused (403) or failed — so nothing an admin does goes unrecorded (category "api").

Request context (IP, user agent) is attached automatically from the current request.
"""

from contextvars import ContextVar

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import AdminAuditLog, User

# One mutable dict per request: endpoints run in a worker thread with a *copy* of the context, so a shared
# object (not a reassigned var) is how "this request already wrote an audit entry" reaches the middleware.
request_audit: ContextVar[dict | None] = ContextVar("request_audit", default=None)


def audit(db: Session, actor: User, action: str, target_type: str, target_id=None, details: dict | None = None,
          ip: str | None = None, *, category: str = "action", outcome: str = "success") -> None:
    ctx = request_audit.get()
    if ctx is not None:
        ctx["audited"] = True
    db.add(AdminAuditLog(
        actor_id=actor.id, action=action, target_type=target_type, target_id=str(target_id) if target_id else None,
        details=details or {}, ip=ip or (ctx or {}).get("ip"), user_agent=((ctx or {}).get("ua") or "")[:300] or None,
        category=category, outcome=outcome, created_at=utcnow(),
    ))


def audit_auth(db: Session, user: User | None, action: str, *, outcome: str = "success", details: dict | None = None,
               ip: str | None = None) -> None:
    """Sign-in activity — recorded for staff accounts only (customers have their own security log)."""
    if user is None or not user.is_staff:
        return
    audit(db, user, action, "session", None, details, ip, category="auth", outcome=outcome)
