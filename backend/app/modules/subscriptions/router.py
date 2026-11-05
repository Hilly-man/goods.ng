import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.deps import DB, CurrentSeller, CurrentUser, client_ip, require_permission
from app.core.errors import AppError, Forbidden, NotFound
from app.core.time import utcnow
from app.models import Payment, Product, Promotion, SellerProfile, Subscription, SubscriptionPlan, User
from app.models.enums import (
    AdminPermission,
    PaymentPurpose,
    ProductStatus,
    PromotionStatus,
    SubscriptionStatus,
)
from app.modules.audit import audit
from app.modules.ledger import service as ledger
from app.modules.notifications.service import notify
from app.modules.payments import service as payments
from app.modules.subscriptions.premium import active_subscription

router = APIRouter(tags=["subscriptions"])


def plan_out(p: SubscriptionPlan) -> dict:
    return {"id": str(p.id), "code": p.code, "name": p.name, "price": f"{p.price:.2f}", "interval_days": p.interval_days,
            "featured_listing_quota": p.featured_listing_quota, "features": p.features}


@router.get("/subscriptions/plans")
def plans(db: DB):
    rows = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.is_active.is_(True))
                      .order_by(SubscriptionPlan.sort_order)).all()
    return [plan_out(p) for p in rows]


class SubscribeIn(BaseModel):
    plan_code: str


@router.post("/subscriptions", status_code=201)
def subscribe(data: SubscribeIn, seller: CurrentSeller, user: CurrentUser, db: DB):
    plan = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.code == data.plan_code,
                                                     SubscriptionPlan.is_active.is_(True))).first()
    if not plan:
        raise NotFound("Plan not found")
    # The price always comes from the server-side plan, never from the client.
    sub = Subscription(seller_id=seller.id, plan_id=plan.id, amount=plan.price, status=SubscriptionStatus.PENDING_PAYMENT)
    db.add(sub)
    db.flush()
    pay = payments.create_payment(db, user=user, purpose=PaymentPurpose.SUBSCRIPTION, amount=plan.price,
                                  subscription_id=sub.id, callback_path="/seller/subscription/complete",
                                  metadata={"plan": plan.code})
    sub.payment_id = pay.id
    db.commit()
    return {"subscription_id": str(sub.id), "payment_reference": pay.reference,
            "authorization_url": pay.authorization_url, "amount": f"{plan.price:.2f}"}


@payments.on_success(PaymentPurpose.SUBSCRIPTION)
def _activate(db: Session, payment: Payment) -> None:
    sub = db.query(Subscription).filter_by(id=payment.subscription_id).with_for_update().one()
    if sub.status != SubscriptionStatus.PENDING_PAYMENT:
        return
    plan = db.get(SubscriptionPlan, sub.plan_id)
    now = utcnow()
    current = active_subscription(db, sub.seller_id)
    start = current.current_period_end if current else now  # renewals stack after the current period
    sub.status = SubscriptionStatus.ACTIVE
    sub.current_period_start = start
    sub.current_period_end = start + timedelta(days=plan.interval_days)
    if start > now:
        # Starts later: keep it ACTIVE but premium checks use the period window, so no overlap issues.
        pass
    ledger.post(db, key=f"subscription:{sub.id}:paid", kind="subscription_paid",
                description=f"Premium subscription {plan.code}", reference=payment.reference,
                legs=[ledger.debit(ledger.SUBSCRIPTION_RECEIPTS, payment.amount),
                      ledger.credit(ledger.SUBSCRIPTION_REVENUE, payment.amount)])
    seller = db.get(SellerProfile, sub.seller_id)
    notify(db, seller.user_id, "subscription", "Premium Seller activated",
           f"Your {plan.name} plan is active until {sub.current_period_end:%d %b %Y}.", link="/seller/subscription")
    cache.invalidate("feed:")


@payments.on_failure(PaymentPurpose.SUBSCRIPTION)
def _failed(db: Session, payment: Payment) -> None:
    sub = db.get(Subscription, payment.subscription_id)
    if sub and sub.status == SubscriptionStatus.PENDING_PAYMENT:
        sub.status = SubscriptionStatus.CANCELLED


