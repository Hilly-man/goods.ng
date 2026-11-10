"""Administration API. Every endpoint requires a specific permission; sensitive actions are audit-logged."""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.core.cache import cache
from app.core.config import settings
from app.core.deps import DB, CurrentUser, client_ip, require_admin_2fa, require_permission
from app.core.errors import AppError, Forbidden, NotFound
from app.core.security import clean_text, decrypt_field, mask
from app.core.time import utcnow
from app.models import (
    AdminAuditLog,
    BnplApplication,
    Category,
    CreditAssessment,
    Dispute,
    EscrowTransaction,
    FinancingAgreement,
    Installment,
    LedgerAccount,
    LedgerEntry,
    LedgerTransaction,
    MessageReport,
    Order,
    Payment,
    Payout,
    PlatformSetting,
    Product,
    Promotion,
    Refund,
    Report,
    Review,
    ReviewReport,
    SellerProfile,
    SellerVerification,
    SiteVisit,
    Subscription,
    SubscriptionPlan,
    User,
    WalletHold,
    WebhookEvent,
)
from app.models.enums import (
    AccountType,
    BnplStatus,
    DisputeStatus,
    EscrowStatus,
    InstallmentStatus,
    PaymentMethod,
    PaymentStatus,
    ProductStatus,
    RefundStatus,
    ReportStatus,
    ReviewStatus,
    VerificationLevel,
    VerificationStatus,
)
from app.models.enums import (
    AdminPermission as P,
)
from app.modules.audit import audit
from app.modules.auth.service import revoke_all_sessions
from app.modules.common import PageParams, paginate
from app.modules.ledger import service as ledger
from app.modules.notifications.service import notify
from app.modules.orders import service as orders
from app.modules.orders.router import order_out
from app.modules.reviews.router import recompute_rating
from app.modules.subscriptions.premium import premium_exists_for
from app.modules.wallet import service as wallet

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_2fa)])


def perm(p: P):
    return Depends(require_permission(p.value))


@router.get("/me")
def admin_me(user: CurrentUser):
    if not user.is_admin:
        raise Forbidden("Not an administrator")
    role = user.admin_role
    return {"role": user.role, "is_super_admin": user.is_super_admin,
            "role_name": role.name if role else ("Super Admin" if user.is_super_admin else "Admin"),
            "permissions": sorted(user.permissions())}


@router.get("/nav-counts")
def nav_counts(db: DB, user: CurrentUser):
    """Work-queue badges for the admin sidebar — only the queues this staff member is allowed to act on."""
    if not user.is_admin:
        raise Forbidden("Not an administrator")
    perms = user.permissions()

    def c(stmt):
        return db.scalar(stmt) or 0

    queues = {
        "disputes": (P.DISPUTES_RESOLVE, lambda: c(select(func.count()).select_from(Dispute).where(
            Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW])))),
        "refunds": (P.REFUNDS_APPROVE, lambda: c(select(func.count()).select_from(Refund).where(
            Refund.status == RefundStatus.PENDING_APPROVAL))),
        "verifications": (P.SELLERS_VERIFY, lambda: c(select(func.count()).select_from(SellerVerification).where(
            SellerVerification.status == VerificationStatus.PENDING))),
        "products": (P.LISTINGS_MODERATE, lambda: c(select(func.count()).select_from(Product).where(
            Product.status == ProductStatus.PENDING_REVIEW, Product.deleted_at.is_(None)))),
        "reports": (P.REPORTS_MANAGE, lambda: c(select(func.count()).select_from(Report).where(
            Report.status == ReportStatus.OPEN))),
        "reviews": (P.REVIEWS_MODERATE, lambda: c(select(func.count(func.distinct(ReviewReport.review_id))).where(
            ReviewReport.status == ReportStatus.OPEN))),
    }
    return {k: fn() for k, (p, fn) in queues.items() if p.value in perms}


@router.get("/overview/trends")
def overview_trends(db: DB, days: int = Query(30, ge=7, le=90), admin: User = perm(P.ANALYTICS_VIEW)):
    """Daily series (Lagos calendar days) + breakdowns for the overview charts."""
    return cache.get_or_compute(f"admin:trends:{days}", 60, lambda: _trends(db, days))


def _trends(db, days: int) -> dict:
    from datetime import date as _date
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    lagos = ZoneInfo("Africa/Lagos")
    today = _dt.now(lagos).date()
    start_day = today - timedelta(days=days - 1)
    start = _dt.combine(start_day, _dt.min.time(), tzinfo=lagos)

    def day(col):
        return func.date(func.timezone("Africa/Lagos", col))

    def by_day(col, value, *where):
        d = day(col)
        return {r[0]: r[1] for r in db.execute(select(d, value).where(col >= start, *where).group_by(d)).all()}

    paid = Order.paid_at.isnot(None)
    sales = by_day(Order.paid_at, func.coalesce(func.sum(Order.total), 0), paid)
    orders = by_day(Order.paid_at, func.count(), paid)
    users = by_day(User.created_at, func.count(), User.deleted_at.is_(None), User.account_type == "customer")
    listings = by_day(Product.created_at, func.count(), Product.deleted_at.is_(None))
    series = []
    for i in range(days):
        d: _date = start_day + timedelta(days=i)
        series.append({"date": d.isoformat(), "sales": f"{sales.get(d, 0):.2f}", "orders": orders.get(d, 0),
                       "new_users": users.get(d, 0), "new_listings": listings.get(d, 0)})

    in_range = (Order.paid_at >= start,)
    by_status = db.execute(select(Order.status, func.count()).where(paid, *in_range).group_by(Order.status)
                           .order_by(func.count().desc())).all()
    mix = dict(db.execute(select(Order.payment_method, func.count()).where(paid, *in_range)
                          .group_by(Order.payment_method)).all())
    top_cats = db.execute(select(Category.name, func.count()).join(Product, Product.category_id == Category.id).where(
        Product.status == ProductStatus.ACTIVE, Product.deleted_at.is_(None)).group_by(Category.name)
        .order_by(func.count().desc()).limit(6)).all()
    return {
        "days": days, "series": series,
        "orders_by_status": [{"status": s.value if hasattr(s, "value") else s, "count": n} for s, n in by_status],
        "payment_mix": {"full": mix.get(PaymentMethod.FULL, 0), "bnpl": mix.get(PaymentMethod.BNPL, 0)},
        "top_categories": [{"name": n, "count": c} for n, c in top_cats],
    }


# ---------------- live traffic ----------------
@router.get("/live-stats")
def live_stats(db: DB, admin: User = perm(P.ANALYTICS_VIEW)):
    return cache.get_or_compute("admin:live-stats", 10, lambda: _live_stats(db))


