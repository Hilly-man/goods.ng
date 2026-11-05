import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentUser
from app.models import Negotiation, Product, SellerProfile
from app.modules.negotiation import service

router = APIRouter(prefix="/negotiations", tags=["negotiation"])


class StartIn(BaseModel):
    product_id: uuid.UUID
    amount: Decimal = Field(gt=0, decimal_places=2)
    note: str | None = Field(None, max_length=500)


class RespondIn(BaseModel):
    offer_id: uuid.UUID
    action: Literal["accept", "reject", "counter"]
    amount: Decimal | None = Field(None, gt=0, decimal_places=2)
    note: str | None = Field(None, max_length=500)


def neg_out(db, n: Negotiation, user) -> dict:
    p: Product = n.product
    seller = db.get(SellerProfile, n.seller_id)
    role = "buyer" if n.buyer_id == user.id else "seller"
    pending = next((o for o in n.offers if o.status == "pending"), None)
    return {
        "id": str(n.id), "status": n.status, "role": role,
        "product": {"id": str(p.id), "title": p.title, "slug": p.slug, "price": f"{p.price:.2f}",
                    "thumb_url": p.images[0].thumb_url if p.images else None, "status": p.status,
                    "bnpl_enabled": p.bnpl_enabled},
        "seller": {"id": str(seller.id), "store_name": seller.store_name, "slug": seller.slug},
        "buyer": {"id": str(n.buyer_id)},
        "listed_price": f"{n.listed_price:.2f}",
        "agreed_price": f"{n.agreed_price:.2f}" if n.agreed_price is not None else None,
        "accepted_at": n.accepted_at, "checkout_expires_at": n.checkout_expires_at,
        "conversation_id": str(n.conversation_id) if n.conversation_id else None,
        "awaiting": (("seller" if pending.made_by == "buyer" else "buyer") if pending else None),
        "your_turn": bool(pending and pending.made_by != role),
        "offers": [{"id": str(o.id), "made_by": o.made_by, "amount": f"{o.amount:.2f}", "note": o.note,
                    "status": o.status, "expires_at": o.expires_at, "created_at": o.created_at} for o in n.offers],
        "created_at": n.created_at, "updated_at": n.updated_at,
    }


@router.post("", status_code=201)
def start(data: StartIn, user: CurrentUser, db: DB):
    check_rate_limit(f"offer:{user.id}", 20, 3600)
    n = service.start(db, user, data.product_id, data.amount, data.note)
    return neg_out(db, n, user)


@router.get("")
def mine(user: CurrentUser, db: DB, role: Literal["buyer", "seller"] = "buyer", status: str | None = None,
         limit: int = Query(50, le=100)):
    if role == "buyer":
        stmt = select(Negotiation).where(Negotiation.buyer_id == user.id)
    else:
        seller = db.scalars(select(SellerProfile).where(SellerProfile.user_id == user.id)).first()
        if not seller:
            return []
        stmt = select(Negotiation).where(Negotiation.seller_id == seller.id)
    if status:
        stmt = stmt.where(Negotiation.status == status)
    rows = db.scalars(stmt.order_by(Negotiation.updated_at.desc()).limit(limit)).all()
    changed = any(service.expire_if_due(db, n) for n in rows)
    if changed:
        db.commit()
    return [neg_out(db, n, user) for n in rows]


@router.get("/{negotiation_id}")
def detail(negotiation_id: uuid.UUID, user: CurrentUser, db: DB):
    n = db.get(Negotiation, negotiation_id)
    if not n:
        from app.core.errors import NotFound

        raise NotFound("Negotiation not found")
    service._role(db, n, user)
    if service.expire_if_due(db, n):
        db.commit()
    return neg_out(db, n, user)


@router.post("/{negotiation_id}/respond")
def respond(negotiation_id: uuid.UUID, data: RespondIn, user: CurrentUser, db: DB):
    n = service.respond(db, user, negotiation_id, data.offer_id, data.action, data.amount, data.note)
    return neg_out(db, n, user)


@router.post("/{negotiation_id}/withdraw")
def withdraw(negotiation_id: uuid.UUID, user: CurrentUser, db: DB):
    return neg_out(db, service.withdraw(db, user, negotiation_id), user)
