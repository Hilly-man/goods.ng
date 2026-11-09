"""One-off paid promotion for a single listing.

This is deliberately separate from account-level Premium subscriptions: a seller pays once, for one
listing, with no recurring commitment. Payment goes through the same server-verified provider path as
every other charge, and only the verified success handler unlocks visibility.
"""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.errors import AppError, NotFound
from app.core.time import utcnow
from app.models import Payment, Product, ProductImage, Promotion, SellerProfile, User
from app.models.enums import PaymentPurpose, ProductStatus, PromotionStatus, VerificationLevel
from app.modules.ledger import service as ledger
from app.modules.notifications.service import notify
from app.modules.payments import service as payments
from app.modules.promotions.packages import get_package


def create(db: Session, seller: SellerProfile, user: User, product_id, package_code: str) -> dict:
    pkg = get_package(db, package_code)
    if not pkg:
        raise NotFound("Promotion package not found")
    p = db.query(Product).filter_by(id=product_id, seller_id=seller.id).filter(Product.deleted_at.is_(None)).one_or_none()
    if not p:
        raise NotFound("Listing not found")
    if p.status != ProductStatus.ACTIVE:
        raise AppError("Only live listings can be promoted", code="listing_not_live", status_code=400)
    if pkg["tier"] == "premium":
        # Boost Premium buys sponsored slots, so it must meet the same quality bar as those slots.
        from app.modules.ads.service import MIN_DESCRIPTION, MIN_PHOTOS

        photos = db.scalar(select(func.count()).select_from(ProductImage).where(ProductImage.product_id == p.id)) or 0
        if seller.verification_level not in (VerificationLevel.IDENTITY, VerificationLevel.BUSINESS):
            raise AppError("Boost Premium requires an ID- or business-verified seller",
                           code="promotion_verification_required", status_code=400)
        if photos < MIN_PHOTOS or len(p.description or "") < MIN_DESCRIPTION:
            raise AppError(f"Boost Premium needs at least {MIN_PHOTOS} photos and a {MIN_DESCRIPTION}-character description",
                           code="promotion_quality_required", status_code=400)
    pending = db.scalars(select(Promotion).where(
        Promotion.product_id == p.id, Promotion.status == PromotionStatus.PENDING_PAYMENT)).first()
    if pending:
        raise AppError("A promotion payment is already pending for this listing",
                       code="promotion_payment_pending", status_code=409)

    now = utcnow()
    promo = Promotion(product_id=p.id, seller_id=seller.id, kind=pkg["tier"], package_code=pkg["code"],
                      starts_at=now, ends_at=now + timedelta(days=pkg["days"]),
                      status=PromotionStatus.PENDING_PAYMENT, source="paid",
                      notes=f"{pkg['name']} · {pkg['days']} days")
    db.add(promo)
    db.flush()
    # The price always comes from the server-side package, never from the client.
    pay = payments.create_payment(db, user=user, purpose=PaymentPurpose.PROMOTION, amount=pkg["price"],
                                  callback_path="/seller/promotions/complete",
                                  metadata={"package": pkg["code"], "product_id": str(p.id)})
    promo.payment_id = pay.id
    db.commit()
    return {"promotion_id": str(promo.id), "payment_reference": pay.reference,
            "authorization_url": pay.authorization_url, "amount": f"{pkg['price']:.2f}",
            "days": pkg["days"], "package": pkg["code"]}


@payments.on_success(PaymentPurpose.PROMOTION)
def activate(db: Session, payment: Payment) -> None:
    promo = db.query(Promotion).filter_by(payment_id=payment.id).with_for_update().one_or_none()
    if not promo or promo.status != PromotionStatus.PENDING_PAYMENT:
        return
    pkg = get_package(db, promo.package_code or "")
    tier = pkg["tier"] if pkg else promo.kind
    days = pkg["days"] if pkg else max(1, (promo.ends_at - promo.starts_at).days)
    name = pkg["name"] if pkg else "Listing promotion"

    p = db.query(Product).filter_by(id=promo.product_id).with_for_update().one_or_none()
    if not p or p.deleted_at:
        promo.status = PromotionStatus.CANCELLED
        return

    now = utcnow()
    # Stack on top of any time already paid for, rather than cutting it short.
    start = p.featured_until if p.featured_until and p.featured_until > now else now
    ends = start + timedelta(days=days)

    promo.status = PromotionStatus.ACTIVE
    promo.starts_at = now
    promo.ends_at = ends
    p.is_featured = True
    p.featured_until = ends
    p.bumped_at = now
    if tier == "premium" or p.promoted_tier == "premium":
        p.promoted_tier = "premium"
    else:
        p.promoted_tier = "top"

    ledger.post(db, key=f"promotion:{promo.id}:paid", kind="promotion_paid",
                description=f"Listing promotion {promo.package_code or tier} for {p.id}",
                reference=payment.reference,
                legs=[ledger.debit(ledger.SUBSCRIPTION_RECEIPTS, payment.amount),
                      ledger.credit(ledger.PROMOTION_REVENUE, payment.amount)])
    seller = db.get(SellerProfile, promo.seller_id)
    if seller:
        notify(db, seller.user_id, "promotion", f"{name} is live",
               f"“{p.title}” is promoted until {ends:%d %b %Y}.", link="/seller/products")
    cache.invalidate("feed:")
    cache.invalidate("search:")


@payments.on_failure(PaymentPurpose.PROMOTION)
def fail(db: Session, payment: Payment) -> None:
    promo = db.query(Promotion).filter_by(payment_id=payment.id).one_or_none()
    if promo and promo.status == PromotionStatus.PENDING_PAYMENT:
        promo.status = PromotionStatus.CANCELLED


def bump_active_premium(db: Session) -> int:
    """Boost Premium listings get a fresh top-of-category position roughly once a day."""
    now = utcnow()
    rows = db.scalars(select(Promotion).where(
        Promotion.status == PromotionStatus.ACTIVE, Promotion.kind == "premium",
        Promotion.ends_at > now)).all()
    bumped = 0
    for promo in rows:
        p = db.get(Product, promo.product_id)
        if not p or p.deleted_at or p.status != ProductStatus.ACTIVE:
            continue
        if p.bumped_at is None or p.bumped_at < now - timedelta(hours=20):
            p.bumped_at = now
            bumped += 1
    if bumped:
        db.commit()
        cache.invalidate("feed:")
        cache.invalidate("search:")
    return bumped
