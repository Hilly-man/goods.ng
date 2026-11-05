"""Centralised notifications: in-app records + outbox for email/SMS, honouring user preferences."""

import logging
import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import Notification, NotificationPreference, OutboundMessage, User

log = logging.getLogger("goodsng.notify")

# event_type -> default channels
EVENTS: dict[str, dict[str, bool]] = {
    "registration": {"in_app": True, "email": True, "sms": False},
    "otp": {"in_app": False, "email": False, "sms": True},
    "new_message": {"in_app": True, "email": False, "sms": False},
    "new_offer": {"in_app": True, "email": True, "sms": False},
    "counter_offer": {"in_app": True, "email": True, "sms": False},
    "offer_accepted": {"in_app": True, "email": True, "sms": True},
    "offer_rejected": {"in_app": True, "email": False, "sms": False},
    "new_order": {"in_app": True, "email": True, "sms": True},
    "payment_confirmed": {"in_app": True, "email": True, "sms": True},
    "order_update": {"in_app": True, "email": True, "sms": False},
    "seller_dispatch": {"in_app": True, "email": True, "sms": True},
    "delivery_update": {"in_app": True, "email": True, "sms": False},
    "dispute": {"in_app": True, "email": True, "sms": True},
    "refund": {"in_app": True, "email": True, "sms": True},
    "funds_released": {"in_app": True, "email": True, "sms": False},
    "bnpl_decision": {"in_app": True, "email": True, "sms": True},
    "guarantor_response": {"in_app": True, "email": True, "sms": True},
    "repayment_reminder": {"in_app": True, "email": True, "sms": True},
    "subscription": {"in_app": True, "email": True, "sms": False},
    "verification": {"in_app": True, "email": True, "sms": False},
    "listing_moderation": {"in_app": True, "email": True, "sms": False},
    "review": {"in_app": True, "email": False, "sms": False},
}


def channels_for(db: Session, user_id: uuid.UUID, event_type: str) -> dict[str, bool]:
    defaults = dict(EVENTS.get(event_type, {"in_app": True, "email": False, "sms": False}))
    pref = db.query(NotificationPreference).filter_by(user_id=user_id, event_type=event_type).one_or_none()
    if pref:
        defaults.update(in_app=pref.in_app, email=pref.email, sms=pref.sms)
    return defaults


def notify(
    db: Session,
    user_id: uuid.UUID,
    event_type: str,
    title: str,
    body: str,
    link: str | None = None,
    data: dict | None = None,
    force_channels: dict[str, bool] | None = None,
) -> None:
    """Queue a notification inside the caller's transaction (delivered only if it commits)."""
    ch = force_channels or channels_for(db, user_id, event_type)
    now = utcnow()
    if ch.get("in_app"):
        db.add(Notification(user_id=user_id, event_type=event_type, title=title, body=body, link=link,
                            data=data or {}, created_at=now))
    user = db.get(User, user_id)
    if not user:
        return
    if ch.get("email") and user.email:
        db.add(OutboundMessage(user_id=user_id, channel="email", recipient=user.email, subject=title,
                               body=body, next_attempt_at=now, created_at=now))
    if ch.get("sms") and user.phone:
        db.add(OutboundMessage(user_id=user_id, channel="sms", recipient=user.phone, body=f"Goods.ng: {body}"[:480],
                               next_attempt_at=now, created_at=now))


def send_direct(db: Session, channel: str, recipient: str, body: str, subject: str | None = None) -> None:
    """For messages to unverified recipients (e.g. OTP) that bypass preferences."""
    now = utcnow()
    db.add(OutboundMessage(channel=channel, recipient=recipient, subject=subject, body=body,
                           next_attempt_at=now, created_at=now))


# ---------------- delivery (called by worker) ----------------
class ConsoleSender:
    """DEVELOPMENT ONLY: logs messages instead of sending. Replace with SMS/email provider adapters."""

    def send(self, msg: OutboundMessage) -> None:
        log.info("outbound_message", extra={"channel": msg.channel, "to": msg.recipient, "subject": msg.subject,
                                            "body": msg.body})


def get_sender(channel: str):
    return ConsoleSender()


def drain_outbox(db: Session, limit: int = 100) -> int:
    now = utcnow()
    msgs = (
        db.query(OutboundMessage)
        .filter(OutboundMessage.status == "pending", OutboundMessage.next_attempt_at <= now)
        .order_by(OutboundMessage.created_at)
        .with_for_update(skip_locked=True)
        .limit(limit)
        .all()
    )
    for m in msgs:
        try:
            get_sender(m.channel).send(m)
            m.status, m.sent_at = "sent", utcnow()
        except Exception as e:  # pragma: no cover
            m.attempts += 1
            m.last_error = str(e)[:300]
            m.status = "failed" if m.attempts >= 5 else "pending"
            m.next_attempt_at = utcnow() + timedelta(minutes=2**m.attempts)
    db.commit()
    return len(msgs)