def _live_stats(db: DB) -> dict:
    now = utcnow()

    def unique(since, *, signed_in: bool | None = None) -> int:
        stmt = select(func.count(func.distinct(SiteVisit.visitor_id))).where(SiteVisit.created_at >= since)
        if signed_in is True:
            stmt = stmt.where(SiteVisit.user_id.isnot(None))
        elif signed_in is False:
            stmt = stmt.where(SiteVisit.user_id.is_(None))
        return db.scalar(stmt) or 0

    visitors = {
        "daily": unique(now - timedelta(days=1)),
        "weekly": unique(now - timedelta(days=7)),
        "monthly": unique(now - timedelta(days=30)),
        "quarterly": unique(now - timedelta(days=90)),
        "yearly": unique(now - timedelta(days=365)),
    }
    active = {
        "live_5m": unique(now - timedelta(minutes=5)),
        "active_15m": unique(now - timedelta(minutes=15)),
        "active_60m": unique(now - timedelta(minutes=60)),
        "active_24h": unique(now - timedelta(hours=24)),
    }
    hour = func.date_trunc("hour", func.timezone("Africa/Lagos", SiteVisit.created_at))
    rows = db.execute(
        select(hour.label("hour"), func.count(func.distinct(SiteVisit.visitor_id)))
        .where(SiteVisit.created_at >= now - timedelta(hours=24))
        .group_by(hour).order_by(hour)
    ).all()
    return {
        "visitors": visitors,
        "active": {**active, "signed_in": unique(now - timedelta(minutes=5), signed_in=True),
                   "guests": unique(now - timedelta(minutes=5), signed_in=False)},
        "series_24h": [{"hour": h.isoformat(), "visitors": c} for h, c in rows],
        "updated_at": now.isoformat(),
    }


# ---------------- overview ----------------
@router.get("/overview")
def overview(db: DB, admin: User = perm(P.ANALYTICS_VIEW)):
    cached = cache.get_json("admin:overview")
    if cached:
        return cached
    S = EscrowStatus
    since30 = utcnow() - timedelta(days=30)

    def c(stmt):
        return db.scalar(stmt) or 0

    total_orders = c(select(func.count()).select_from(Order).where(Order.paid_at.isnot(None)))
    disputes = c(select(func.count(func.distinct(Dispute.order_id))))
    refunded = c(select(func.count()).select_from(Order).where(Order.status == S.REFUNDED))
    gmv = db.scalar(select(func.coalesce(func.sum(Order.total), 0)).where(Order.status == S.COMPLETED))
    revenue = ledger.balance(db, ledger.COMMISSION[0]) + ledger.balance(db, ledger.PROTECTION_FEES[0]) + \
        ledger.balance(db, ledger.SUBSCRIPTION_REVENUE[0])
    active_buyers = c(select(func.count(func.distinct(Order.buyer_id))).where(Order.created_at >= since30))
    active_sellers = c(select(func.count(func.distinct(Product.seller_id))).where(
        Product.status == ProductStatus.ACTIVE, Product.deleted_at.is_(None)))
    bnpl_outstanding = db.scalar(select(func.coalesce(func.sum(FinancingAgreement.outstanding_balance), 0)).where(
        FinancingAgreement.status == BnplStatus.ACTIVE))
    data = {
        "total_users": c(select(func.count()).select_from(User).where(User.deleted_at.is_(None))),
        "active_buyers_30d": active_buyers,
        "active_sellers": active_sellers,
        "total_sellers": c(select(func.count()).select_from(SellerProfile)),
        "verified_sellers": c(select(func.count()).select_from(SellerProfile).where(SellerProfile.verification_level.in_(
            [VerificationLevel.IDENTITY, VerificationLevel.BUSINESS]))),
        "premium_sellers": c(select(func.count()).select_from(SellerProfile).where(premium_exists_for(SellerProfile.id))),
        "active_listings": c(select(func.count()).select_from(Product).where(Product.status == ProductStatus.ACTIVE,
                                                                             Product.deleted_at.is_(None))),
        "pending_listings": c(select(func.count()).select_from(Product).where(Product.status == ProductStatus.PENDING_REVIEW)),
        "total_orders": total_orders,
        "completed_protected": c(select(func.count()).select_from(Order).where(Order.status == S.COMPLETED)),
        "in_escrow_value": f"{db.scalar(select(func.coalesce(func.sum(EscrowTransaction.amount), 0)).where(EscrowTransaction.status.in_([S.AWAITING_SELLER, S.PROCESSING, S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION, S.DISPUTED]))):.2f}",
        "total_transaction_value": f"{gmv:.2f}",
        "platform_revenue": f"{revenue:.2f}",
        "dispute_rate": round(disputes / total_orders * 100, 2) if total_orders else 0,
        "refund_rate": round(refunded / total_orders * 100, 2) if total_orders else 0,
        "open_disputes": c(select(func.count()).select_from(Dispute).where(Dispute.status.in_(
            [DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]))),
        "pending_refunds": c(select(func.count()).select_from(Refund).where(Refund.status == RefundStatus.PENDING_APPROVAL)),
        "pending_verifications": c(select(func.count()).select_from(SellerVerification).where(
            SellerVerification.status == VerificationStatus.PENDING)),
        "open_reports": c(select(func.count()).select_from(Report).where(Report.status == ReportStatus.OPEN)),
        "bnpl": {
            "applications": c(select(func.count()).select_from(BnplApplication)),
            "approved": c(select(func.count()).select_from(BnplApplication).where(BnplApplication.status.in_(
                [BnplStatus.APPROVED, BnplStatus.ACCEPTED, BnplStatus.ACTIVE, BnplStatus.COMPLETED]))),
            "active_agreements": c(select(func.count()).select_from(FinancingAgreement).where(
                FinancingAgreement.status == BnplStatus.ACTIVE)),
            "outstanding": f"{bnpl_outstanding:.2f}",
            "overdue_installments": c(select(func.count()).select_from(Installment).where(
                Installment.status == InstallmentStatus.OVERDUE)),
        },
    }
    cache.set_json("admin:overview", data, ttl=30)
    return data


# ---------------- users ----------------
@router.get("/users")
def users(db: DB, q: str | None = None, role: str | None = None, params: PageParams = Depends(),
          admin: User = perm(P.USERS_MANAGE)):
    stmt = select(User).where(User.account_type == AccountType.CUSTOMER)
    if q:
        like = f"%{q[:60]}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.full_name.ilike(like), User.phone.ilike(like)))
    if role:
        stmt = stmt.where(User.role == role)
    return paginate(db, stmt.order_by(User.created_at.desc()), params, lambda u: {
        "id": str(u.id), "email": u.email, "phone": u.phone, "full_name": u.full_name, "role": u.role,
        "admin_permissions": u.admin_permissions, "is_active": u.is_active, "email_verified": u.email_verified,
        "phone_verified": u.phone_verified, "is_seller": u.seller_profile is not None, "created_at": u.created_at,
        "last_login_at": u.last_login_at})


