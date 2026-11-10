import secrets
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, Forbidden, InvalidState, NotFound
from app.core.security import clean_text, decrypt_field, encrypt_field
from app.core.time import utcnow
from app.integrations.delivery import get_delivery_provider
from app.models import (
    DeliveryRecord,
    Dispute,
    DisputeMessage,
    EscrowTransaction,
    Negotiation,
    Order,
    OrderItem,
    Payment,
    PlatformSetting,
    Product,
    Refund,
    SellerProfile,
    User,
)
from app.models.enums import (
    DeliveryStatus,
    DisputeReason,
    DisputeStatus,
    EscrowStatus,
    NegotiationStatus,
    PaymentMethod,
    PaymentPurpose,
    PaymentStatus,
    ProductStatus,
    RefundStatus,
)
from app.models.enums import EscrowStatus as S
from app.modules.common import money
from app.modules.locations import canonical_city
from app.modules.negotiation import service as negotiation
from app.modules.notifications.service import notify
from app.modules.orders import escrow
from app.modules.payments import service as payments


# ---------------- pricing (server-side only) ----------------
def fee_config(db: Session) -> dict:
    row = db.get(PlatformSetting, "fees")
    v = row.value if row else {}
    return {
        "commission_rate": Decimal(str(v.get("commission_rate", settings.platform_commission_rate))),
        "protection_fee_rate": Decimal(str(v.get("protection_fee_rate", settings.protection_fee_rate))),
        "protection_fee_cap": Decimal(str(v.get("protection_fee_cap", settings.protection_fee_cap))),
    }


def price_checkout(db: Session, buyer: User, product: Product, quantity: int, negotiation_id, delivery_index: int,
                   lock_negotiation: bool = False) -> dict:
    if product.deleted_at or product.status != ProductStatus.ACTIVE:
        raise InvalidState("This listing is no longer available", code="listing_unavailable")
    if not product.protected_checkout_enabled:
        raise AppError("Protected Checkout is not available for this listing", code="checkout_unavailable")
    seller = db.get(SellerProfile, product.seller_id)
    if seller.user_id == buyer.id:
        raise AppError("You cannot buy your own listing", code="own_listing")
    if seller.is_suspended:
        raise InvalidState("This seller is not currently accepting orders")
    if quantity < 1:
        raise AppError("Quantity must be at least 1")
    if quantity > product.quantity:
        raise InvalidState("Not enough stock available", code="insufficient_stock")
    unit_price, neg = product.price, None
    if negotiation_id:
        neg = negotiation.checkout_price(db, negotiation_id, buyer, product, lock=lock_negotiation)
        if quantity != 1:
            raise AppError("Agreed offer prices apply to a single item")
        unit_price = neg.agreed_price
    opts = product.delivery_options or []
    if not (0 <= delivery_index < len(opts)):
        raise AppError("Select a delivery option", code="invalid_delivery_option")
    option = opts[delivery_index]
    fees = fee_config(db)
    subtotal = money(unit_price * quantity)
    # "Arrange with seller" means delivery is planned and paid outside the app.
    delivery_fee = Decimal("0") if option.get("type") == "arrange" else money(option.get("fee", 0))
    protection_fee = min(money(subtotal * fees["protection_fee_rate"]), fees["protection_fee_cap"])
    commission = money(subtotal * fees["commission_rate"])
    total = subtotal + delivery_fee + protection_fee
    return {
        "product_id": product.id, "unit_price": unit_price, "listed_price": product.price, "quantity": quantity,
        "subtotal": subtotal, "delivery_fee": delivery_fee, "protection_fee": protection_fee, "total": total,
        "commission": commission, "commission_rate": fees["commission_rate"], "delivery_option": option,
        "negotiation": neg, "seller": seller,
    }


def _order_number() -> str:
    return f"GNG{utcnow():%y%m}{secrets.randbelow(10**6):06d}"


