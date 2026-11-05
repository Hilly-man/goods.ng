"""Price negotiation state machine.

Negotiation: open -> accepted -> converted (used by an order)
                  -> rejected | cancelled | expired
Offer:       pending -> accepted | rejected | countered | expired | withdrawn

Concurrency: every mutating action locks the negotiation row (SELECT ... FOR UPDATE) and requires
the client to name the offer it is responding to, so stale/double responses are rejected. The public
listing price is never modified.
"""

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, Conflict, Forbidden, InvalidState, NotFound
from app.core.security import clean_text
from app.core.time import utcnow
from app.models import Negotiation, Offer, Product, SellerProfile, User
from app.models.enums import NegotiationStatus, OfferParty, OfferStatus, ProductStatus
from app.modules.messaging.router import get_or_create_conversation, post_message
from app.modules.notifications.service import notify

MAX_ROUNDS = 10
MIN_OFFER_RATIO = Decimal("0.10")  # offers below 10% of list price are rejected as spam


def fmt(v: Decimal) -> str:
    return f"₦{v:,.0f}"


def _lock(db: Session, negotiation_id) -> Negotiation:
    neg = db.query(Negotiation).filter_by(id=negotiation_id).with_for_update().one_or_none()
    if not neg:
        raise NotFound("Negotiation not found")
    return neg


def _role(db: Session, neg: Negotiation, user: User) -> OfferParty:
    if neg.buyer_id == user.id:
        return OfferParty.BUYER
    seller = db.get(SellerProfile, neg.seller_id)
    if seller.user_id == user.id:
        return OfferParty.SELLER
    raise NotFound("Negotiation not found")


def _pending(neg: Negotiation) -> Offer | None:
    return next((o for o in neg.offers if o.status == OfferStatus.PENDING), None)


def expire_if_due(db: Session, neg: Negotiation) -> bool:
    now = utcnow()
    if neg.status == NegotiationStatus.OPEN:
        pend = _pending(neg)
        if pend and pend.expires_at <= now:
            pend.status = OfferStatus.EXPIRED
            neg.status = NegotiationStatus.EXPIRED
            return True
    if neg.status == NegotiationStatus.ACCEPTED and neg.checkout_expires_at and neg.checkout_expires_at <= now:
        neg.status = NegotiationStatus.EXPIRED
        return True
    return False


def _validate_amount(product: Product, amount: Decimal, by: OfferParty, last: Offer | None):
    if amount <= 0 or amount.as_tuple().exponent < -2:
        raise AppError("Enter a valid amount")
    if amount >= product.price:
        raise AppError("Offer must be below the listed price. Use Buy Now to pay the full price.", code="offer_too_high")
    if amount < (product.price * MIN_OFFER_RATIO):
        raise AppError("This offer is too low to send", code="offer_too_low")
    if last and by == OfferParty.SELLER and amount <= last.amount:
        raise AppError("Your counteroffer must be higher than the buyer's offer", code="counter_invalid")
    if last and by == OfferParty.BUYER and amount >= last.amount:
        raise AppError("Your counteroffer must be lower than the seller's offer", code="counter_invalid")


def _new_offer(neg, by, user, amount, note) -> Offer:
    now = utcnow()
    o = Offer(negotiation_id=neg.id, made_by=by, made_by_user_id=user.id, amount=amount, note=clean_text(note),
              expires_at=now + timedelta(hours=settings.offer_ttl_hours), created_at=now)
    neg.offers.append(o)
    return o


def start(db: Session, buyer: User, product_id, amount: Decimal, note: str | None) -> Negotiation:
    product = db.query(Product).filter_by(id=product_id).with_for_update().one_or_none()
    if not product or product.deleted_at or product.status != ProductStatus.ACTIVE:
        raise NotFound("Listing not available")
    if not product.negotiable:
        raise AppError("The seller has marked this price as fixed", code="not_negotiable")
    seller = db.get(SellerProfile, product.seller_id)
    if seller.user_id == buyer.id:
        raise AppError("You cannot make an offer on your own listing", code="own_listing")
    existing = db.scalars(select(Negotiation).where(
        Negotiation.product_id == product.id, Negotiation.buyer_id == buyer.id,
        Negotiation.status.in_([NegotiationStatus.OPEN, NegotiationStatus.ACCEPTED])).with_for_update()).first()
    if existing and not expire_if_due(db, existing):
        raise Conflict("You already have an active negotiation for this item", code="negotiation_exists",
                       details={"negotiation_id": str(existing.id)})
    db.flush()
    _validate_amount(product, amount, OfferParty.BUYER, None)
    conv, _ = get_or_create_conversation(db, product, buyer)
    neg = Negotiation(product_id=product.id, buyer_id=buyer.id, seller_id=seller.id, conversation_id=conv.id,
                      listed_price=product.price)
    db.add(neg)
    db.flush()
    o = _new_offer(neg, OfferParty.BUYER, buyer, amount, note)
    db.flush()
    post_message(db, conv, buyer.id, f"Offered {fmt(amount)}" + (f" — {o.note}" if o.note else ""), kind="offer",
                 offer_id=o.id)
    notify(db, seller.user_id, "new_offer", "New offer received",
           f"{buyer.full_name} offered {fmt(amount)} for {product.title[:60]} (listed {fmt(product.price)}).",
           link=f"/seller/offers/{neg.id}")
    db.commit()
    return neg


