"""Centralised notifications: in-app records + outbox for email/SMS, honouring user preferences."""

import logging
import smtplib
import uuid
from datetime import timedelta
from email.message import EmailMessage

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
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
        db.info["outbox_dirty"] = True
    if ch.get("sms") and user.phone:
        db.add(OutboundMessage(user_id=user_id, channel="sms", recipient=user.phone, body=f"Goods.ng: {body}"[:480],
                               next_attempt_at=now, created_at=now))
        db.info["outbox_dirty"] = True


def send_direct(db: Session, channel: str, recipient: str, body: str, subject: str | None = None) -> None:
    """For messages to unverified recipients (e.g. OTP) that bypass preferences."""
    now = utcnow()
    db.add(OutboundMessage(channel=channel, recipient=recipient, subject=subject, body=body,
                           next_attempt_at=now, created_at=now))
    db.info["outbox_dirty"] = True


# ---------------- delivery (called by worker) ----------------
class ConsoleSender:
    """DEVELOPMENT ONLY: logs messages instead of sending."""

    def send(self, msg: OutboundMessage) -> None:
        log.info("outbound_message", extra={"channel": msg.channel, "to": msg.recipient, "subject": msg.subject,
                                            "body": msg.body})


class TermiiSender:
    """Termii SMS adapter (Nigeria). Server-side only; the API key never reaches the browser."""

    name = "termii"

    def __init__(self, api_key: str | None = None, sender_id: str | None = None,
                 base_url: str | None = None, transport: httpx.BaseTransport | None = None):
        self.api_key = api_key or settings.termii_api_key
        if not self.api_key:
            raise RuntimeError("TERMII_API_KEY is not configured")
        self.sender_id = sender_id or settings.termii_sender_id
        self.base_url = (base_url or settings.termii_base_url).rstrip("/")
        self.transport = transport

    def send(self, msg: OutboundMessage) -> None:
        payload = {"api_key": self.api_key, "to": msg.recipient, "from": self.sender_id, "sms": msg.body,
                   "type": "plain", "channel": "generic"}
        try:
            with httpx.Client(base_url=self.base_url, timeout=15, transport=self.transport) as c:
                r = c.post("/api/sms/send", json=payload)
        except httpx.HTTPError as e:
            raise RuntimeError("SMS provider unreachable") from e
        if r.status_code >= 400:
            raise RuntimeError(f"SMS provider error: {r.status_code}")


class PostmarkSender:
    """Postmark transactional email adapter."""

    name = "postmark"

    def __init__(self, server_token: str | None = None, from_addr: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.token = server_token or settings.postmark_server_token
        if not self.token:
            raise RuntimeError("POSTMARK_SERVER_TOKEN is not configured")
        self.from_addr = from_addr or settings.postmark_from
        if not self.from_addr:
            raise RuntimeError("POSTMARK_FROM is not configured")
        self.transport = transport

    def send(self, msg: OutboundMessage) -> None:
        try:
            with httpx.Client(timeout=15, transport=self.transport) as c:
                r = c.post("https://api.postmarkapp.com/email", headers={
                    "X-Postmark-Server-Token": self.token, "Accept": "application/json"}, json={
                    "From": self.from_addr, "To": msg.recipient, "Subject": msg.subject or "Goods.ng",
                    "TextBody": msg.body, "MessageStream": "outbound"})
        except httpx.HTTPError as e:
            raise RuntimeError("Email provider unreachable") from e
        if r.status_code >= 400:
            raise RuntimeError(f"Email provider error: {r.status_code}")


class SmtpSender:
    """SMTP email adapter (e.g. SES, Postmark SMTP, Mailgun SMTP)."""

    name = "smtp"

    def __init__(self, host: str | None = None, port: int | None = None, username: str | None = None,
                 password: str | None = None, from_addr: str | None = None, smtp_factory=None):
        self.host = host or settings.smtp_host
        self.port = port or settings.smtp_port
        self.username = username if username is not None else settings.smtp_username
        self.password = password if password is not None else settings.smtp_password
        self.from_addr = from_addr or settings.smtp_from
        if not self.host or not self.from_addr:
            raise RuntimeError("SMTP_HOST and SMTP_FROM are not configured")
        self.smtp_factory = smtp_factory or smtplib.SMTP

    def send(self, msg: OutboundMessage) -> None:
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.from_addr, msg.recipient, msg.subject or "Goods.ng"
        m.set_content(msg.body)
        smtp = self.smtp_factory(self.host, self.port, timeout=15)
        try:
            smtp.starttls()
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(m)
        finally:
            smtp.quit()


def get_sender(channel: str):
    if channel == "sms" and settings.sms_provider == "termii":
        return TermiiSender()
    if channel == "email" and settings.email_provider == "postmark":
        return PostmarkSender()
    if channel == "email" and settings.email_provider == "smtp":
        return SmtpSender()
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