def create_checkout(db: Session, buyer: User, *, product_id, quantity: int, negotiation_id, delivery_index: int,
                    address: dict | None, note: str | None, idempotency_key: str | None,
                    payment_method: PaymentMethod = PaymentMethod.FULL) -> tuple[Order, Payment | None]:
    from app.core.deps import ensure_customer

    ensure_customer(buyer)
    if not buyer.email_verified:
        raise Forbidden("Verify your email address before checkout", code="email_unverified")
    if not buyer.phone_verified:
        raise Forbidden("Verify your phone number before checkout", code="phone_unverified")
    if idempotency_key:
        existing = db.scalars(select(Order).where(Order.buyer_id == buyer.id,
                                                  Order.idempotency_key == idempotency_key)).first()
        if existing:
            pay = db.scalars(select(Payment).where(Payment.order_id == existing.id)
                             .order_by(Payment.created_at.desc())).first()
            return existing, pay
    if negotiation_id:
        live = db.scalars(select(Order).where(Order.negotiation_id == negotiation_id,
                                              Order.status != EscrowStatus.CANCELLED)).first()
        if live:
            if live.buyer_id != buyer.id:
                raise NotFound("Accepted offer not found")
            pay = db.scalars(select(Payment).where(Payment.order_id == live.id).order_by(Payment.created_at.desc())).first()
            return live, pay
    product = db.query(Product).filter_by(id=product_id).with_for_update().one_or_none()
    if not product:
        raise NotFound("Listing not found")
    q = price_checkout(db, buyer, product, quantity, negotiation_id, delivery_index, lock_negotiation=True)
    arranging = q["delivery_option"].get("type") == "arrange"
    if arranging:
        address = {}  # delivery is planned directly between buyer and seller
    else:
        if not address:
            raise AppError("Add a delivery address", code="address_required")
        address = {**address, "city": canonical_city(db, address.get("state"), address.get("city"),
                                                     field="address.city")}
    if payment_method == PaymentMethod.BNPL and not product.bnpl_enabled:
        raise AppError("Goods Flex is not available for this listing", code="bnpl_unavailable")
    # Reserve stock atomically.
    res = db.execute(update(Product).where(Product.id == product.id, Product.quantity >= quantity)
                     .values(quantity=Product.quantity - quantity))
    if res.rowcount != 1:
        raise InvalidState("Not enough stock available", code="insufficient_stock")
    seller: SellerProfile = q["seller"]
    order = Order(
        order_number=_order_number(), buyer_id=buyer.id, seller_id=seller.id,
        negotiation_id=q["negotiation"].id if q["negotiation"] else None, payment_method=payment_method,
        subtotal=q["subtotal"], delivery_fee=q["delivery_fee"], protection_fee=q["protection_fee"], total=q["total"],
        commission_rate=q["commission_rate"], delivery_option=q["delivery_option"], delivery_address=address,
        buyer_note=clean_text(note), stock_reserved=True, idempotency_key=idempotency_key,
        expires_at=utcnow() + timedelta(minutes=settings.unpaid_order_ttl_minutes if payment_method == PaymentMethod.FULL
                                        else 60 * 24),
    )
    order.items.append(OrderItem(product_id=product.id, title=product.title,
                                 image_url=product.images[0].thumb_url if product.images else None,
                                 unit_price=q["unit_price"], listed_price=product.price, quantity=quantity,
                                 line_total=q["subtotal"]))
    db.add(order)
    db.flush()
    platform_amount = q["commission"] + q["protection_fee"]
    esc = EscrowTransaction(order_id=order.id, provider=settings.escrow_provider, amount=q["total"],
                            seller_amount=q["total"] - platform_amount, platform_amount=platform_amount)
    db.add(esc)
    db.add(DeliveryRecord(order_id=order.id, method=q["delivery_option"].get("type", "pickup")))
    db.flush()
    from app.models import EscrowEvent

    db.add(EscrowEvent(escrow_id=esc.id, from_status=None, to_status=S.PENDING_PAYMENT.value, actor_id=buyer.id,
                       actor_role="buyer", note="Protected checkout started", created_at=utcnow()))
    pay = None
    if payment_method == PaymentMethod.FULL:
        pay = payments.create_payment(db, user=buyer, purpose=PaymentPurpose.ORDER, amount=order.total,
                                      order_id=order.id, callback_path=f"/orders/{order.id}/payment",
                                      metadata={"order": order.order_number})
    db.commit()
    return order, pay


@payments.on_success(PaymentPurpose.ORDER)
def _order_paid(db: Session, payment: Payment) -> None:
    order, esc = escrow.lock(db, payment.order_id)
    on_order_funded(db, order, esc, payment)


