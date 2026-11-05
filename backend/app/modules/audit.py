from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import AdminAuditLog, User


def audit(db: Session, actor: User, action: str, target_type: str, target_id=None, details: dict | None = None,
          ip: str | None = None) -> None:
    db.add(AdminAuditLog(actor_id=actor.id, action=action, target_type=target_type,
                         target_id=str(target_id) if target_id else None, details=details or {}, ip=ip,
                         created_at=utcnow()))