class UserStatusIn(BaseModel):
    is_active: bool
    reason: str = Field(min_length=3, max_length=300)


@router.post("/users/{user_id}/status")
def set_user_status(user_id: uuid.UUID, data: UserStatusIn, request: Request, db: DB,
                    admin: User = perm(P.USERS_MANAGE)):
    u = db.get(User, user_id)
    if not u:
        raise NotFound("User not found")
    if u.is_staff:
        raise Forbidden("Staff accounts are managed under Admin team (super admin only)", code="staff_account")
    u.is_active = data.is_active
    if not data.is_active:
        revoke_all_sessions(db, u)
    audit(db, admin, "user.status", "user", u.id, data.model_dump(), client_ip(request))
    db.commit()
    return {"id": str(u.id), "is_active": u.is_active}


# Role changes for admins live in app/modules/staff (super admin only). Customers can't be promoted.


# ---------------- sellers & verification ----------------
@router.get("/sellers")
def sellers(db: DB, q: str | None = None, params: PageParams = Depends(), admin: User = perm(P.SELLERS_VERIFY)):
    stmt = select(SellerProfile)
    if q:
        stmt = stmt.where(SellerProfile.store_name.ilike(f"%{q[:60]}%"))
    return paginate(db, stmt.order_by(SellerProfile.created_at.desc()), params, lambda s: {
        "id": str(s.id), "store_name": s.store_name, "slug": s.slug, "verification_level": s.verification_level,
        "is_suspended": s.is_suspended, "rating_avg": f"{s.rating_avg:.2f}", "rating_count": s.rating_count,
        "completed_sales": s.completed_sales, "owner_email": s.user.email, "created_at": s.created_at})


class SuspendIn(BaseModel):
    suspended: bool
    reason: str = Field(min_length=3, max_length=300)


@router.post("/sellers/{seller_id}/suspend")
def suspend_seller(seller_id: uuid.UUID, data: SuspendIn, request: Request, db: DB,
                   admin: User = perm(P.SELLERS_VERIFY)):
    s = db.get(SellerProfile, seller_id)
    if not s:
        raise NotFound("Seller not found")
    s.is_suspended = data.suspended
    audit(db, admin, "seller.suspend" if data.suspended else "seller.unsuspend", "seller", s.id, data.model_dump(),
          client_ip(request))
    db.commit()
    cache.invalidate("feed:")
    return {"id": str(s.id), "is_suspended": s.is_suspended}


@router.get("/verifications")
def verifications(db: DB, status: VerificationStatus = VerificationStatus.PENDING, params: PageParams = Depends(),
                  admin: User = perm(P.SELLERS_VERIFY)):
    stmt = select(SellerVerification).where(SellerVerification.status == status) \
        .order_by(SellerVerification.created_at)

    def m(v: SellerVerification):
        s = db.get(SellerProfile, v.seller_id)
        return {"id": str(v.id), "seller": {"id": str(s.id), "store_name": s.store_name, "slug": s.slug,
                                            "current_level": s.verification_level},
                "level_requested": v.level_requested, "document_type": v.document_type,
                "document_number": f"••••{v.document_number_last4}", "business_name": v.business_name,
                "status": v.status, "created_at": v.created_at, "review_notes": v.review_notes}

    return paginate(db, stmt, params, m)


@router.get("/verifications/{verification_id}/document-number")
def reveal_document_number(verification_id: uuid.UUID, request: Request, db: DB,
                           admin: User = perm(P.SELLERS_VERIFY)):
    """Decrypts the KYC identifier for manual checking. Every reveal is audit-logged."""
    v = db.get(SellerVerification, verification_id)
    if not v:
        raise NotFound("Verification not found")
    audit(db, admin, "kyc.reveal", "verification", v.id, {}, client_ip(request))
    db.commit()
    return {"document_number": decrypt_field(v.document_number_enc), "masked": mask(decrypt_field(v.document_number_enc))}


class VerifyDecisionIn(BaseModel):
    approve: bool
    notes: str = Field(min_length=3, max_length=500)


@router.post("/verifications/{verification_id}/decide")
def decide_verification(verification_id: uuid.UUID, data: VerifyDecisionIn, request: Request, db: DB,
                        admin: User = perm(P.SELLERS_VERIFY)):
    v = db.query(SellerVerification).filter_by(id=verification_id).with_for_update().one_or_none()
    if not v or v.status != VerificationStatus.PENDING:
        raise NotFound("Pending verification not found")
    s = db.get(SellerProfile, v.seller_id)
    v.status = VerificationStatus.APPROVED if data.approve else VerificationStatus.REJECTED
    v.reviewed_by_id, v.reviewed_at, v.review_notes = admin.id, utcnow(), clean_text(data.notes)
    if data.approve:
        order = [VerificationLevel.UNVERIFIED, VerificationLevel.PHONE, VerificationLevel.IDENTITY, VerificationLevel.BUSINESS]
        if order.index(v.level_requested) > order.index(s.verification_level):
            s.verification_level = v.level_requested
    audit(db, admin, "verification.decide", "verification", v.id, data.model_dump(), client_ip(request))
    notify(db, s.user_id, "verification", "Verification update",
           f"Your {v.level_requested.value.replace('_', ' ')} request was {'approved' if data.approve else 'not approved'}."
           + ("" if data.approve else f" Reason: {data.notes}"), link="/seller/verification")
    db.commit()
    return {"id": str(v.id), "status": v.status, "seller_level": s.verification_level}


# ---------------- listings moderation ----------------
@router.get("/products")
def products(db: DB, status: str | None = None, q: str | None = None, params: PageParams = Depends(),
             admin: User = perm(P.LISTINGS_MODERATE)):
    stmt = select(Product).where(Product.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Product.status == status)
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q[:60]}%"))
    return paginate(db, stmt.order_by(Product.created_at.desc()), params, lambda p: {
        "id": str(p.id), "title": p.title, "slug": p.slug, "price": f"{p.price:.2f}", "status": p.status,
        "seller": {"id": str(p.seller_id), "store_name": p.seller.store_name}, "category": p.category.name,
        "thumb_url": p.images[0].thumb_url if p.images else None, "is_featured": p.is_featured,
        "rejection_reason": p.rejection_reason, "created_at": p.created_at})


