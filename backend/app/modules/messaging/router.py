import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.orm import Session

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentUser
from app.core.errors import AppError, Forbidden, NotFound
from app.core.security import clean_text
from app.core.time import utcnow
from app.models import Conversation, Message, MessageReport, Product, SellerProfile, User
from app.models.enums import ProductStatus
from app.modules.notifications.service import notify

router = APIRouter(tags=["messaging"])


class StartIn(BaseModel):
    product_id: uuid.UUID
    body: str = Field(min_length=1, max_length=2000)


class SendIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


def _party(conv: Conversation, user: User) -> str:
    if conv.buyer_id == user.id:
        return "buyer"
    if conv.seller_user_id == user.id:
        return "seller"
    raise NotFound("Conversation not found")


def _get_conv(db: Session, conv_id, user: User) -> tuple[Conversation, str]:
    conv = db.get(Conversation, conv_id)
    if not conv:
        raise NotFound("Conversation not found")
    return conv, _party(conv, user)


def message_out(m: Message) -> dict:
    return {"id": str(m.id), "conversation_id": str(m.conversation_id), "sender_id": str(m.sender_id), "body": m.body,
            "kind": m.kind, "offer_id": str(m.offer_id) if m.offer_id else None, "read_at": m.read_at,
            "created_at": m.created_at}


def post_message(db: Session, conv: Conversation, sender_id, body: str, kind: str = "text", offer_id=None) -> Message:
    now = utcnow()
    m = Message(conversation_id=conv.id, sender_id=sender_id, body=body, kind=kind, offer_id=offer_id, created_at=now)
    db.add(m)
    conv.last_message_at = now
    conv.last_message_preview = body[:200]
    conv.buyer_archived = conv.seller_archived = False
    return m


def get_or_create_conversation(db: Session, product: Product, buyer: User) -> tuple[Conversation, bool]:
    seller = db.get(SellerProfile, product.seller_id)
    if seller.user_id == buyer.id:
        raise AppError("You cannot message yourself about your own listing", code="own_listing")
    conv = db.scalars(select(Conversation).where(Conversation.product_id == product.id,
                                                 Conversation.buyer_id == buyer.id)).first()
    if conv:
        return conv, False
    conv = Conversation(product_id=product.id, buyer_id=buyer.id, seller_user_id=seller.user_id)
    db.add(conv)
    db.flush()
    db.execute(update(Product).where(Product.id == product.id).values(enquiries_count=Product.enquiries_count + 1))
    return conv, True


@router.post("/conversations", status_code=201)
def start(data: StartIn, user: CurrentUser, db: DB):
    check_rate_limit(f"msg:{user.id}", 30, 60)
    product = db.get(Product, data.product_id)
    if not product or product.deleted_at or product.status != ProductStatus.ACTIVE:
        raise NotFound("Listing not available")
    conv, _ = get_or_create_conversation(db, product, user)
    m = post_message(db, conv, user.id, clean_text(data.body))
    notify(db, conv.seller_user_id, "new_message", f"New message about {product.title[:60]}",
           clean_text(data.body)[:140], link=f"/messages/{conv.id}")
    db.commit()
    return {"conversation_id": str(conv.id), "message": message_out(m)}


@router.get("/conversations")
def list_conversations(user: CurrentUser, db: DB, role: str | None = Query(None, pattern="^(buyer|seller)$"),
                       limit: int = Query(30, le=100), before: datetime | None = None):
    cond = or_(and_(Conversation.buyer_id == user.id, Conversation.buyer_archived.is_(False)),
               and_(Conversation.seller_user_id == user.id, Conversation.seller_archived.is_(False)))
    if role == "buyer":
        cond = and_(Conversation.buyer_id == user.id, Conversation.buyer_archived.is_(False))
    elif role == "seller":
        cond = and_(Conversation.seller_user_id == user.id, Conversation.seller_archived.is_(False))
    stmt = select(Conversation).where(cond, Conversation.last_message_at.isnot(None))
    if before:
        stmt = stmt.where(Conversation.last_message_at < before)
    convs = db.scalars(stmt.order_by(Conversation.last_message_at.desc()).limit(limit)).all()
    ids = [c.id for c in convs]
    unread = dict(db.execute(select(Message.conversation_id, func.count()).where(
        Message.conversation_id.in_(ids), Message.sender_id != user.id, Message.read_at.is_(None))
        .group_by(Message.conversation_id)).all()) if ids else {}
    out = []
    for c in convs:
        is_buyer = c.buyer_id == user.id
        other = c.seller_user if is_buyer else c.buyer
        store = other.seller_profile if is_buyer else None
        p = c.product
        out.append({
            "id": str(c.id), "role": "buyer" if is_buyer else "seller",
            "other_party": {"id": str(other.id), "name": store.store_name if store else other.full_name,
                            "avatar_url": (store.logo_url if store else (other.profile.avatar_url if other.profile else None))},
            "product": {"id": str(p.id), "title": p.title, "slug": p.slug, "price": f"{p.price:.2f}",
                        "thumb_url": p.images[0].thumb_url if p.images else None} if p else None,
            "last_message_at": c.last_message_at, "last_message_preview": c.last_message_preview,
            "unread": unread.get(c.id, 0),
        })
    return out