def respond(db: Session, user: User, negotiation_id, offer_id, action: str, amount: Decimal | None = None,
            note: str | None = None) -> Negotiation:
    neg = _lock(db, negotiation_id)
    role = _role(db, neg, user)
    if expire_if_due(db, neg):
        db.commit()
        raise InvalidState("This offer has expired", code="offer_expired")
    if neg.status != NegotiationStatus.OPEN:
        raise InvalidState(f"Negotiation is {neg.status.value}", code="negotiation_closed")
    pend = _pending(neg)
    if not pend or str(pend.id) != str(offer_id):
        raise Conflict("This offer has changed. Refresh to see the latest offer.", code="stale_offer")
    if pend.made_by == role:
        raise Forbidden("Waiting for the other party to respond", code="not_your_turn")
    product = db.get(Product, neg.product_id)
    now = utcnow()
    other_user = neg.buyer_id if role == OfferParty.SELLER else db.get(SellerProfile, neg.seller_id).user_id
    conv_id = neg.conversation_id
    from app.models import Conversation

    conv = db.get(Conversation, conv_id) if conv_id else None
    if action == "accept":
        if product.status != ProductStatus.ACTIVE or product.deleted_at:
            raise InvalidState("This listing is no longer available", code="listing_unavailable")
        pend.status, pend.responded_at = OfferStatus.ACCEPTED, now
        neg.status = NegotiationStatus.ACCEPTED
        neg.agreed_price = pend.amount
        neg.accepted_at = now
        neg.checkout_expires_at = now + timedelta(hours=settings.accepted_offer_checkout_hours)
        if conv:
            post_message(db, conv, user.id, f"Accepted offer of {fmt(pend.amount)}. Complete checkout within "
                                            f"{settings.accepted_offer_checkout_hours} hours.", kind="system")
        notify(db, other_user, "offer_accepted", "Offer accepted",
               f"{fmt(pend.amount)} agreed for {product.title[:60]}.",
               link=f"/checkout/{product.slug}?negotiation={neg.id}" if role == OfferParty.SELLER else f"/seller/offers/{neg.id}")
    elif action == "reject":
        pend.status, pend.responded_at = OfferStatus.REJECTED, now
        neg.status = NegotiationStatus.REJECTED
        if conv:
            post_message(db, conv, user.id, f"Declined offer of {fmt(pend.amount)}.", kind="system")
        notify(db, other_user, "offer_rejected", "Offer declined",
               f"Your offer of {fmt(pend.amount)} for {product.title[:60]} was declined.", link=f"/item/{product.slug}")
    elif action == "counter":
        if amount is None:
            raise AppError("Enter a counteroffer amount")
        if len(neg.offers) >= MAX_ROUNDS:
            raise AppError("Maximum negotiation rounds reached. Accept or decline the current offer.", code="max_rounds")
        _validate_amount(product, amount, role, pend)
        pend.status, pend.responded_at = OfferStatus.COUNTERED, now
        o = _new_offer(neg, role, user, amount, note)
        db.flush()
        if conv:
            post_message(db, conv, user.id, f"Counteroffer: {fmt(amount)}" + (f" — {o.note}" if o.note else ""),
                         kind="offer", offer_id=o.id)
        notify(db, other_user, "counter_offer", "New counteroffer",
               f"{fmt(amount)} proposed for {product.title[:60]}.",
               link=f"/offers/{neg.id}" if role == OfferParty.SELLER else f"/seller/offers/{neg.id}")
    else:
        raise AppError("Unknown action")
    db.commit()
    return neg


def withdraw(db: Session, user: User, negotiation_id) -> Negotiation:
    neg = _lock(db, negotiation_id)
    if _role(db, neg, user) != OfferParty.BUYER:
        raise Forbidden("Only the buyer can withdraw")
    if neg.status not in (NegotiationStatus.OPEN, NegotiationStatus.ACCEPTED):
        raise InvalidState("Negotiation already closed")
    pend = _pending(neg)
    if pend:
        pend.status = OfferStatus.WITHDRAWN
    neg.status = NegotiationStatus.CANCELLED
    db.commit()
    return neg


def checkout_price(db: Session, negotiation_id, buyer: User, product: Product, lock: bool = True) -> Negotiation:
    """Validate an accepted negotiation for checkout by this buyer and return it (row-locked)."""
    q = db.query(Negotiation).filter_by(id=negotiation_id)
    neg = (q.with_for_update() if lock else q).one_or_none()
    if not neg or neg.buyer_id != buyer.id or neg.product_id != product.id:
        raise NotFound("Accepted offer not found")
    expire_if_due(db, neg)
    if neg.status != NegotiationStatus.ACCEPTED or neg.agreed_price is None:
        raise InvalidState("This offer is not available for checkout", code="offer_not_accepted")
    return neg


def expire_due(db: Session) -> int:
    now = utcnow()
    n = 0
    ids = db.scalars(select(Negotiation.id).where(Negotiation.status.in_([NegotiationStatus.OPEN, NegotiationStatus.ACCEPTED]))).all()
    for nid in ids:
        neg = db.query(Negotiation).filter_by(id=nid).with_for_update(skip_locked=True).one_or_none()
        if neg and expire_if_due(db, neg):
            n += 1
    db.commit()
    _ = now
    return n