class ModerateIn(BaseModel):
    action: Literal["approve", "reject", "deactivate", "feature", "unfeature"]
    reason: str | None = Field(None, max_length=300)
    feature_days: int = Field(7, ge=1, le=90)


@router.post("/products/{product_id}/moderate")
def moderate(product_id: uuid.UUID, data: ModerateIn, request: Request, db: DB,
             admin: User = perm(P.LISTINGS_MODERATE)):
    p = db.get(Product, product_id)
    if not p:
        raise NotFound("Listing not found")
    if data.action in ("reject", "deactivate") and not data.reason:
        raise AppError("A reason is required")
    if data.action == "approve":
        p.status, p.rejection_reason = ProductStatus.ACTIVE, None
        p.published_at = p.published_at or utcnow()
    elif data.action == "reject":
        p.status, p.rejection_reason = ProductStatus.REJECTED, clean_text(data.reason)
    elif data.action == "deactivate":
        p.status, p.rejection_reason = ProductStatus.INACTIVE, clean_text(data.reason)
    elif data.action == "feature":
        p.is_featured, p.featured_until = True, utcnow() + timedelta(days=data.feature_days)
        db.add(Promotion(product_id=p.id, seller_id=p.seller_id, starts_at=utcnow(), ends_at=p.featured_until,
                         source="admin", notes=clean_text(data.reason)))
    else:
        p.is_featured, p.featured_until = False, None
    audit(db, admin, f"product.{data.action}", "product", p.id, data.model_dump(), client_ip(request))
    if data.action in ("approve", "reject", "deactivate"):
        notify(db, p.seller.user_id, "listing_moderation", "Listing update",
               f"\"{p.title[:60]}\" was {data.action}d." + (f" Reason: {data.reason}" if data.reason else ""),
               link="/seller/products")
    db.commit()
    cache.invalidate("feed:")
    cache.invalidate("categories:")
    return {"id": str(p.id), "status": p.status, "is_featured": p.is_featured}


# ---------------- orders, payments, escrow, ledger ----------------
@router.get("/orders")
def admin_orders(db: DB, status: str | None = None, q: str | None = None, params: PageParams = Depends(),
                 admin: User = perm(P.ORDERS_VIEW)):
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == status)
    if q:
        stmt = stmt.where(Order.order_number.ilike(f"%{q[:30]}%"))
    return paginate(db, stmt.order_by(Order.created_at.desc()), params, lambda o: order_out(db, o, "admin"))


@router.get("/orders/{order_id}")
def admin_order(order_id: uuid.UUID, db: DB, admin: User = perm(P.ORDERS_VIEW)):
    o = db.get(Order, order_id)
    if not o:
        raise NotFound("Order not found")
    return order_out(db, o, "admin", detail=True)


@router.get("/payments")
def admin_payments(db: DB, status: str | None = None, purpose: str | None = None, params: PageParams = Depends(),
                   admin: User = perm(P.PAYMENTS_VIEW)):
    stmt = select(Payment)
    if status:
        stmt = stmt.where(Payment.status == status)
    if purpose:
        stmt = stmt.where(Payment.purpose == purpose)
    return paginate(db, stmt.order_by(Payment.created_at.desc()), params, lambda p: {
        "id": str(p.id), "reference": p.reference, "provider": p.provider, "purpose": p.purpose, "status": p.status,
        "amount": f"{p.amount:.2f}", "amount_refunded": f"{p.amount_refunded:.2f}", "channel": p.channel,
        "failure_reason": p.failure_reason, "order_id": str(p.order_id) if p.order_id else None,
        "verified_at": p.verified_at, "created_at": p.created_at})


@router.get("/escrow")
def admin_escrow(db: DB, status: str | None = None, params: PageParams = Depends(), admin: User = perm(P.PAYMENTS_VIEW)):
    stmt = select(EscrowTransaction)
    if status:
        stmt = stmt.where(EscrowTransaction.status == status)
    return paginate(db, stmt.order_by(EscrowTransaction.created_at.desc()), params, lambda e: {
        "id": str(e.id), "order_id": str(e.order_id), "order_number": e.order.order_number, "status": e.status,
        "provider": e.provider, "provider_escrow_ref": e.provider_escrow_ref, "amount": f"{e.amount:.2f}",
        "seller_amount": f"{e.seller_amount:.2f}", "platform_amount": f"{e.platform_amount:.2f}",
        "funded_at": e.funded_at, "release_eligible_at": e.release_eligible_at, "released_at": e.released_at,
        "refunded_at": e.refunded_at})


@router.get("/ledger")
def admin_ledger(db: DB, admin: User = perm(P.PAYMENTS_VIEW), limit: int = Query(50, le=200)):
    accounts = db.scalars(select(LedgerAccount).order_by(LedgerAccount.code)).all()
    txns = db.scalars(select(LedgerTransaction).order_by(LedgerTransaction.created_at.desc()).limit(limit)).all()
    tb = ledger.trial_balance(db)
    return {
        "trial_balance": {"debits": f"{tb['debits']:.2f}", "credits": f"{tb['credits']:.2f}", "balanced": tb["balanced"]},
        "accounts": [{"code": a.code, "name": a.name, "type": a.type, "balance": f"{ledger.balance(db, a.code):.2f}"}
                     for a in accounts],
        "transactions": [{"id": str(t.id), "kind": t.kind, "reference": t.reference, "description": t.description,
                          "created_at": t.created_at,
                          "entries": [{"account": e.account.code, "direction": e.direction, "amount": f"{e.amount:.2f}"}
                                      for e in db.scalars(select(LedgerEntry).where(LedgerEntry.transaction_id == t.id))]}
                         for t in txns],
    }


