"""Administration API. Every endpoint requires a specific permission; sensitive actions are audit-logged."""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.core.cache import cache
from app.core.deps import DB, CurrentUser, client_ip, require_permission
from app.core.errors import AppError, Forbidden, NotFound
from app.core.security import clean_text, decrypt_field, mask
from app.core.time import utcnow
from app.models import (
    AdminAuditLog,
    BnplApplication,
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
    PlatformSetting,
    Product,
    Promotion,
    Refund,
    Report,
    Review,
    ReviewReport,
    SellerProfile,
    SellerVerification,
    Subscription,
    SubscriptionPlan,
    User,
    WebhookEvent,
)
from app.models.enums import (
    AdminPermission as P,
)
from app.models.enums import (
    BnplStatus,
    DisputeStatus,
    EscrowStatus,
    InstallmentStatus,
    PaymentStatus,
    ProductStatus,
    RefundStatus,
    ReportStatus,
    ReviewStatus,
    UserRole,
    VerificationLevel,
    VerificationStatus,
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

router = APIRouter(prefix="/admin", tags=["admin"])


def perm(p: P):
    return Depends(require_permission(p.value))


@router.get("/me")
def admin_me(user: CurrentUser):
    if not user.is_admin:
        raise Forbidden("Not an administrator")
    perms = [p.value for p in P] if user.role == UserRole.SUPER_ADMIN else user.admin_permissions
    return {"role": user.role, "permissions": perms}


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
    stmt = select(User)
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
    if u.role == UserRole.SUPER_ADMIN or (u.is_admin and admin.role != UserRole.SUPER_ADMIN):
        raise Forbidden("Only a super administrator can change another administrator's status")
    u.is_active = data.is_active
    if not data.is_active:
        revoke_all_sessions(db, u)
    audit(db, admin, "user.status", "user", u.id, data.model_dump(), client_ip(request))
    db.commit()
    return {"id": str(u.id), "is_active": u.is_active}


class RoleIn(BaseModel):
    role: UserRole
    permissions: list[P] = []


@router.post("/users/{user_id}/role")
def set_role(user_id: uuid.UUID, data: RoleIn, request: Request, db: DB, admin: CurrentUser):
    if admin.role != UserRole.SUPER_ADMIN:
        raise Forbidden("Only a super administrator can change roles and permissions")
    u = db.get(User, user_id)
    if not u:
        raise NotFound("User not found")
    if u.id == admin.id:
        raise Forbidden("You cannot change your own role")
    u.role = data.role
    u.admin_permissions = [p.value for p in data.permissions] if data.role == UserRole.ADMIN else []
    revoke_all_sessions(db, u)
    audit(db, admin, "user.role", "user", u.id, {"role": data.role.value, "permissions": u.admin_permissions},
          client_ip(request))
    db.commit()
    return {"id": str(u.id), "role": u.role, "permissions": u.admin_permissions}


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
    return {"fees": {k: str(v) for k, v in fees.items()},
            "listing_moderation_required": rows.get("listing_moderation_required", {"enabled": False}),
            "flex_rules": {k: str(v) for k, v in flex_rules(db).items()}}


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


class SettingsIn(BaseModel):
    fees: FeesIn | None = None
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
    audit(db, admin, "settings.update", "settings", None, data.model_dump(mode="json", exclude_none=True),
          client_ip(request))
    db.commit()
    return get_settings(db, admin)


@router.get("/audit-logs")
def audit_logs(db: DB, action: str | None = None, params: PageParams = Depends(), admin: User = perm(P.AUDIT_VIEW)):
    stmt = select(AdminAuditLog)
    if action:
        stmt = stmt.where(AdminAuditLog.action.ilike(f"{action}%"))
    return paginate(db, stmt.order_by(AdminAuditLog.created_at.desc()), params, lambda a: {
        "id": str(a.id), "actor_id": str(a.actor_id), "action": a.action, "target_type": a.target_type,
        "target_id": a.target_id, "details": a.details, "ip": a.ip, "created_at": a.created_at})


__all__ = ["SETTING_KEYS"]