def on_order_funded(db: Session, order: Order, esc: EscrowTransaction, payment: Payment) -> None:
    if esc.status == S.CANCELLED:
        # Paid after the unpaid order expired: re-reserve if possible, else refund automatically.
        item = order.items[0]
        res = db.execute(update(Product).where(Product.id == item.product_id, Product.quantity >= item.quantity,
                                               Product.status == ProductStatus.ACTIVE)
                         .values(quantity=Product.quantity - item.quantity))
        if res.rowcount != 1:
            _auto_refund_late_payment(db, order, payment)
            return
        order.stock_reserved = True
        esc.status = order.status = S.PENDING_PAYMENT
        order.cancelled_at = None
    if esc.status != S.PENDING_PAYMENT:
        return
    escrow.fund(db, order, esc, payment.reference)
    if order.negotiation_id:
        db.execute(update(Negotiation).where(Negotiation.id == order.negotiation_id)
                   .values(status=NegotiationStatus.CONVERTED, version=Negotiation.version + 1))
    seller = db.get(SellerProfile, order.seller_id)
    notify(db, order.buyer_id, "payment_confirmed", "Payment confirmed",
           f"Order {order.order_number}: ₦{order.total:,.2f} is safeguarded until you confirm delivery.",
           link=f"/orders/{order.id}")
    notify(db, seller.user_id, "new_order", "New protected order",
           f"Order {order.order_number} for {order.items[0].title[:60]} is paid. Please accept and prepare it.",
           link=f"/seller/orders/{order.id}")


def _auto_refund_late_payment(db: Session, order: Order, payment: Payment) -> None:
    refund = Refund(order_id=order.id, payment_id=payment.id, amount=payment.amount, requested_by_id=order.buyer_id,
                    reason="Payment received after order expired and item no longer available",
                    status=RefundStatus.PROCESSING, approved_at=utcnow())
    db.add(refund)
    result = payments.refund_payment(db, payment, payment.amount, refund.reason)
    refund.provider_refund_ref = result.provider_refund_ref
    refund.status = RefundStatus.COMPLETED if result.status == "completed" else RefundStatus.PROCESSING
    refund.completed_at = utcnow() if refund.status == RefundStatus.COMPLETED else None
    notify(db, order.buyer_id, "refund", "Payment refunded",
           f"Your payment for order {order.order_number} arrived after the item was sold. A full refund has been issued.",
           link=f"/orders/{order.id}")


@payments.on_failure(PaymentPurpose.ORDER)
def _order_payment_failed(db: Session, payment: Payment) -> None:
    order = db.get(Order, payment.order_id)
    if order:
        notify(db, order.buyer_id, "order_update", "Payment not completed",
               f"Payment for order {order.order_number} was not successful. You can retry from your orders page.",
               link=f"/orders/{order.id}")


def retry_payment(db: Session, buyer: User, order_id) -> Payment:
    order, esc = escrow.lock(db, order_id)
    if order.buyer_id != buyer.id:
        raise NotFound("Order not found")
    if esc.status != S.PENDING_PAYMENT or order.payment_method != PaymentMethod.FULL:
        raise InvalidState("This order is not awaiting payment")
    if order.expires_at and order.expires_at < utcnow():
        raise InvalidState("This checkout has expired. Please start again.", code="checkout_expired")
    pending = db.scalars(select(Payment).where(Payment.order_id == order.id,
                                               Payment.status == PaymentStatus.INITIALIZED)).all()
    for p in pending:
        payments.confirm_payment(db, p.reference)  # never abandon a payment that actually succeeded
        db.refresh(esc)
        if esc.status != S.PENDING_PAYMENT:
            raise InvalidState("This order has already been paid", code="already_paid")
    pay = payments.create_payment(db, user=buyer, purpose=PaymentPurpose.ORDER, amount=order.total, order_id=order.id,
                                  callback_path=f"/orders/{order.id}/payment", metadata={"order": order.order_number})
    db.commit()
    return pay


# ---------------- access ----------------
def get_for(db: Session, user: User, order_id) -> tuple[Order, str]:
    order = db.get(Order, order_id)
    if not order:
        raise NotFound("Order not found")
    if order.buyer_id == user.id:
        return order, "buyer"
    seller = db.get(SellerProfile, order.seller_id)
    if seller.user_id == user.id:
        return order, "seller"
    if user.is_admin and user.has_permission("orders.view"):
        return order, "admin"
    raise NotFound("Order not found")