@router.get("/conversations/unread-count")
def unread_count(user: CurrentUser, db: DB):
    n = db.scalar(select(func.count()).select_from(Message).join(Conversation).where(
        or_(Conversation.buyer_id == user.id, Conversation.seller_user_id == user.id),
        Message.sender_id != user.id, Message.read_at.is_(None)))
    return {"unread": n or 0}


@router.get("/conversations/{conv_id}")
def get_conversation(conv_id: uuid.UUID, user: CurrentUser, db: DB, after: datetime | None = None,
                     before: datetime | None = None, limit: int = Query(50, le=200)):
    """Message history. Clients poll with ?after=<last created_at> for near-real-time updates."""
    conv, role = _get_conv(db, conv_id, user)
    stmt = select(Message).where(Message.conversation_id == conv.id)
    if after:
        stmt = stmt.where(Message.created_at > after).order_by(Message.created_at).limit(limit)
        msgs = db.scalars(stmt).all()
    else:
        if before:
            stmt = stmt.where(Message.created_at < before)
        msgs = list(reversed(db.scalars(stmt.order_by(Message.created_at.desc()).limit(limit)).all()))
    # Read receipts: mark the other party's messages read.
    db.execute(update(Message).where(Message.conversation_id == conv.id, Message.sender_id != user.id,
                                     Message.read_at.is_(None)).values(read_at=utcnow()))
    db.commit()
    other = conv.seller_user if role == "buyer" else conv.buyer
    store = other.seller_profile if role == "buyer" else None
    p = conv.product
    from app.models import Negotiation
    from app.models.enums import NegotiationStatus

    neg = db.scalars(select(Negotiation).where(Negotiation.product_id == conv.product_id,
                                               Negotiation.buyer_id == conv.buyer_id,
                                               Negotiation.status.in_([NegotiationStatus.OPEN, NegotiationStatus.ACCEPTED]))
                     ).first() if p else None
    return {
        "id": str(conv.id), "role": role,
        "other_party": {"id": str(other.id), "name": store.store_name if store else other.full_name,
                        "seller_slug": store.slug if store else None},
        "product": {"id": str(p.id), "title": p.title, "slug": p.slug, "price": f"{p.price:.2f}",
                    "negotiable": p.negotiable, "status": p.status, "seller_id": str(p.seller_id),
                    "protected_checkout_enabled": p.protected_checkout_enabled,
                    "thumb_url": p.images[0].thumb_url if p.images else None} if p else None,
        "negotiation_id": str(neg.id) if neg else None,
        "messages": [message_out(m) for m in msgs],
    }


@router.post("/conversations/{conv_id}/messages", status_code=201)
def send(conv_id: uuid.UUID, data: SendIn, user: CurrentUser, db: DB):
    check_rate_limit(f"msg:{user.id}", 30, 60)
    conv, role = _get_conv(db, conv_id, user)
    body = clean_text(data.body)
    if not body:
        raise AppError("Message cannot be empty")
    m = post_message(db, conv, user.id, body)
    recipient = conv.seller_user_id if role == "buyer" else conv.buyer_id
    title = conv.product.title[:60] if conv.product else "your conversation"
    notify(db, recipient, "new_message", f"New message about {title}", body[:140], link=f"/messages/{conv.id}")
    db.commit()
    return message_out(m)


@router.post("/conversations/{conv_id}/archive")
def archive(conv_id: uuid.UUID, user: CurrentUser, db: DB):
    conv, role = _get_conv(db, conv_id, user)
    if role == "buyer":
        conv.buyer_archived = True
    else:
        conv.seller_archived = True
    db.commit()
    return {"archived": True}


@router.post("/messages/{message_id}/report", status_code=201)
def report(message_id: uuid.UUID, data: ReportIn, user: CurrentUser, db: DB):
    m = db.get(Message, message_id)
    if not m:
        raise NotFound("Message not found")
    conv, _ = _get_conv(db, m.conversation_id, user)
    if m.sender_id == user.id:
        raise Forbidden("You cannot report your own message")
    if db.scalars(select(MessageReport).where(MessageReport.message_id == m.id,
                                              MessageReport.reporter_id == user.id)).first():
        return {"reported": True}
    db.add(MessageReport(message_id=m.id, reporter_id=user.id, reason=clean_text(data.reason), created_at=utcnow()))
    db.commit()
    return {"reported": True}