@router.get("/reconciliation")
def reconciliation(db: DB, admin: User = perm(P.PAYMENTS_VIEW)):
    """Cross-checks payments, escrow states and the ledger; any non-empty list needs investigation."""
    S = EscrowStatus
    funded_states = [S.AWAITING_SELLER, S.PROCESSING, S.DISPATCHED, S.DELIVERED, S.AWAITING_BUYER_CONFIRMATION,
                     S.DISPUTED, S.REFUND_PENDING, S.COMPLETED, S.REFUNDED]
    funded = db.scalars(select(EscrowTransaction).where(EscrowTransaction.status.in_(funded_states))).all()
    keys = set(db.scalars(select(LedgerTransaction.idempotency_key)).all())
    missing_funding = [e.order.order_number for e in funded if f"escrow:{e.id}:funded" not in keys]
    settled = [e for e in funded if e.status in (S.COMPLETED, S.REFUNDED)]
    missing_settlement = [e.order.order_number for e in settled if f"escrow:{e.id}:settle" not in keys]
    paid_orders_without_escrow = db.scalars(select(Order.order_number).join(Payment, Payment.order_id == Order.id).where(
        Payment.status == PaymentStatus.SUCCESS, Order.status.in_([S.PENDING_PAYMENT, S.CANCELLED]))).all()
    held = ledger.balance(db, ledger.ESCROW_HOLDING[0])
    obligations = ledger.balance(db, ledger.ESCROW_OBLIGATIONS[0])
    open_escrow = sum((e.amount for e in funded if e.status not in (S.COMPLETED, S.REFUNDED)), Decimal("0"))
    stale_webhooks = db.scalar(select(func.count()).select_from(WebhookEvent).where(WebhookEvent.processing_error.isnot(None)))
    tb = ledger.trial_balance(db)
    return {
        "ledger_balanced": tb["balanced"],
        "escrow_obligations_ledger": f"{obligations:.2f}",
        "open_escrow_value": f"{open_escrow:.2f}",
        "obligations_match_open_escrow": obligations == open_escrow,
        "escrow_partner_holding_ledger": f"{held:.2f}",
        "missing_funding_entries": missing_funding,
        "missing_settlement_entries": missing_settlement,
        "paid_orders_not_funded": list(paid_orders_without_escrow),
        "webhooks_with_errors": stale_webhooks or 0,
    }


# ---------------- disputes & refunds ----------------
@router.get("/disputes")
def disputes(db: DB, status: str | None = None, params: PageParams = Depends(), admin: User = perm(P.DISPUTES_RESOLVE)):
    stmt = select(Dispute)
    stmt = stmt.where(Dispute.status == status) if status else stmt.where(
        Dispute.status.in_([DisputeStatus.OPEN, DisputeStatus.UNDER_REVIEW]))
    return paginate(db, stmt.order_by(Dispute.created_at), params, lambda d: {
        "id": str(d.id), "order_id": str(d.order_id), "order_number": d.order.order_number, "status": d.status,
        "reason": d.reason, "opened_by": d.opened_by_role, "description": d.description,
        "amount": f"{d.order.total:.2f}", "created_at": d.created_at})


class ResolveIn(BaseModel):
    outcome: Literal["release_to_seller", "refund_buyer", "cancel"]
    notes: str = Field(min_length=10, max_length=2000)


@router.post("/disputes/{dispute_id}/review")
def mark_under_review(dispute_id: uuid.UUID, request: Request, db: DB, admin: User = perm(P.DISPUTES_RESOLVE)):
    d = db.get(Dispute, dispute_id)
    if not d or d.status != DisputeStatus.OPEN:
        raise NotFound("Open dispute not found")
    d.status = DisputeStatus.UNDER_REVIEW
    audit(db, admin, "dispute.review", "dispute", d.id, {}, client_ip(request))
    db.commit()
    return {"status": d.status}


@router.post("/disputes/{dispute_id}/resolve")
def resolve(dispute_id: uuid.UUID, data: ResolveIn, request: Request, db: DB, admin: User = perm(P.DISPUTES_RESOLVE)):
    audit(db, admin, "dispute.resolve", "dispute", dispute_id, data.model_dump(), client_ip(request))
    d = orders.resolve_dispute(db, admin, dispute_id, data.outcome, data.notes)
    return {"id": str(d.id), "status": d.status}


@router.get("/refunds")
def refunds(db: DB, status: str | None = None, params: PageParams = Depends(), admin: User = perm(P.REFUNDS_APPROVE)):
    stmt = select(Refund)
    if status:
        stmt = stmt.where(Refund.status == status)
    return paginate(db, stmt.order_by(Refund.created_at.desc()), params, lambda r: {
        "id": str(r.id), "order_id": str(r.order_id), "amount": f"{r.amount:.2f}", "status": r.status,
        "reason": r.reason, "requested_by_id": str(r.requested_by_id),
        "approved_by_id": str(r.approved_by_id) if r.approved_by_id else None,
        "dispute_id": str(r.dispute_id) if r.dispute_id else None, "created_at": r.created_at,
        "completed_at": r.completed_at})


@router.post("/refunds/{refund_id}/approve")
def approve_refund(refund_id: uuid.UUID, request: Request, db: DB, admin: User = perm(P.REFUNDS_APPROVE)):
    audit(db, admin, "refund.approve", "refund", refund_id, {}, client_ip(request))
    r = orders.approve_refund(db, admin, refund_id)
    return {"id": str(r.id), "status": r.status}


class RejectIn(BaseModel):
    reason: str = Field(min_length=5, max_length=300)


@router.post("/refunds/{refund_id}/reject")
def reject_refund(refund_id: uuid.UUID, data: RejectIn, request: Request, db: DB,
                  admin: User = perm(P.REFUNDS_APPROVE)):
    audit(db, admin, "refund.reject", "refund", refund_id, data.model_dump(), client_ip(request))
    r = orders.reject_refund(db, admin, refund_id, data.reason)
    return {"id": str(r.id), "status": r.status}


# ---------------- seller wallet & payouts ----------------
@router.get("/payouts")
def admin_payouts(db: DB, status: str | None = None, params: PageParams = Depends(),
                  admin: User = perm(P.PAYOUTS_APPROVE)):
    stmt = select(Payout)
    if status:
        stmt = stmt.where(Payout.status == status)
    return paginate(db, stmt.order_by(Payout.created_at.desc()), params, wallet.payout_out)


@router.post("/payouts/{payout_id}/approve")
def approve_payout(payout_id: uuid.UUID, request: Request, db: DB, admin: User = perm(P.PAYOUTS_APPROVE)):
    audit(db, admin, "payout.approve", "payout", payout_id, {}, client_ip(request))
    p = wallet.approve_payout(db, payout_id, admin_id=admin.id)
    return wallet.payout_out(p)


class PayoutRejectIn(BaseModel):
    reason: str = Field(min_length=5, max_length=300)


@router.post("/payouts/{payout_id}/reject")
def reject_payout(payout_id: uuid.UUID, data: PayoutRejectIn, request: Request, db: DB,
                  admin: User = perm(P.PAYOUTS_APPROVE)):
    audit(db, admin, "payout.reject", "payout", payout_id, data.model_dump(), client_ip(request))
    p = wallet.reject_payout(db, payout_id, admin_id=admin.id, reason=data.reason)
    return wallet.payout_out(p)


@router.post("/payouts/{payout_id}/retry")
def retry_payout(payout_id: uuid.UUID, request: Request, db: DB, admin: User = perm(P.PAYOUTS_APPROVE)):
    audit(db, admin, "payout.retry", "payout", payout_id, {}, client_ip(request))
    p = wallet.retry_payout(db, payout_id, admin_id=admin.id)
    return {"id": str(p.id), "status": p.status}