def _seller_user(db, order) -> SellerProfile:
    return db.get(SellerProfile, order.seller_id)


# ---------------- seller actions ----------------
def seller_accept(db: Session, user: User, order_id) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "seller":
        raise Forbidden("Only the seller can accept this order")
    order, esc = escrow.lock(db, order.id)
    escrow.transition(db, order, esc, S.PROCESSING, actor_id=user.id, actor_role="seller", note="Seller accepted order")
    notify(db, order.buyer_id, "order_update", "Seller is preparing your order",
           f"Order {order.order_number} has been accepted by the seller.", link=f"/orders/{order.id}")
    db.commit()
    return order


def seller_dispatch(db: Session, user: User, order_id, carrier: str | None, tracking: str | None,
                    tracking_url: str | None, notes: str | None) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "seller":
        raise Forbidden("Only the seller can dispatch this order")
    order, esc = escrow.lock(db, order.id)
    d = order.delivery
    if d.method == "courier" and not tracking:
        raise AppError("A tracking reference is required for courier deliveries", code="tracking_required")
    escrow.transition(db, order, esc, S.DISPATCHED, actor_id=user.id, actor_role="seller",
                      note=f"Dispatched via {carrier or d.method}" + (f" ({tracking})" if tracking else ""))
    now = utcnow()
    d.status, d.carrier, d.tracking_reference, d.tracking_url = DeliveryStatus.DISPATCHED, clean_text(carrier), \
        clean_text(tracking), tracking_url
    d.notes, d.dispatched_at = clean_text(notes), now
    if settings.environment in ("development", "test"):
        # No live carrier is configured yet. Production falls back to the buyer PIN only, never a fake
        # mock shipment; a real adapter (Shipbubble/GIG/Fez) will populate these fields.
        shipment = get_delivery_provider().create_shipment(
            order_reference=order.order_number, carrier=carrier, tracking_reference=tracking)
        d.provider, d.provider_reference = get_delivery_provider().name, shipment.reference
        d.tracking_url = tracking_url or shipment.tracking_url
    pin = f"{secrets.randbelow(10 ** 6):06d}"
    d.pin_enc, d.pin_attempts, d.pin_expires_at = encrypt_field(pin), 0, now + timedelta(days=14)
    d.updates = [*d.updates, {"at": now.isoformat(), "status": "dispatched", "note": clean_text(notes) or ""}]
    notify(db, order.buyer_id, "seller_dispatch", "Your order is on the way",
           f"Order {order.order_number} has been dispatched. Open the order to see your delivery PIN and share it "
           "only when the item is handed over.",
           link=f"/orders/{order.id}")
    db.commit()
    return order


def add_delivery_update(db: Session, user: User, order_id, note: str) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "seller":
        raise Forbidden("Only the seller can post delivery updates")
    if order.status not in (S.DISPATCHED,):
        raise InvalidState("Delivery updates are only possible while the order is in transit")
    d = order.delivery
    d.status = DeliveryStatus.IN_TRANSIT
    d.updates = [*d.updates, {"at": utcnow().isoformat(), "status": "in_transit", "note": clean_text(note)}]
    notify(db, order.buyer_id, "delivery_update", "Delivery update", f"{order.order_number}: {clean_text(note)[:140]}",
           link=f"/orders/{order.id}")
    db.commit()
    return order


def _verify_delivery_pin(db: Session, d: DeliveryRecord, pin: str | None) -> None:
    """The buyer-only PIN proves physical handover. Five wrong attempts lock the order for support."""
    if not d.pin_enc or not d.pin_expires_at:
        raise InvalidState("This order has no delivery PIN; contact support", code="delivery_pin_missing")
    if d.pin_expires_at < utcnow():
        raise AppError("The delivery PIN has expired; contact support", code="delivery_pin_expired")
    if d.pin_attempts >= 5:
        raise AppError("Too many incorrect delivery PIN attempts; contact support", code="delivery_pin_locked")
    if not pin or decrypt_field(d.pin_enc) != pin:
        d.pin_attempts += 1
        db.commit()
        raise AppError("The delivery PIN is incorrect", code="invalid_delivery_pin")
    d.pin_verified_at = utcnow()


