"""Escrow state machine — the ONLY place order/escrow status changes happen.

    pending_payment ──> payment_confirmed ──> funds_safeguarded ──> awaiting_seller ──> processing ──> dispatched
          │                    │                     │                    │                 │              │
          └─> cancelled        └──────── refund_pending <─────────────────┴─────────────────┘              │
                                               │                                                        delivered
                                               v                                                           │
                                            refunded                       awaiting_buyer_confirmation <───┘
                                                                                     │  (auto-release after N days)
                       disputed  <── (from awaiting_seller … awaiting_buyer_confirmation)
                          ├─> completed (released to seller) · refund_pending (buyer refunded)
                          └─> back to where it was (dispute closed with no action)
                                                                                     v
                                                                                 completed

Guarantees (each one enforced in code and covered by tests):
* Every transition is checked against ALLOWED below and recorded as an immutable EscrowEvent.
* transition() refuses to run unless lock() row-locked the order + escrow in the same transaction.
* Release/refund check the money first: held amount == order total, and seller + platform splits add up.
* Settlement posts a ledger entry with a unique key per escrow — releasing or refunding twice is impossible,
  even under concurrent requests. The ledger itself is append-only and must balance (database triggers).
"""

from datetime import timedelta

from sqlalchemy import event, update
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.config import settings
from app.core.errors import InvalidState
from app.core.time import utcnow
from app.integrations.escrow import get_escrow_provider
from app.models import EscrowEvent, EscrowTransaction, Order, Product, SellerProfile
from app.models.enums import EscrowStatus as S
from app.models.enums import ProductStatus
from app.modules.ledger import service as ledger

ALLOWED: dict[S, set[S]] = {
    S.PENDING_PAYMENT: {S.PAYMENT_CONFIRMED, S.CANCELLED},
    S.PAYMENT_CONFIRMED: {S.FUNDS_SAFEGUARDED, S.REFUND_PENDING},
    S.FUNDS_SAFEGUARDED: {S.AWAITING_SELLER, S.REFUND_PENDING},
    S.AWAITING_SELLER: {S.PROCESSING, S.REFUND_PENDING, S.DISPUTED},
    S.PROCESSING: {S.DISPATCHED, S.REFUND_PENDING, S.DISPUTED},
    S.DISPATCHED: {S.DELIVERED, S.COMPLETED, S.DISPUTED},
    S.DELIVERED: {S.AWAITING_BUYER_CONFIRMATION, S.COMPLETED, S.DISPUTED},
    S.AWAITING_BUYER_CONFIRMATION: {S.COMPLETED, S.DISPUTED},
    S.DISPUTED: {S.COMPLETED, S.REFUND_PENDING, S.AWAITING_SELLER, S.PROCESSING, S.DISPATCHED, S.DELIVERED,
                 S.AWAITING_BUYER_CONFIRMATION},
    S.REFUND_PENDING: {S.REFUNDED},
    S.COMPLETED: set(),
    S.REFUNDED: set(),
    S.CANCELLED: set(),
}

FUNDED_STATES = {S.AWAITING_SELLER, S.PROCESSING, S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION, S.DISPUTED}


_LOCKED = "escrow_locked_orders"


@event.listens_for(Session, "after_commit")
@event.listens_for(Session, "after_rollback")
def _forget_locks(session: Session) -> None:
    session.info.pop(_LOCKED, None)  # row locks end with the transaction, so does our record of them


def lock(db: Session, order_id) -> tuple[Order, EscrowTransaction]:
    """SELECT ... FOR UPDATE the order and its escrow. Required before any transition (enforced)."""
    order = db.query(Order).filter_by(id=order_id).with_for_update().one()
    esc = db.query(EscrowTransaction).filter_by(order_id=order.id).with_for_update().one()
    db.info.setdefault(_LOCKED, set()).add(order.id)
    return order, esc


def _check_money(order: Order, esc: EscrowTransaction) -> None:
    """Settlement invariants: the held amount is exactly what the buyer paid, and splits add up."""
    if esc.amount != order.total or esc.amount <= 0:
        raise InvalidState("Escrow amount doesn't match the order total", code="escrow_amount_mismatch")
    if esc.seller_amount < 0 or esc.platform_amount < order.protection_fee \
            or esc.seller_amount + esc.platform_amount != esc.amount:
        raise InvalidState("Escrow split doesn't add up", code="escrow_split_mismatch")


def transition(db: Session, order: Order, esc: EscrowTransaction, to: S, *, actor_id=None, actor_role="system",
               note: str | None = None) -> None:
    if order.id not in db.info.get(_LOCKED, ()) or esc.order_id != order.id:
        # Programming error, not user error: fail closed rather than risk a race on money.
        raise RuntimeError("escrow.transition() called without escrow.lock() in this transaction")
    frm = esc.status
    if to not in ALLOWED[frm]:
        raise InvalidState(f"Cannot move order from {frm.value} to {to.value}", code="invalid_transition")
    esc.status = to
    order.status = to
    db.add(EscrowEvent(escrow_id=esc.id, from_status=frm.value, to_status=to.value, actor_id=actor_id,
                       actor_role=actor_role, note=note, created_at=utcnow()))