@router.get("/subscriptions/me")
def my_subscription(seller: CurrentSeller, db: DB):
    sub = active_subscription(db, seller.id)
    history = db.scalars(select(Subscription).where(Subscription.seller_id == seller.id)
                         .order_by(Subscription.created_at.desc()).limit(20)).all()
    used = 0
    if sub:
        used = db.scalar(select(func.count()).select_from(Promotion).where(
            Promotion.seller_id == seller.id, Promotion.source == "subscription_quota",
            Promotion.created_at >= sub.current_period_start)) or 0
    return {
        "active": {"id": str(sub.id), "plan": plan_out(sub.plan), "current_period_start": sub.current_period_start,
                   "current_period_end": sub.current_period_end, "featured_used": used,
                   "featured_remaining": max(sub.plan.featured_listing_quota - used, 0)} if sub else None,
        "history": [{"id": str(h.id), "plan": h.plan.name, "status": h.status, "amount": f"{h.amount:.2f}",
                     "current_period_start": h.current_period_start, "current_period_end": h.current_period_end,
                     "created_at": h.created_at} for h in history],
    }


class FeatureIn(BaseModel):
    product_id: uuid.UUID
    days: int = Field(7, ge=1, le=30)


@router.post("/subscriptions/feature-listing")
def feature_listing(data: FeatureIn, seller: CurrentSeller, db: DB):
    sub = active_subscription(db, seller.id)
    if not sub:
        raise Forbidden("Featured listings require an active Premium Seller subscription", code="premium_required")
    p = db.get(Product, data.product_id)
    if not p or p.seller_id != seller.id or p.deleted_at or p.status != ProductStatus.ACTIVE:
        raise NotFound("Active listing not found")
    # Lock the subscription row so concurrent requests cannot exceed the quota.
    db.query(Subscription).filter_by(id=sub.id).with_for_update().one()
    used = db.scalar(select(func.count()).select_from(Promotion).where(
        Promotion.seller_id == seller.id, Promotion.source == "subscription_quota",
        Promotion.created_at >= sub.current_period_start)) or 0
    if used >= sub.plan.featured_listing_quota:
        raise AppError("You have used all featured listings in your plan for this period", code="quota_exhausted")
    now = utcnow()
    ends = min(now + timedelta(days=data.days), sub.current_period_end)
    db.add(Promotion(product_id=p.id, seller_id=seller.id, starts_at=now, ends_at=ends, status=PromotionStatus.ACTIVE,
                     source="subscription_quota"))
    p.is_featured, p.featured_until = True, ends
    db.commit()
    cache.invalidate("feed:")
    return {"product_id": str(p.id), "featured_until": ends}


# ---------------- admin ----------------
class GrantIn(BaseModel):
    seller_id: uuid.UUID
    plan_code: str
    days: int = Field(30, ge=1, le=366)
    reason: str = Field(min_length=5, max_length=300)


@router.post("/admin/subscriptions/grant")
def grant(data: GrantIn, request: Request, db: DB,
          admin: User = Depends(require_permission(AdminPermission.SUBSCRIPTIONS_MANAGE))):
    seller = db.get(SellerProfile, data.seller_id)
    plan = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.code == data.plan_code)).first()
    if not seller or not plan:
        raise NotFound("Seller or plan not found")
    now = utcnow()
    sub = Subscription(seller_id=seller.id, plan_id=plan.id, amount=0, status=SubscriptionStatus.ACTIVE,
                       current_period_start=now, current_period_end=now + timedelta(days=data.days),
                       granted_by_admin_id=admin.id)
    db.add(sub)
    db.flush()
    audit(db, admin, "subscription.grant", "seller", seller.id, data.model_dump(mode="json"), client_ip(request))
    notify(db, seller.user_id, "subscription", "Premium Seller activated",
           f"Goods.ng has activated {plan.name} on your store for {data.days} days.", link="/seller/subscription")
    db.commit()
    return {"subscription_id": str(sub.id), "current_period_end": sub.current_period_end}


@router.post("/admin/subscriptions/{subscription_id}/cancel")
def cancel(subscription_id: uuid.UUID, request: Request, db: DB,
           admin: User = Depends(require_permission(AdminPermission.SUBSCRIPTIONS_MANAGE))):
    sub = db.get(Subscription, subscription_id)
    if not sub:
        raise NotFound("Subscription not found")
    sub.status = SubscriptionStatus.CANCELLED
    seller = db.get(SellerProfile, sub.seller_id)
    seller.whatsapp_enabled = seller.phone_enabled = False
    audit(db, admin, "subscription.cancel", "subscription", sub.id, {}, client_ip(request))
    db.commit()
    cache.invalidate("feed:")
    return {"status": sub.status}