def _mark_delivered(db: Session, order: Order, esc: EscrowTransaction, *, actor_id, actor_role,
                    evidence_urls: list[str], notes: str | None) -> None:
    escrow.mark_delivered(db, order, esc, actor_id, actor_role)
    d = order.delivery
    now = utcnow()
    d.status, d.delivered_at = DeliveryStatus.DELIVERED, now
    d.evidence_urls = [*d.evidence_urls, *evidence_urls]
    d.updates = [*d.updates, {"at": now.isoformat(), "status": "delivered", "note": clean_text(notes) or ""}]
    notify(db, order.buyer_id, "delivery_update", "Order delivered — please confirm",
           f"Order {order.order_number} was marked delivered. Confirm receipt or report a problem within "
           f"{settings.auto_release_days} days.", link=f"/orders/{order.id}")


def seller_mark_delivered(db: Session, user: User, order_id, evidence_urls: list[str], notes: str | None,
                          pin: str | None = None) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "seller":
        raise Forbidden("Only the seller can mark delivery")
    order, esc = escrow.lock(db, order.id)
    _verify_delivery_pin(db, order.delivery, pin)
    _mark_delivered(db, order, esc, actor_id=user.id, actor_role="seller",
                    evidence_urls=evidence_urls, notes=notes)
    db.commit()
    return order


def delivery_webhook(db: Session, event) -> int:
    """Handle a carrier event. A verified carrier delivery does not need the buyer's PIN."""
    if event.status != "delivered":
        return 0
    order = db.scalars(select(Order).where(Order.order_number == event.order_reference)).first()
    if not order or order.status in (S.COMPLETED, S.REFUNDED, S.CANCELLED):
        return 0
    order, esc = escrow.lock(db, order.id)
    if esc.status not in (S.DISPATCHED, S.DELIVERED):
        db.rollback()
        return 0
    if order.status == S.DISPATCHED:
        _mark_delivered(db, order, esc, actor_id=None, actor_role="provider", evidence_urls=[], notes="Carrier webhook")
    db.commit()
    return 1


def seller_decline(db: Session, user: User, order_id, reason: str) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "seller":
        raise Forbidden("Only the seller can decline this order")
    order, esc = escrow.lock(db, order.id)
    if esc.status not in (S.AWAITING_SELLER, S.PROCESSING):
        raise InvalidState("This order can no longer be declined")
    _system_refund(db, order, esc, f"Seller declined: {clean_text(reason)}", actor_id=user.id, actor_role="seller")
    db.commit()
    return order


# ---------------- buyer actions ----------------
def buyer_confirm(db: Session, user: User, order_id) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "buyer":
        raise Forbidden("Only the buyer can confirm receipt")
    order, esc = escrow.lock(db, order.id)
    if esc.status not in (S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION):
        raise InvalidState("This order cannot be confirmed right now", code="invalid_transition")
    if esc.status == S.DISPATCHED:
        d = order.delivery
        d.status, d.delivered_at = DeliveryStatus.DELIVERED, utcnow()
    escrow.release(db, order, esc, actor_id=user.id, actor_role="buyer", note="Buyer confirmed receipt")
    _notify_release(db, order)
    db.commit()
    return order


def _notify_release(db, order):
    seller = _seller_user(db, order)
    notify(db, seller.user_id, "funds_released", "Funds released",
           f"Order {order.order_number} is complete. Your earnings have been released for payout.",
           link=f"/seller/orders/{order.id}")
    notify(db, order.buyer_id, "order_update", "Order completed",
           f"Thanks for confirming order {order.order_number}. You can now leave a review.", link=f"/orders/{order.id}")


def buyer_cancel(db: Session, user: User, order_id, reason: str | None) -> Order:
    order, role = get_for(db, user, order_id)
    if role != "buyer":
        raise Forbidden("Only the buyer can cancel this order")
    order, esc = escrow.lock(db, order.id)
    if esc.status == S.PENDING_PAYMENT:
        cancel_unpaid(db, order, esc, actor_id=user.id, actor_role="buyer", reason=reason or "Cancelled by buyer")
    elif esc.status == S.AWAITING_SELLER:
        _system_refund(db, order, esc, f"Buyer cancelled before seller acceptance: {clean_text(reason) or ''}",
                       actor_id=user.id, actor_role="buyer")
    else:
        raise InvalidState("Once the seller has accepted, please contact them or open a dispute", code="cannot_cancel")
    db.commit()
    return order