def fund(db: Session, order: Order, esc: EscrowTransaction, payment_reference: str) -> None:
    """Payment verified -> safeguard funds with the escrow partner -> await seller."""
    transition(db, order, esc, S.PAYMENT_CONFIRMED, actor_role="provider", note=f"Payment {payment_reference} verified")
    hold = get_escrow_provider().create_hold(order_reference=order.order_number, payment_reference=payment_reference,
                                             amount=esc.amount)
    esc.provider_escrow_ref = hold.reference
    esc.funded_at = utcnow()
    order.paid_at = esc.funded_at
    ledger.post(db, key=f"escrow:{esc.id}:funded", kind="escrow_funded", reference=order.order_number,
                description=f"Protected checkout funds held for order {order.order_number}",
                legs=[ledger.debit(ledger.ESCROW_HOLDING, esc.amount),
                      ledger.credit(ledger.ESCROW_OBLIGATIONS, esc.amount)])
    transition(db, order, esc, S.FUNDS_SAFEGUARDED, actor_role="provider", note=f"Held by escrow partner ({hold.reference})")
    transition(db, order, esc, S.AWAITING_SELLER, actor_role="system")


def mark_delivered(db: Session, order: Order, esc: EscrowTransaction, actor_id, actor_role) -> None:
    transition(db, order, esc, S.DELIVERED, actor_id=actor_id, actor_role=actor_role)
    transition(db, order, esc, S.AWAITING_BUYER_CONFIRMATION, actor_role="system",
               note=f"Funds auto-release in {settings.auto_release_days} days unless a dispute is raised")
    esc.release_eligible_at = utcnow() + timedelta(days=settings.auto_release_days)


def release(db: Session, order: Order, esc: EscrowTransaction, *, actor_id=None, actor_role="system",
            note: str | None = None) -> None:
    """Release funds to seller. Only valid from delivery/confirmation/dispute states."""
    _check_money(order, esc)
    if not esc.funded_at:
        raise InvalidState("Can't release funds that were never received", code="escrow_not_funded")
    transition(db, order, esc, S.COMPLETED, actor_id=actor_id, actor_role=actor_role, note=note)
    get_escrow_provider().release(escrow_reference=esc.provider_escrow_ref, seller_amount=esc.seller_amount,
                                  platform_amount=esc.platform_amount, seller_ref=str(order.seller_id))
    ledger.post(db, key=f"escrow:{esc.id}:settle", kind="escrow_released", reference=order.order_number,
                description=f"Funds released for order {order.order_number}",
                legs=[ledger.debit(ledger.ESCROW_OBLIGATIONS, esc.amount),
                      ledger.credit(ledger.seller_payable(order.seller_id), esc.seller_amount),
                      ledger.credit(ledger.COMMISSION, esc.platform_amount - order.protection_fee),
                      ledger.credit(ledger.PROTECTION_FEES, order.protection_fee)])
    now = utcnow()
    esc.released_at = order.completed_at = now
    db.execute(update(SellerProfile).where(SellerProfile.id == order.seller_id)
               .values(completed_sales=SellerProfile.completed_sales + 1))
    for item in order.items:
        db.execute(update(Product).where(Product.id == item.product_id, Product.quantity == 0,
                                         Product.status == ProductStatus.ACTIVE).values(status=ProductStatus.SOLD))
    if order.payment_method == "bnpl":
        from app.modules.bnpl.service import schedule_seller_holds

        schedule_seller_holds(db, order, esc)
    cache.invalidate("feed:")


def settle_refund(db: Session, order: Order, esc: EscrowTransaction, *, actor_id=None, actor_role="system",
                  note: str | None = None) -> None:
    """Called once the refund has been executed by the provider."""
    if esc.funded_at:
        _check_money(order, esc)
    transition(db, order, esc, S.REFUNDED, actor_id=actor_id, actor_role=actor_role, note=note)
    if esc.funded_at:
        get_escrow_provider().refund(escrow_reference=esc.provider_escrow_ref, amount=esc.amount, reason=note or "refund")
        ledger.post(db, key=f"escrow:{esc.id}:settle", kind="escrow_refunded", reference=order.order_number,
                    description=f"Funds returned to buyer for order {order.order_number}",
                    legs=[ledger.debit(ledger.ESCROW_OBLIGATIONS, esc.amount),
                          ledger.credit(ledger.ESCROW_HOLDING, esc.amount)])
    esc.refunded_at = utcnow()
    if not (order.delivery and order.delivery.dispatched_at):
        restore_stock(db, order)  # item never left the seller: make it available again


def restore_stock(db: Session, order: Order) -> None:
    if not order.stock_reserved:
        return
    for item in order.items:
        db.execute(update(Product).where(Product.id == item.product_id)
                   .values(quantity=Product.quantity + item.quantity))
        db.execute(update(Product).where(Product.id == item.product_id, Product.status == ProductStatus.SOLD)
                   .values(status=ProductStatus.ACTIVE))
    order.stock_reserved = False