@router.get("/wallet/holds")
def wallet_holds(db: DB, params: PageParams = Depends(), admin: User = perm(P.DISPUTES_RESOLVE)):
    stmt = select(WalletHold).where(WalletHold.released_at.is_(None))
    return paginate(db, stmt.order_by(WalletHold.created_at.desc()), params, wallet.serialize_hold)


@router.post("/wallet/holds/{hold_id}/release")
def release_wallet_hold(hold_id: uuid.UUID, request: Request, db: DB, admin: User = perm(P.DISPUTES_RESOLVE)):
    audit(db, admin, "wallet_hold.release", "wallet_hold", hold_id, {}, client_ip(request))
    h = wallet.release_hold(db, hold_id, actor_id=admin.id)
    return wallet.serialize_hold(h)


# ---------------- BNPL ----------------
@router.get("/bnpl/applications")
def bnpl_apps(db: DB, status: str | None = None, params: PageParams = Depends(), admin: User = perm(P.BNPL_VIEW)):
    stmt = select(BnplApplication)
    if status:
        stmt = stmt.where(BnplApplication.status == status)
    return paginate(db, stmt.order_by(BnplApplication.created_at.desc()), params, lambda a: {
        "id": str(a.id), "status": a.status, "provider": a.provider, "credit_decision_ref": a.credit_decision_ref,
        "purchase_amount": f"{a.purchase_amount:.2f}", "tenor_months": a.tenor_months, "decline_reason": a.decline_reason,
        "order_id": str(a.order_id) if a.order_id else None, "created_at": a.created_at,
        "credit_limit": f"{a.credit_limit_at_application:.2f}" if a.credit_limit_at_application is not None else None,
        "assessed_income": f"{db.get(CreditAssessment, a.assessment_id).monthly_income:.2f}" if a.assessment_id else None,
        "outstanding": f"{a.agreement.outstanding_balance:.2f}" if a.agreement else None})


# ---------------- subscriptions & plans ----------------
@router.get("/subscriptions")
def subs(db: DB, status: str | None = None, params: PageParams = Depends(), admin: User = perm(P.SUBSCRIPTIONS_MANAGE)):
    stmt = select(Subscription)
    if status:
        stmt = stmt.where(Subscription.status == status)
    return paginate(db, stmt.order_by(Subscription.created_at.desc()), params, lambda s: {
        "id": str(s.id), "seller": {"id": str(s.seller_id), "store_name": s.seller.store_name}, "plan": s.plan.name,
        "status": s.status, "amount": f"{s.amount:.2f}", "current_period_start": s.current_period_start,
        "current_period_end": s.current_period_end, "granted_by_admin": s.granted_by_admin_id is not None,
        "created_at": s.created_at})


class PlanIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    price: Decimal = Field(ge=0, decimal_places=2)
    interval_days: int = Field(ge=1, le=366)
    featured_listing_quota: int = Field(0, ge=0, le=1000)
    features: list[str] = []
    is_active: bool = True


@router.put("/plans/{code}")
def upsert_plan(code: str, data: PlanIn, request: Request, db: DB, admin: User = perm(P.SUBSCRIPTIONS_MANAGE)):
    plan = db.scalars(select(SubscriptionPlan).where(SubscriptionPlan.code == code)).first()
    if not plan:
        plan = SubscriptionPlan(code=code)
        db.add(plan)
    for k, v in data.model_dump().items():
        setattr(plan, k, v)
    audit(db, admin, "plan.upsert", "plan", code, data.model_dump(mode="json"), client_ip(request))
    db.commit()
    return {"code": plan.code}


@router.get("/promotions")
def promotions(db: DB, params: PageParams = Depends(), admin: User = perm(P.PROMOTIONS_MANAGE)):
    return paginate(db, select(Promotion).order_by(Promotion.created_at.desc()), params, lambda p: {
        "id": str(p.id), "product_id": str(p.product_id), "seller_id": str(p.seller_id), "kind": p.kind,
        "source": p.source, "status": p.status, "starts_at": p.starts_at, "ends_at": p.ends_at})


# ---------------- reviews & reports ----------------
@router.get("/reviews")
def admin_reviews(db: DB, reported_only: bool = False, params: PageParams = Depends(),
                  admin: User = perm(P.REVIEWS_MODERATE)):
    stmt = select(Review)
    if reported_only:
        stmt = stmt.where(Review.id.in_(select(ReviewReport.review_id).where(ReviewReport.status == ReportStatus.OPEN)))
    return paginate(db, stmt.order_by(Review.created_at.desc()), params, lambda r: {
        "id": str(r.id), "rating": r.rating, "title": r.title, "comment": r.comment, "status": r.status,
        "is_verified_purchase": r.is_verified_purchase, "seller_id": str(r.seller_id), "reviewer": r.reviewer.email,
        "reports": db.scalar(select(func.count()).select_from(ReviewReport).where(ReviewReport.review_id == r.id)),
        "created_at": r.created_at})


class ReviewModIn(BaseModel):
    status: ReviewStatus
    note: str = Field(min_length=3, max_length=300)


@router.post("/reviews/{review_id}/moderate")
def moderate_review(review_id: uuid.UUID, data: ReviewModIn, request: Request, db: DB,
                    admin: User = perm(P.REVIEWS_MODERATE)):
    r = db.get(Review, review_id)
    if not r:
        raise NotFound("Review not found")
    r.status, r.moderation_note = data.status, clean_text(data.note)
    for rep in db.scalars(select(ReviewReport).where(ReviewReport.review_id == r.id, ReviewReport.status == ReportStatus.OPEN)):
        rep.status = ReportStatus.ACTIONED if data.status == ReviewStatus.HIDDEN else ReportStatus.DISMISSED
    recompute_rating(db, r.seller_id)
    audit(db, admin, "review.moderate", "review", r.id, data.model_dump(mode="json"), client_ip(request))
    db.commit()
    return {"id": str(r.id), "status": r.status}


@router.get("/reports")
def reports(db: DB, status: ReportStatus = ReportStatus.OPEN, admin: User = perm(P.REPORTS_MANAGE),
            params: PageParams = Depends()):
    page = paginate(db, select(Report).where(Report.status == status).order_by(Report.created_at), params, lambda r: {
        "id": str(r.id), "target_type": r.target_type, "target_id": str(r.target_id), "reason": r.reason,
        "details": r.details, "status": r.status, "created_at": r.created_at})
    page["message_reports"] = [{"id": str(m.id), "message_id": str(m.message_id), "reason": m.reason,
                                "created_at": m.created_at}
                               for m in db.scalars(select(MessageReport).where(MessageReport.status == status).limit(50))]
    return page