def cancel_unpaid(db: Session, order: Order, esc: EscrowTransaction, *, actor_id=None, actor_role="system",
                  reason="Payment window expired") -> None:
    escrow.transition(db, order, esc, S.CANCELLED, actor_id=actor_id, actor_role=actor_role, note=reason)
    order.cancelled_at, order.cancellation_reason = utcnow(), reason
    escrow.restore_stock(db, order)
    db.execute(update(Payment).where(Payment.order_id == order.id, Payment.status == PaymentStatus.INITIALIZED)
               .values(status=PaymentStatus.ABANDONED))


def _system_refund(db: Session, order: Order, esc: EscrowTransaction, reason: str, *, actor_id, actor_role) -> Refund:
    """Full refund for low-risk pre-dispatch cases (seller decline / buyer cancel before acceptance)."""
    escrow.transition(db, order, esc, S.REFUND_PENDING, actor_id=actor_id, actor_role=actor_role, note=reason)
    order.cancelled_at, order.cancellation_reason = utcnow(), reason
    payment = _paid_payment(db, order)
    refund = Refund(order_id=order.id, payment_id=payment.id, amount=payment.amount, reason=reason[:300],
                    requested_by_id=actor_id or order.buyer_id, status=RefundStatus.APPROVED, approved_at=utcnow())
    db.add(refund)
    db.flush()
    execute_refund(db, refund, order, esc)
    return refund


def _paid_payment(db, order) -> Payment:
    p = db.scalars(select(Payment).where(Payment.order_id == order.id, Payment.status.in_(
        [PaymentStatus.SUCCESS, PaymentStatus.PARTIALLY_REFUNDED]))).first()
    if p:
        return p
    # BNPL orders: the down payment is the buyer's payment; financed portion is unwound with the lender.
    p = db.scalars(select(Payment).where(Payment.order_id == order.id, Payment.purpose == PaymentPurpose.BNPL_DOWN_PAYMENT,
                                         Payment.status == PaymentStatus.SUCCESS)).first()
    if not p:
        raise InvalidState("No completed payment found for this order")
    return p


def execute_refund(db: Session, refund: Refund, order: Order, esc: EscrowTransaction, actor_id=None,
                   actor_role="system") -> None:
    if refund.status != RefundStatus.APPROVED:
        raise InvalidState("Refund is not approved")
    payment = db.get(Payment, refund.payment_id)
    refund.status = RefundStatus.PROCESSING
    amount = min(refund.amount, payment.amount - payment.amount_refunded)
    if amount > 0:
        result = payments.refund_payment(db, payment, amount, refund.reason)
        refund.provider_refund_ref = result.provider_refund_ref
    if order.payment_method == PaymentMethod.BNPL:
        from app.modules.bnpl.service import cancel_financing_for_order

        cancel_financing_for_order(db, order, refund.reason)
    refund.status = RefundStatus.COMPLETED
    refund.completed_at = utcnow()
    escrow.settle_refund(db, order, esc, actor_id=actor_id, actor_role=actor_role, note=refund.reason)
    notify(db, order.buyer_id, "refund", "Refund issued",
           f"₦{refund.amount:,.2f} for order {order.order_number} has been refunded to your original payment method.",
           link=f"/orders/{order.id}")
    seller = _seller_user(db, order)
    notify(db, seller.user_id, "refund", "Order refunded", f"Order {order.order_number} was refunded to the buyer.",
           link=f"/seller/orders/{order.id}")


# ---------------- disputes ----------------
BUYER_DISPUTABLE = {S.AWAITING_SELLER, S.PROCESSING, S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION}
SELLER_DISPUTABLE = {S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION}


