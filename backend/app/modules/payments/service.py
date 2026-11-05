"""Payment orchestration.

Trust model: a payment is only treated as successful after a SERVER-TO-SERVER verification call to
the provider confirms status=success with the exact expected amount and currency. Webhooks only
*trigger* verification (after their signature is validated); redirects/frontend claims never count.
"""

import logging
import secrets
from collections.abc import Callable
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import AppError, Forbidden, NotFound
from app.core.time import utcnow
from app.integrations.payments import get_payment_provider
from app.models import Payment, User, WebhookEvent
from app.models.enums import PaymentPurpose, PaymentStatus

log = logging.getLogger("goodsng.payments")

# purpose -> handler(db, payment). Registered by the owning modules (orders, subscriptions, bnpl).
SUCCESS_HANDLERS: dict[PaymentPurpose, Callable[[Session, Payment], None]] = {}
FAILURE_HANDLERS: dict[PaymentPurpose, Callable[[Session, Payment], None]] = {}


def on_success(purpose: PaymentPurpose):
    def deco(fn):
        SUCCESS_HANDLERS[purpose] = fn
        return fn

    return deco


def on_failure(purpose: PaymentPurpose):
    def deco(fn):
        FAILURE_HANDLERS[purpose] = fn
        return fn

    return deco


def new_reference(prefix: str = "GNG") -> str:
    return f"{prefix}-{utcnow():%y%m%d}-{secrets.token_hex(6).upper()}"


def create_payment(db: Session, *, user: User, purpose: PaymentPurpose, amount: Decimal, callback_path: str,
                   order_id=None, subscription_id=None, installment_id=None, bnpl_application_id=None,
                   metadata: dict | None = None) -> Payment:
    """Create a Payment row and initialise it with the provider. Caller commits."""
    if amount <= 0:
        raise AppError("Invalid payment amount")
    provider = get_payment_provider()
    ref = new_reference()
    payment = Payment(reference=ref, provider=provider.name, purpose=purpose, user_id=user.id, amount=amount,
                      order_id=order_id, subscription_id=subscription_id, installment_id=installment_id,
                      bnpl_application_id=bnpl_application_id, currency="NGN")
    db.add(payment)
    db.flush()
    init = provider.initialize(
        reference=ref, amount=amount, currency="NGN", email=user.email,
        callback_url=f"{settings.frontend_url}{callback_path}?reference={ref}",
        metadata={"purpose": purpose.value, **(metadata or {})},
    )
    payment.authorization_url = init.authorization_url
    payment.provider_reference = init.provider_reference
    payment.provider_data = {"init": init.raw}
    return payment


def confirm_payment(db: Session, reference: str) -> Payment:
    """Idempotently verify a payment with its provider and apply business effects exactly once."""
    payment = db.query(Payment).filter_by(reference=reference).with_for_update().one_or_none()
    if not payment:
        raise NotFound("Payment not found")
    if payment.status != PaymentStatus.INITIALIZED:
        db.commit()
        return payment  # already final: no double application
    provider = get_payment_provider(payment.provider)
    result = provider.verify(reference)
    if result.status == "pending":
        db.commit()
        return payment
    payment.provider_data = {**payment.provider_data, "verify": result.raw}
    payment.channel = result.channel
    if result.status != "success":
        payment.status = PaymentStatus.FAILED if result.status == "failed" else PaymentStatus.ABANDONED
        payment.failure_reason = f"provider_status:{result.status}"
        handler = FAILURE_HANDLERS.get(payment.purpose)
        if handler:
            handler(db, payment)
        db.commit()
        return payment
    if result.amount != payment.amount or result.currency != payment.currency:
        # Tampered or partial payment: never fulfil; flag for reconciliation.
        payment.status = PaymentStatus.FAILED
        payment.failure_reason = f"amount_mismatch: expected {payment.amount} {payment.currency}, got {result.amount} {result.currency}"
        log.error("payment_amount_mismatch", extra={"reference": reference, "expected": str(payment.amount),
                                                    "received": str(result.amount)})
        handler = FAILURE_HANDLERS.get(payment.purpose)
        if handler:
            handler(db, payment)
        db.commit()
        return payment
    payment.status = PaymentStatus.SUCCESS
    payment.verified_at = utcnow()
    if result.provider_reference:
        payment.provider_reference = result.provider_reference
    handler = SUCCESS_HANDLERS.get(payment.purpose)
    if handler:
        handler(db, payment)
    db.commit()
    return payment


def handle_webhook(db: Session, provider_name: str, body: bytes, headers: dict[str, str]) -> dict:
    import json

    provider = get_payment_provider(provider_name)
    valid = provider.verify_webhook_signature(body, headers)
    try:
        payload = json.loads(body or b"{}")
    except ValueError:
        payload = {}
    if not valid:
        log.warning("webhook_invalid_signature", extra={"provider": provider_name})
        raise Forbidden("Invalid signature", code="invalid_signature")
    event = provider.parse_webhook(payload)
    record = WebhookEvent(provider=provider_name, event_key=event.event_key, event_type=event.event_type,
                          signature_valid=True, payload=payload, received_at=utcnow())
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"status": "duplicate"}
    try:
        if event.reference and event.event_type.startswith("charge"):
            confirm_payment(db, event.reference)
        record = db.get(WebhookEvent, record.id)
        record.processed_at = utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        record = db.get(WebhookEvent, record.id)
        record.processing_error = str(e)[:1000]
        db.commit()
        log.exception("webhook_processing_failed")
    return {"status": "ok"}


def refund_payment(db: Session, payment: Payment, amount: Decimal, reason: str):
    if amount <= 0 or payment.amount_refunded + amount > payment.amount:
        raise AppError("Refund exceeds the amount paid", code="refund_exceeds_payment")
    if payment.status not in (PaymentStatus.SUCCESS, PaymentStatus.PARTIALLY_REFUNDED):
        raise AppError("Only successful payments can be refunded")
    result = get_payment_provider(payment.provider).refund(reference=payment.reference, amount=amount, reason=reason)
    payment.amount_refunded += amount
    payment.status = PaymentStatus.REFUNDED if payment.amount_refunded == payment.amount else PaymentStatus.PARTIALLY_REFUNDED
    return result