class ReportActionIn(BaseModel):
    status: Literal["actioned", "dismissed"]
    resolution: str = Field(min_length=3, max_length=300)


@router.post("/reports/{report_id}")
def handle_report(report_id: uuid.UUID, data: ReportActionIn, request: Request, db: DB,
                  admin: User = perm(P.REPORTS_MANAGE)):
    r = db.get(Report, report_id)
    if not r:
        raise NotFound("Report not found")
    r.status, r.resolution, r.handled_by_id = ReportStatus(data.status), clean_text(data.resolution), admin.id
    audit(db, admin, "report.handle", "report", r.id, data.model_dump(), client_ip(request))
    db.commit()
    return {"id": str(r.id), "status": r.status}


# ---------------- settings & audit ----------------
SETTING_KEYS = {"fees", "listing_moderation_required"}


@router.get("/settings")
def get_settings(db: DB, admin: User = perm(P.SETTINGS_MANAGE)):
    from app.modules.orders.service import fee_config

    rows = {s.key: s.value for s in db.scalars(select(PlatformSetting))}
    from app.modules.bnpl.flex import rules as flex_rules

    fees = fee_config(db)
    from app.modules.marketing.service import config as marketing_config

    return {"fees": {k: str(v) for k, v in fees.items()},
            "listing_moderation_required": rows.get("listing_moderation_required", {"enabled": False}),
            "flex_rules": {k: str(v) for k, v in flex_rules(db).items()},
            "marketing": {**marketing_config(db), "capi_configured": bool(settings.meta_capi_access_token),
                          "feed_token_required": bool(settings.feed_token)}}


class FeesIn(BaseModel):
    commission_rate: Decimal = Field(ge=0, le=Decimal("0.30"))
    protection_fee_rate: Decimal = Field(ge=0, le=Decimal("0.10"))
    protection_fee_cap: Decimal = Field(ge=0, le=Decimal("1000000"))


class FlexRulesIn(BaseModel):
    max_dti: Decimal = Field(ge=Decimal("0.05"), le=Decimal("0.6"))
    tier1_max: Decimal = Field(ge=0)
    tier2_max: Decimal = Field(ge=0)
    lender_max: Decimal = Field(ge=0)
    first_plan_cap: Decimal = Field(ge=0)
    growth_per_completed_plan: Decimal = Field(ge=0, le=Decimal("5"))
    assessment_valid_days: int = Field(ge=7, le=365)
    max_active_guarantees: int = Field(3, ge=1, le=20)


class MarketingIn(BaseModel):
    feed_enabled: bool = False
    feed_excluded_categories: list[str] = Field(default_factory=list, max_length=100)
    meta_pixel_id: str = Field("", max_length=20)
    ga4_id: str = Field("", max_length=20)
    google_ads_id: str = Field("", max_length=20)
    google_ads_purchase_label: str = Field("", max_length=40)


class SettingsIn(BaseModel):
    fees: FeesIn | None = None
    marketing: MarketingIn | None = None
    listing_moderation_required: bool | None = None
    flex_rules: FlexRulesIn | None = None


@router.put("/settings")
def put_settings(data: SettingsIn, request: Request, db: DB, admin: User = perm(P.SETTINGS_MANAGE)):
    now = utcnow()

    def upsert(key, value):
        row = db.get(PlatformSetting, key)
        if row:
            row.value, row.updated_at, row.updated_by_id = value, now, admin.id
        else:
            db.add(PlatformSetting(key=key, value=value, updated_at=now, updated_by_id=admin.id))

    if data.fees:
        upsert("fees", {k: str(v) for k, v in data.fees.model_dump().items()})
    if data.listing_moderation_required is not None:
        upsert("listing_moderation_required", {"enabled": data.listing_moderation_required})
    if data.flex_rules:
        fr = data.flex_rules
        if not (fr.tier1_max <= fr.tier2_max <= fr.lender_max):
            raise AppError("Tier caps must increase: tier 1 ≤ tier 2 ≤ lender maximum")
        row = db.get(PlatformSetting, "flex_rules")
        upsert("flex_rules", {**(row.value if row else {}),
                              **{k: (str(v) if isinstance(v, Decimal) else v) for k, v in fr.model_dump().items()}})
    if data.marketing:
        from app.core.cache import cache as _cache
        from app.modules.marketing.service import ID_RULES

        m = data.marketing.model_dump()
        for k, rule in ID_RULES.items():
            m[k] = (m[k] or "").strip()
            if m[k] and not rule.match(m[k]):
                raise AppError(f"{k.replace('_', ' ')} doesn't look right", code="invalid_tracking_id")
        m["feed_excluded_categories"] = sorted({c.strip().lower() for c in m["feed_excluded_categories"] if c.strip()})
        upsert("marketing", m)
        _cache.invalidate("feed:")
        _cache.invalidate("tracking:")
    audit(db, admin, "settings.update", "settings", None, data.model_dump(mode="json", exclude_none=True),
          client_ip(request))
    db.commit()
    return get_settings(db, admin)


# ---------------- admin activity report ----------------
ACTIVITY_CATEGORIES = ("action", "auth", "view", "api")


def _activity_filters(actor_id: uuid.UUID | None, category: str | None, outcome: str | None, q: str | None,
                      days: int | None, since: str | None, until: str | None):
    from datetime import date as _date
    from datetime import datetime as _dt
    from zoneinfo import ZoneInfo

    conds = []
    if actor_id:
        conds.append(AdminAuditLog.actor_id == actor_id)
    if category:
        conds.append(AdminAuditLog.category == category)
    elif category is None:
        conds.append(AdminAuditLog.category != "view")  # page views are opt-in: they're noisy
    if outcome:
        conds.append(AdminAuditLog.outcome == outcome)
    if q:
        like = f"%{q.strip()[:80]}%"
        conds.append(or_(AdminAuditLog.action.ilike(like), AdminAuditLog.target_type.ilike(like),
                         AdminAuditLog.target_id.ilike(like), AdminAuditLog.ip.ilike(like)))
    lagos = ZoneInfo("Africa/Lagos")
    if days:
        conds.append(AdminAuditLog.created_at >= utcnow() - timedelta(days=days))
    try:
        if since:
            conds.append(AdminAuditLog.created_at >= _dt.combine(_date.fromisoformat(since), _dt.min.time(), tzinfo=lagos))
        if until:
            conds.append(AdminAuditLog.created_at < _dt.combine(_date.fromisoformat(until) + timedelta(days=1), _dt.min.time(), tzinfo=lagos))
    except ValueError as e:
        raise AppError("Dates must be YYYY-MM-DD") from e
    return conds