def post_delivery_complaint(db: Session, user: User, order_id, description: str):
    """A buyer can freeze the seller's just-released payout during the clearing window."""
    from app.modules.wallet import service as wallet

    order, role = get_for(db, user, order_id)
    if role != "buyer":
        raise Forbidden("Only the buyer can raise a complaint")
    if not wallet.complaint_window_open(order):
        raise InvalidState("The complaint window for this order has closed", code="complaint_window_closed")
    existing = db.query(wallet.WalletHold).filter_by(order_id=order.id, released_at=None).first()
    if existing:
        raise AppError("A complaint is already open for this order", code="complaint_exists")
    hold = wallet.place_hold(db, seller_id=order.seller_id, amount=order.escrow.seller_amount,
                             reason="post_delivery_claim", order_id=order.id, note=clean_text(description),
                             created_by_id=user.id, freeze=True)
    seller_user = _seller_user(db, order)
    notify(db, seller_user.user_id, "payout_hold", "Payout on hold",
           f"A buyer complaint on order {order.order_number} is under review. Withdrawals are paused meanwhile.",
           link=f"/seller/orders/{order.id}")
    db.commit()
    return hold


def open_dispute(db: Session, user: User, order_id, reason: DisputeReason, description: str,
                 evidence_urls: list[str]) -> Dispute:
    order, role = get_for(db, user, order_id)
    if role not in ("buyer", "seller"):
        raise Forbidden("Only the buyer or seller can open a dispute")
    order, esc = escrow.lock(db, order.id)
    allowed = BUYER_DISPUTABLE if role == "buyer" else SELLER_DISPUTABLE
    if esc.status not in allowed:
        raise InvalidState("A dispute cannot be opened at this stage", code="cannot_dispute")
    prev = esc.status
    escrow.transition(db, order, esc, S.DISPUTED, actor_id=user.id, actor_role=role, note=f"Dispute: {reason.value}")
    d = Dispute(order_id=order.id, opened_by_id=user.id, opened_by_role=role, reason=reason,
                description=clean_text(description), previous_order_status=prev.value)
    db.add(d)
    db.flush()
    db.add(DisputeMessage(dispute_id=d.id, author_id=user.id, author_role=role, body=clean_text(description),
                          evidence_urls=evidence_urls, created_at=utcnow()))
    other = _seller_user(db, order).user_id if role == "buyer" else order.buyer_id
    for uid in (order.buyer_id, _seller_user(db, order).user_id):
        notify(db, uid, "dispute", "Dispute opened",
               f"A dispute was opened on order {order.order_number}. Funds remain safeguarded while Goods.ng reviews it.",
               link=f"/orders/{order.id}" if uid == order.buyer_id else f"/seller/orders/{order.id}")
    _ = other
    db.commit()
    return d


def add_dispute_message(db: Session, user: User, dispute_id, body: str, evidence_urls: list[str]) -> DisputeMessage:
    d = db.get(Dispute, dispute_id)
    if not d:
        raise NotFound("Dispute not found")
    _, role = get_for(db, user, d.order_id)
    if d.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
        raise InvalidState("This dispute is closed")
    m = DisputeMessage(dispute_id=d.id, author_id=user.id, author_role=role, body=clean_text(body),
                       evidence_urls=evidence_urls, created_at=utcnow())
    db.add(m)
    db.commit()
    return m


def resolve_dispute(db: Session, admin: User, dispute_id, outcome: str, notes: str) -> Dispute:
    d = db.query(Dispute).filter_by(id=dispute_id).with_for_update().one_or_none()
    if not d:
        raise NotFound("Dispute not found")
    if d.status not in (DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW):
        raise InvalidState("Dispute already resolved")
    order, esc = escrow.lock(db, d.order_id)
    now = utcnow()
    d.resolution_notes, d.resolved_by_id, d.resolved_at = clean_text(notes), admin.id, now
    if outcome == "release_to_seller":
        d.status = DisputeStatus.RESOLVED_SELLER
        escrow.release(db, order, esc, actor_id=admin.id, actor_role="admin", note=f"Dispute resolved for seller: {notes}")
        _notify_release(db, order)
    elif outcome == "refund_buyer":
        d.status = DisputeStatus.RESOLVED_BUYER
        escrow.transition(db, order, esc, S.REFUND_PENDING, actor_id=admin.id, actor_role="admin",
                          note=f"Dispute resolved for buyer: {notes}")
        payment = _paid_payment(db, order)
        # Dispute refunds require a second, independent approval (see approve_refund).
        db.add(Refund(order_id=order.id, payment_id=payment.id, dispute_id=d.id, amount=payment.amount,
                      reason=f"Dispute resolution: {clean_text(notes)}"[:300], requested_by_id=admin.id,
                      status=RefundStatus.PENDING_APPROVAL))
    elif outcome == "cancel":
        d.status = DisputeStatus.CANCELLED
        escrow.transition(db, order, esc, S(d.previous_order_status), actor_id=admin.id, actor_role="admin",
                          note="Dispute closed without action")
        if esc.status == S.AWAITING_BUYER_CONFIRMATION:
            esc.release_eligible_at = now + timedelta(days=settings.auto_release_days)
    else:
        raise AppError("Unknown outcome")
    for uid in (order.buyer_id, _seller_user(db, order).user_id):
        notify(db, uid, "dispute", "Dispute update", f"The dispute on order {order.order_number} has been resolved.",
               link=f"/orders/{order.id}" if uid == order.buyer_id else f"/seller/orders/{order.id}")
    db.commit()
    return d


