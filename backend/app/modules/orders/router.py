import uuid
from typing import Literal

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentSeller, CurrentUser
from app.core.errors import NotFound
from app.core.security import CleanStr
from app.integrations.storage import store_image
from app.models import Dispute, EscrowTransaction, Order, Payment, Product, Refund
from app.models.enums import DisputeReason, EscrowStatus, PaymentMethod
from app.modules.auth.schemas import normalize_ng_phone
from app.modules.common import PageParams, paginate
from app.modules.orders import service
from app.modules.products.schemas import NG_STATES

router = APIRouter(tags=["orders"])


class Address(BaseModel):
    full_name: CleanStr = Field(min_length=2, max_length=120)
    phone: str
    state: str
    city: CleanStr = Field(min_length=2, max_length=80)
    street: CleanStr = Field(min_length=3, max_length=300)
    landmark: CleanStr | None = Field(None, max_length=200)

    @field_validator("phone")
    @classmethod
    def _p(cls, v):
        return normalize_ng_phone(v)

    @field_validator("state")
    @classmethod
    def _s(cls, v):
        if v not in NG_STATES:
            raise ValueError("Select a valid Nigerian state")
        return v


class QuoteIn(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(1, ge=1, le=1000)
    negotiation_id: uuid.UUID | None = None
    delivery_option_index: int = 0


class CheckoutIn(QuoteIn):
    address: Address
    note: CleanStr | None = Field(None, max_length=500)
    marketing_consent: bool = False  # buyer accepted marketing cookies (ads measurement)


def quote_out(q: dict) -> dict:
    return {
        "product_id": str(q["product_id"]), "unit_price": f"{q['unit_price']:.2f}", "listed_price": f"{q['listed_price']:.2f}",
        "quantity": q["quantity"], "subtotal": f"{q['subtotal']:.2f}", "delivery_fee": f"{q['delivery_fee']:.2f}",
        "protection_fee": f"{q['protection_fee']:.2f}", "total": f"{q['total']:.2f}",
        "delivery_option": q["delivery_option"], "negotiated": q["negotiation"] is not None,
        "seller": {"id": str(q["seller"].id), "store_name": q["seller"].store_name, "slug": q["seller"].slug,
                   "verification_level": q["seller"].verification_level},
    }


@router.post("/checkout/quote")
def quote(data: QuoteIn, user: CurrentUser, db: DB):
    product = db.get(Product, data.product_id)
    if not product:
        raise NotFound("Listing not found")
    return quote_out(service.price_checkout(db, user, product, data.quantity, data.negotiation_id,
                                            data.delivery_option_index))


@router.post("/checkout", status_code=201)
def checkout(data: CheckoutIn, user: CurrentUser, db: DB, idempotency_key: str | None = Header(None, max_length=80)):
    check_rate_limit(f"checkout:{user.id}", 30, 3600)
    order, pay = service.create_checkout(
        db, user, product_id=data.product_id, quantity=data.quantity, negotiation_id=data.negotiation_id,
        delivery_index=data.delivery_option_index, address=data.address.model_dump(), note=data.note,
        idempotency_key=idempotency_key,
    )
    if data.marketing_consent and not order.marketing_consent:
        order.marketing_consent = True
        db.commit()
    return {"order_id": str(order.id), "order_number": order.order_number, "total": f"{order.total:.2f}",
            "payment_reference": pay.reference if pay else None,
            "authorization_url": pay.authorization_url if pay and pay.status == "initialized" else None}


def order_out(db, o: Order, role: str, detail: bool = False) -> dict:
    esc: EscrowTransaction = o.escrow
    out = {
        "id": str(o.id), "order_number": o.order_number, "status": o.status, "payment_method": o.payment_method,
        "role": role, "currency": o.currency, "subtotal": f"{o.subtotal:.2f}", "delivery_fee": f"{o.delivery_fee:.2f}",
        "protection_fee": f"{o.protection_fee:.2f}", "total": f"{o.total:.2f}",
        "items": [{"product_id": str(i.product_id), "title": i.title, "image_url": i.image_url,
                   "unit_price": f"{i.unit_price:.2f}", "listed_price": f"{i.listed_price:.2f}", "quantity": i.quantity,
                   "line_total": f"{i.line_total:.2f}"} for i in o.items],
        "seller": {"id": str(o.seller.id), "store_name": o.seller.store_name, "slug": o.seller.slug},
        "buyer": {"id": str(o.buyer.id), "name": o.buyer.full_name},
        "created_at": o.created_at, "paid_at": o.paid_at, "completed_at": o.completed_at, "expires_at": o.expires_at,
        "negotiated": o.negotiation_id is not None,
    }
    if role == "seller":
        out["seller_earnings"] = f"{esc.seller_amount:.2f}"
        out["platform_fees"] = f"{esc.platform_amount - o.protection_fee:.2f}"
    if detail:
        d = o.delivery
        out.update(
            delivery_option=o.delivery_option,
            # Buyer address is shared with the seller only once the order is funded.
            delivery_address=o.delivery_address if (role != "seller" or o.paid_at) else None,
            buyer_note=o.buyer_note, cancellation_reason=o.cancellation_reason,
            delivery={"status": d.status, "method": d.method, "carrier": d.carrier,
                      "tracking_reference": d.tracking_reference, "tracking_url": d.tracking_url,
                      "evidence_urls": d.evidence_urls, "dispatched_at": d.dispatched_at,
                      "delivered_at": d.delivered_at, "updates": d.updates} if d else None,
            escrow={"status": esc.status, "funded_at": esc.funded_at, "release_eligible_at": esc.release_eligible_at,
                    "released_at": esc.released_at, "refunded_at": esc.refunded_at,
                    "timeline": [{"from": e.from_status, "to": e.to_status, "actor": e.actor_role, "note": e.note,
                                  "at": e.created_at} for e in esc.events]},
            payment=_latest_payment(db, o),
            disputes=[{"id": str(x.id), "status": x.status, "reason": x.reason, "opened_by": x.opened_by_role,
                       "description": x.description, "resolution_notes": x.resolution_notes, "created_at": x.created_at,
                       "messages": [{"author_role": m.author_role, "body": m.body, "evidence_urls": m.evidence_urls,
                                     "created_at": m.created_at} for m in x.messages]}
                      for x in db.scalars(select(Dispute).where(Dispute.order_id == o.id)
                                          .order_by(Dispute.created_at)).all()],
            refunds=[{"id": str(r.id), "amount": f"{r.amount:.2f}", "status": r.status, "reason": r.reason,
                      "created_at": r.created_at, "completed_at": r.completed_at}
                     for r in db.scalars(select(Refund).where(Refund.order_id == o.id)).all()],
            actions=_actions(o, role),
        )
        if o.payment_method == PaymentMethod.BNPL:
            from app.modules.bnpl.service import financing_summary_for_order

            out["financing"] = financing_summary_for_order(db, o, role)
    return out


def _latest_payment(db, o):
    p = db.scalars(select(Payment).where(Payment.order_id == o.id).order_by(Payment.created_at.desc())).first()
    if not p:
        return None
    return {"reference": p.reference, "status": p.status, "purpose": p.purpose, "amount": f"{p.amount:.2f}",
            "authorization_url": p.authorization_url if p.status == "initialized" else None}


def _actions(o: Order, role: str) -> list[str]:
    S = EscrowStatus
    s = o.status
    acts = []
    if role == "buyer":
        if s == S.PENDING_PAYMENT:
            acts += ["pay", "cancel"]
        if s == S.AWAITING_SELLER:
            acts += ["cancel"]
        if s in (S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION):
            acts += ["confirm"]
        if s in service.BUYER_DISPUTABLE:
            acts += ["dispute"]
        if s == S.COMPLETED:
            acts += ["review"]
    elif role == "seller":
        if s == S.AWAITING_SELLER:
            acts += ["accept", "decline"]
        if s == S.PROCESSING:
            acts += ["dispatch", "decline"]
        if s == S.DISPATCHED:
            acts += ["delivery_update", "mark_delivered"]
        if s in service.SELLER_DISPUTABLE:
            acts += ["dispute"]
    return acts


@router.get("/orders")
def my_orders(user: CurrentUser, db: DB, status: str | None = None, params: PageParams = Depends()):
    stmt = select(Order).where(Order.buyer_id == user.id)
    if status:
        stmt = stmt.where(Order.status == status)
    page = paginate(db, stmt.order_by(Order.created_at.desc()), params)
    page["items"] = [order_out(db, o, "buyer") for o in page["items"]]
    return page


@router.get("/seller/orders")
def seller_orders(seller: CurrentSeller, db: DB, status: str | None = None,
                  bucket: Literal["all", "action", "transit", "done"] = "all", params: PageParams = Depends()):
    S = EscrowStatus
    stmt = select(Order).where(Order.seller_id == seller.id, Order.status != S.PENDING_PAYMENT)
    buckets = {"action": [S.AWAITING_SELLER, S.PROCESSING, S.DISPUTED],
               "transit": [S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION],
               "done": [S.COMPLETED, S.REFUNDED, S.CANCELLED, S.REFUND_PENDING]}
    if bucket in buckets:
        stmt = stmt.where(Order.status.in_(buckets[bucket]))
    if status:
        stmt = stmt.where(Order.status == status)
    page = paginate(db, stmt.order_by(Order.created_at.desc()), params)
    page["items"] = [order_out(db, o, "seller") for o in page["items"]]
    return page


@router.get("/orders/{order_id}")
def order_detail(order_id: uuid.UUID, user: CurrentUser, db: DB):
    o, role = service.get_for(db, user, order_id)
    return order_out(db, o, role, detail=True)


@router.post("/orders/{order_id}/retry-payment")
def retry_payment(order_id: uuid.UUID, user: CurrentUser, db: DB):
    p = service.retry_payment(db, user, order_id)
    return {"payment_reference": p.reference, "authorization_url": p.authorization_url}


class ReasonIn(BaseModel):
    reason: str | None = Field(None, max_length=300)


class DispatchIn(BaseModel):
    carrier: str | None = Field(None, max_length=80)
    tracking_reference: str | None = Field(None, max_length=120)
    tracking_url: str | None = Field(None, max_length=500, pattern=r"^https://")
    notes: str | None = Field(None, max_length=500)


class DeliveredIn(BaseModel):
    evidence_urls: list[str] = Field(default_factory=list, max_length=5)
    notes: str | None = Field(None, max_length=500)


class UpdateIn(BaseModel):
    note: str = Field(min_length=3, max_length=300)


class DisputeIn(BaseModel):
    reason: DisputeReason
    description: str = Field(min_length=20, max_length=3000)
    evidence_urls: list[str] = Field(default_factory=list, max_length=8)


class DisputeMsgIn(BaseModel):
    body: str = Field(min_length=2, max_length=3000)
    evidence_urls: list[str] = Field(default_factory=list, max_length=8)


def _detail(db, user, order_id):
    o, role = service.get_for(db, user, order_id)
    db.refresh(o)
    return order_out(db, o, role, detail=True)


@router.post("/orders/{order_id}/accept")
def accept(order_id: uuid.UUID, user: CurrentUser, db: DB):
    service.seller_accept(db, user, order_id)
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/decline")
def decline(order_id: uuid.UUID, data: ReasonIn, user: CurrentUser, db: DB):
    service.seller_decline(db, user, order_id, data.reason or "Unable to fulfil")
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/dispatch")
def dispatch(order_id: uuid.UUID, data: DispatchIn, user: CurrentUser, db: DB):
    service.seller_dispatch(db, user, order_id, data.carrier, data.tracking_reference, data.tracking_url, data.notes)
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/delivery-update")
def delivery_update(order_id: uuid.UUID, data: UpdateIn, user: CurrentUser, db: DB):
    service.add_delivery_update(db, user, order_id, data.note)
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/evidence")
async def upload_evidence(order_id: uuid.UUID, user: CurrentUser, db: DB, file: UploadFile = File(...)):
    check_rate_limit(f"evidence:{user.id}", 40, 3600)
    service.get_for(db, user, order_id)
    img = store_image(await file.read(), f"evidence/{order_id}")
    return {"url": img.url}


@router.post("/orders/{order_id}/delivered")
def delivered(order_id: uuid.UUID, data: DeliveredIn, user: CurrentUser, db: DB):
    service.seller_mark_delivered(db, user, order_id, data.evidence_urls, data.notes)
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/confirm")
def confirm(order_id: uuid.UUID, user: CurrentUser, db: DB):
    service.buyer_confirm(db, user, order_id)
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/cancel")
def cancel(order_id: uuid.UUID, data: ReasonIn, user: CurrentUser, db: DB):
    service.buyer_cancel(db, user, order_id, data.reason)
    return _detail(db, user, order_id)


@router.post("/orders/{order_id}/disputes", status_code=201)
def dispute(order_id: uuid.UUID, data: DisputeIn, user: CurrentUser, db: DB):
    check_rate_limit(f"dispute:{user.id}", 10, 86400)
    service.open_dispute(db, user, order_id, data.reason, data.description, data.evidence_urls)
    return _detail(db, user, order_id)


@router.post("/disputes/{dispute_id}/messages", status_code=201)
def dispute_message(dispute_id: uuid.UUID, data: DisputeMsgIn, user: CurrentUser, db: DB):
    m = service.add_dispute_message(db, user, dispute_id, data.body, data.evidence_urls)
    return {"id": str(m.id), "created_at": m.created_at}


@router.get("/seller/earnings")
def earnings(seller: CurrentSeller, db: DB, limit: int = Query(50, le=200)):
    from app.modules.ledger import service as ledger

    S = EscrowStatus
    rows = db.scalars(select(Order).where(Order.seller_id == seller.id, Order.paid_at.isnot(None))
                      .order_by(Order.created_at.desc()).limit(limit)).all()
    held = sum((o.escrow.seller_amount for o in rows if o.status in
                (S.AWAITING_SELLER, S.PROCESSING, S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION, S.DISPUTED)),
               start=0)
    return {
        "released_balance": f"{ledger.balance(db, ledger.seller_payable(seller.id)[0]):.2f}",
        "in_escrow": f"{held:.2f}",
        "note": "Released funds are paid out by our licensed escrow partner to your registered bank account.",
        "transactions": [{"order_id": str(o.id), "order_number": o.order_number, "status": o.status,
                          "gross": f"{o.subtotal + o.delivery_fee:.2f}",
                          "fees": f"{o.escrow.platform_amount - o.protection_fee:.2f}",
                          "net": f"{o.escrow.seller_amount:.2f}", "released_at": o.escrow.released_at,
                          "created_at": o.created_at} for o in rows],
    }