def _actor_map(db, ids) -> dict:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    users = db.scalars(select(User).where(User.id.in_(ids))).all()
    return {u.id: {"id": str(u.id), "name": u.full_name, "email": u.email,
                   "role": u.admin_role.name if u.admin_role else ("Super Admin" if u.is_super_admin else "Admin")}
            for u in users}


def _entry(a: AdminAuditLog, actors: dict) -> dict:
    return {"id": str(a.id), "actor": actors.get(a.actor_id) or {"id": str(a.actor_id), "name": "Unknown", "email": "", "role": ""},
            "action": a.action, "category": a.category, "outcome": a.outcome, "target_type": a.target_type,
            "target_id": a.target_id, "details": a.details, "ip": a.ip, "user_agent": a.user_agent, "created_at": a.created_at}


@router.get("/audit-logs")
def audit_logs(db: DB, params: PageParams = Depends(), actor_id: uuid.UUID | None = None,
               category: Literal["action", "auth", "view", "api", "all"] | None = None,
               outcome: Literal["success", "denied", "failed"] | None = None, q: str | None = None,
               action: str | None = None, days: int | None = Query(None, ge=1, le=366),
               since: str | None = None, until: str | None = None, admin: User = perm(P.AUDIT_VIEW)):
    conds = _activity_filters(actor_id, "" if category == "all" else category, outcome, q or action, days, since, until)
    stmt = select(AdminAuditLog).where(*conds).order_by(AdminAuditLog.created_at.desc())
    page = paginate(db, stmt, params, lambda a: a)
    actors = _actor_map(db, [a.actor_id for a in page["items"]])
    page["items"] = [_entry(a, actors) for a in page["items"]]
    return page


@router.get("/audit-logs/summary")
def audit_summary(db: DB, days: int = Query(30, ge=1, le=366), admin: User = perm(P.AUDIT_VIEW)):
    """Per-admin activity totals for the period, plus every staff member (so inactive admins show up too)."""
    since = utcnow() - timedelta(days=days)
    L = AdminAuditLog
    rows = db.execute(select(
        L.actor_id, func.count().filter(L.category == "action"), func.count().filter(L.category == "auth", L.action == "auth.sign_in"),
        func.count().filter(L.outcome != "success"), func.count().filter(L.category == "view"), func.max(L.created_at),
    ).where(L.created_at >= since).group_by(L.actor_id)).all()
    stats = {r[0]: r for r in rows}
    staff = db.scalars(select(User).where(User.account_type == AccountType.STAFF)).all()
    actors = _actor_map(db, [u.id for u in staff] + list(stats))
    last_seen = dict(db.execute(select(L.actor_id, func.max(L.created_at)).group_by(L.actor_id)).all())
    out = []
    for uid, info in actors.items():
        r = stats.get(uid)
        out.append({**info, "actions": r[1] if r else 0, "sign_ins": r[2] if r else 0, "issues": r[3] if r else 0,
                    "page_views": r[4] if r else 0, "last_active": last_seen.get(uid),
                    "is_active": next((u.is_active for u in staff if u.id == uid), True)})
    out.sort(key=lambda x: (x["actions"], x["sign_ins"]), reverse=True)
    totals = db.execute(select(func.count().filter(L.category == "action"), func.count().filter(L.category == "auth"),
                               func.count().filter(L.outcome != "success"), func.count(func.distinct(L.actor_id)))
                        .where(L.created_at >= since, L.category != "view")).one()
    return {"days": days, "admins": out,
            "totals": {"actions": totals[0], "auth_events": totals[1], "issues": totals[2], "active_admins": totals[3]}}


@router.get("/audit-logs/export")
def audit_export(db: DB, actor_id: uuid.UUID | None = None,
                 category: Literal["action", "auth", "view", "api", "all"] | None = None,
                 outcome: Literal["success", "denied", "failed"] | None = None, q: str | None = None,
                 days: int | None = Query(None, ge=1, le=366), since: str | None = None, until: str | None = None,
                 admin: User = perm(P.AUDIT_VIEW)):
    """CSV of the filtered activity (max 50,000 rows). The export itself is recorded in the log."""
    import csv
    import io
    import json

    from fastapi.responses import Response as RawResponse

    conds = _activity_filters(actor_id, "" if category == "all" else category, outcome, q, days, since, until)
    rows = db.scalars(select(AdminAuditLog).where(*conds).order_by(AdminAuditLog.created_at.desc()).limit(50_000)).all()
    actors = _actor_map(db, [r.actor_id for r in rows])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["time_utc", "admin", "email", "role", "category", "action", "outcome", "target_type", "target_id", "ip", "details"])
    for r in rows:
        a = actors.get(r.actor_id, {})
        cells = [r.created_at.isoformat(), a.get("name", ""), a.get("email", ""), a.get("role", ""), r.category, r.action,
                 r.outcome, r.target_type, r.target_id or "", r.ip or "", json.dumps(r.details, default=str)]
        w.writerow([("'" + c) if isinstance(c, str) and c[:1] in ("=", "+", "-", "@") else c for c in cells])  # CSV-injection safe
    audit(db, admin, "activity.export", "audit_log", None, {"rows": len(rows), "filters": {
        "actor_id": str(actor_id) if actor_id else None, "category": category, "outcome": outcome, "q": q, "days": days,
        "since": since, "until": until}})
    db.commit()
    return RawResponse(buf.getvalue(), media_type="text/csv",
                       headers={"Content-Disposition": f'attachment; filename="goodsng-admin-activity-{utcnow():%Y%m%d-%H%M}.csv"'})


class PageViewIn(BaseModel):
    path: str = Field(min_length=1, max_length=200, pattern=r"^/")
    title: str | None = Field(None, max_length=120)


@router.post("/activity/view", status_code=202)
def record_page_view(data: PageViewIn, db: DB, user: CurrentUser):
    """Console page viewed. One entry per admin per page per 10 minutes."""
    if not user.is_admin:
        raise Forbidden("Not an administrator")
    recent = db.scalar(select(AdminAuditLog.id).where(
        AdminAuditLog.actor_id == user.id, AdminAuditLog.category == "view", AdminAuditLog.target_id == data.path[:80],
        AdminAuditLog.created_at > utcnow() - timedelta(minutes=10)).limit(1))
    audit(db, user, "page.view", "page", data.path[:80], {"title": clean_text(data.title)} if data.title else {}, category="view")
    if recent:
        db.rollback()
        return {"recorded": False}
    db.commit()
    return {"recorded": True}


__all__ = ["SETTING_KEYS"]
