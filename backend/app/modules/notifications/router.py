import uuid

from fastapi import APIRouter, Query
from sqlalchemy import func, select, update

from app.core.deps import DB, CurrentUser
from app.core.errors import NotFound
from app.core.time import utcnow
from app.models import Notification

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: CurrentUser, db: DB, unread_only: bool = False, limit: int = Query(30, le=100)):
    stmt = select(Notification).where(Notification.user_id == user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = db.scalars(stmt.order_by(Notification.created_at.desc()).limit(limit)).all()
    return [{"id": str(n.id), "event_type": n.event_type, "title": n.title, "body": n.body, "link": n.link,
             "read_at": n.read_at, "created_at": n.created_at} for n in rows]


@router.get("/unread-count")
def unread(user: CurrentUser, db: DB):
    n = db.scalar(select(func.count()).select_from(Notification).where(Notification.user_id == user.id,
                                                                      Notification.read_at.is_(None)))
    return {"unread": n or 0}


@router.post("/{notification_id}/read")
def mark_read(notification_id: uuid.UUID, user: CurrentUser, db: DB):
    res = db.execute(update(Notification).where(Notification.id == notification_id, Notification.user_id == user.id)
                     .values(read_at=utcnow()))
    if not res.rowcount:
        raise NotFound("Notification not found")  # someone else's (or no such) notification
    db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all(user: CurrentUser, db: DB):
    db.execute(update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
               .values(read_at=utcnow()))
    db.commit()
    return {"ok": True}