def approve_refund(db: Session, admin: User, refund_id) -> Refund:
    refund = db.query(Refund).filter_by(id=refund_id).with_for_update().one_or_none()
    if not refund:
        raise NotFound("Refund not found")
    if refund.status != RefundStatus.PENDING_APPROVAL:
        raise InvalidState(f"Refund is {refund.status.value}", code="refund_not_pending")
    if refund.requested_by_id == admin.id and admin.role.value != "super_admin":
        raise Forbidden("A different administrator must approve this refund (four-eyes control)", code="four_eyes")
    order, esc = escrow.lock(db, refund.order_id)
    if esc.status != S.REFUND_PENDING:
        raise InvalidState("Order is not awaiting a refund")
    refund.status, refund.approved_by_id, refund.approved_at = RefundStatus.APPROVED, admin.id, utcnow()
    execute_refund(db, refund, order, esc, actor_id=admin.id, actor_role="admin")
    db.commit()
    return refund


def reject_refund(db: Session, admin: User, refund_id, reason: str) -> Refund:
    refund = db.query(Refund).filter_by(id=refund_id).with_for_update().one_or_none()
    if not refund or refund.status != RefundStatus.PENDING_APPROVAL:
        raise InvalidState("Refund is not pending approval")
    refund.status, refund.failure_reason, refund.approved_by_id = RefundStatus.REJECTED, clean_text(reason), admin.id
    order, esc = escrow.lock(db, refund.order_id)
    # Return the order to dispute so it can be re-decided.
    if esc.status == S.REFUND_PENDING:
        esc.status = order.status = S.DISPUTED
        from app.models import EscrowEvent

        db.add(EscrowEvent(escrow_id=esc.id, from_status=S.REFUND_PENDING.value, to_status=S.DISPUTED.value,
                           actor_id=admin.id, actor_role="admin", note=f"Refund rejected: {reason}", created_at=utcnow()))
        if refund.dispute_id:
            d = db.get(Dispute, refund.dispute_id)
            d.status = DisputeStatus.UNDER_REVIEW
    db.commit()
    return refund


# ---------------- background jobs ----------------
def auto_release_due(db: Session) -> int:
    now = utcnow()
    ids = db.scalars(select(EscrowTransaction.order_id).where(
        EscrowTransaction.status == S.AWAITING_BUYER_CONFIRMATION, EscrowTransaction.release_eligible_at <= now)).all()
    n = 0
    for oid in ids:
        order, esc = escrow.lock(db, oid)
        if esc.status == S.AWAITING_BUYER_CONFIRMATION and esc.release_eligible_at <= now:
            escrow.release(db, order, esc, actor_role="system", note="Auto-released: buyer confirmation window elapsed")
            _notify_release(db, order)
            n += 1
        db.commit()
    return n


def expire_unpaid(db: Session) -> int:
    now = utcnow()
    ids = db.scalars(select(Order.id).where(Order.status == S.PENDING_PAYMENT, Order.expires_at <= now)).all()
    n = 0
    for oid in ids:
        # Ask the provider first: a late webhook must never lose a real payment.
        for p in db.scalars(select(Payment).where(Payment.order_id == oid, Payment.status == PaymentStatus.INITIALIZED)).all():
            payments.confirm_payment(db, p.reference)
        order, esc = escrow.lock(db, oid)
        if esc.status == S.PENDING_PAYMENT:
            if order.payment_method == PaymentMethod.BNPL:
                from app.modules.bnpl.service import cancel_financing_for_order

                cancel_financing_for_order(db, order, "Checkout expired")
            cancel_unpaid(db, order, esc)
            n += 1
        db.commit()
    return n
