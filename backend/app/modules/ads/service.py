"""Sponsored placements for Premium sellers.

Where they appear (always labelled "Sponsored"):
  search / category results  — up to 3 per page, at positions 1, 6 and 12 (≈12% of a 24-item page; hard cap 20%)
  item page                  — "More from trusted sellers" (same category, other sellers)
  Recommended for you        — 1 slot in every 5, only when it matches the visitor's interests
  home                       — "Top Premium stores"

Who is eligible (QUALITY BAR — poor listings don't sell and cost buyer trust):
  active Premium subscription · seller ID- or business-verified · seller not suspended
  · listing live · at least MIN_PHOTOS photos · description of at least MIN_DESCRIPTION characters

Fairness: candidates are picked at random among the eligible (rotation) and at most one listing per seller
per block, so no single seller can take over a page. Sponsored listings always match the buyer's filters.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.errors import AppError, Forbidden, NotFound
from app.core.time import utcnow
from app.models import AdEvent, Product, ProductImage, SellerProfile, SubscriptionPlan
from app.models.enums import VerificationLevel
from app.modules.products.service import base_query, public_filter
from app.modules.subscriptions.premium import active_subscription, premium_exists_for

MIN_PHOTOS = 3
MIN_DESCRIPTION = 60
SLOTS = (0, 5, 11)          # positions 1, 6 and 12 on a results page
MAX_SHARE = 0.20            # never more than 20% of a page is sponsored
PLACEMENTS = {"search", "category", "item", "for_you", "home", "seller"}
BUMPS_PER_DAY = {"business_annual": 3}  # every other Premium plan: 1
LAGOS = ZoneInfo("Africa/Lagos")


def eligible():
    """SQL conditions a listing must meet to be shown as Sponsored."""
    photos = select(func.count()).select_from(ProductImage).where(ProductImage.product_id == Product.id).scalar_subquery()
    premium_visibility = or_(
        premium_exists_for(Product.seller_id),
        # A single-listing Boost Premium purchase gets the same sponsored eligibility as a
        # Premium seller, but only while its paid window is running.
        and_(Product.promoted_tier == "premium", Product.is_featured.is_(True),
             or_(Product.featured_until.is_(None), Product.featured_until > func.now())),
    )
    return and_(
        public_filter(),
        premium_visibility,
        # Same meaning of "verified" as the rest of the site: ID or business verified (not just a phone).
        Product.seller.has(SellerProfile.verification_level.in_([VerificationLevel.IDENTITY, VerificationLevel.BUSINESS])),
        photos >= MIN_PHOTOS,
        func.length(Product.description) >= MIN_DESCRIPTION,
    )


def pick(db: Session, conditions: list, *, exclude_ids=(), exclude_sellers=(), n: int = 3) -> list[Product]:
    """Random (rotating) eligible listings matching `conditions`, one per seller."""
    stmt = base_query().where(eligible(), *conditions)
    if exclude_ids:
        stmt = stmt.where(Product.id.not_in(list(exclude_ids)))
    if exclude_sellers:
        stmt = stmt.where(Product.seller_id.not_in(list(exclude_sellers)))
    rows = db.scalars(stmt.order_by(func.random()).limit(n * 6)).unique().all()
    out, seen = [], set()
    for p in rows:
        if p.seller_id in seen:
            continue
        seen.add(p.seller_id)
        out.append(p)
        if len(out) == n:
            break
    return out


def blend(organic: list, sponsored: list, page_size: int) -> list[tuple[object, bool]]:
    """Insert sponsored items at SLOTS. Returns [(item, is_sponsored)], respecting the MAX_SHARE cap."""
    cap = max(0, min(len(SLOTS), int(page_size * MAX_SHARE)))
    sponsored = sponsored[:cap]
    out = [(x, False) for x in organic]
    for slot, s in zip(SLOTS, sponsored, strict=False):  # fewer sponsored than slots is normal
        out.insert(min(slot, len(out)), (s, True))
    return out


# ---------------- bump to top ----------------

def _today_start() -> datetime:
    now = datetime.now(LAGOS)
    return datetime(now.year, now.month, now.day, tzinfo=LAGOS)


def bump_quota(db: Session, seller: SellerProfile) -> dict:
    sub = active_subscription(db, seller.id)
    if not sub:
        return {"premium": False, "allowed": 0, "used": 0, "remaining": 0}
    plan = db.get(SubscriptionPlan, sub.plan_id)
    allowed = BUMPS_PER_DAY.get(plan.code if plan else "", 1)
    used = db.scalar(select(func.count()).select_from(AdEvent).where(
        AdEvent.seller_id == seller.id, AdEvent.kind == "bump", AdEvent.created_at >= _today_start())) or 0
    return {"premium": True, "allowed": allowed, "used": used, "remaining": max(allowed - used, 0)}


def bump(db: Session, seller: SellerProfile, product_id) -> Product:
    p = db.query(Product).filter_by(id=product_id).with_for_update().one_or_none()
    if not p or p.seller_id != seller.id or p.deleted_at:
        raise NotFound("Listing not found")
    q = bump_quota(db, seller)
    if not q["premium"]:
        raise Forbidden("Bump to top is a Premium Seller feature", code="premium_required")
    if q["remaining"] <= 0:
        raise AppError(f"You've used today's {q['allowed']} bump{'s' if q['allowed'] != 1 else ''}. Try again tomorrow.",
                       code="bump_quota_used", status_code=429)
    from app.models.enums import ProductStatus

    if p.status != ProductStatus.ACTIVE:
        raise AppError("Only live listings can be bumped", code="listing_not_live")
    p.bumped_at = utcnow()
    db.add(AdEvent(kind="bump", placement="seller", product_id=p.id, seller_id=seller.id, viewer=None))
    db.commit()
    cache.invalidate("feed:")
    return p


# ---------------- measurement ----------------

def record(db: Session, events: list[dict], viewer: str | None) -> int:
    """Store impressions/clicks. Impressions are de-duplicated per viewer, listing and placement for an hour."""
    ids = {e["product_id"] for e in events}
    sellers = dict(db.execute(select(Product.id, Product.seller_id).where(Product.id.in_(ids))).all()) if ids else {}
    n = 0
    for e in events:
        sid = sellers.get(e["product_id"])
        if not sid or e["placement"] not in PLACEMENTS:
            continue
        if e["kind"] == "impression" and viewer:
            key = f"adimp:{viewer}:{e['product_id']}:{e['placement']}"
            if cache.get_json(key):
                continue
            cache.set_json(key, 1, ttl=3600)
        db.add(AdEvent(kind=e["kind"], placement=e["placement"], product_id=e["product_id"], seller_id=sid,
                       viewer=viewer, created_at=utcnow()))
        n += 1
    db.commit()
    return n


def seller_summary(db: Session, seller: SellerProfile, days: int = 30) -> dict:
    since = utcnow() - timedelta(days=days)
    rows = db.execute(select(AdEvent.placement, AdEvent.kind, func.count()).where(
        AdEvent.seller_id == seller.id, AdEvent.created_at >= since).group_by(AdEvent.placement, AdEvent.kind)).all()
    by = {}
    for placement, kind, c in rows:
        by.setdefault(placement, {"impressions": 0, "clicks": 0, "bumps": 0})[kind + "s" if kind != "impression" else "impressions"] = c
    imps = sum(v["impressions"] for v in by.values())
    clicks = sum(v["clicks"] for v in by.values())
    top = db.execute(select(Product.id, Product.title, Product.slug,
                            func.count().filter(AdEvent.kind == "impression"), func.count().filter(AdEvent.kind == "click"))
                     .join(AdEvent, AdEvent.product_id == Product.id)
                     .where(AdEvent.seller_id == seller.id, AdEvent.created_at >= since, AdEvent.kind != "bump")
                     .group_by(Product.id).order_by(func.count().filter(AdEvent.kind == "click").desc()).limit(5)).all()
    q = bump_quota(db, seller)
    from_ads = _from_ads(db, seller, since)
    eligible_count = db.scalar(select(func.count()).select_from(Product).where(Product.seller_id == seller.id, eligible())) or 0
    live = db.scalar(select(func.count()).select_from(Product).where(Product.seller_id == seller.id, public_filter())) or 0
    return {
        "days": days, "impressions": imps, "clicks": clicks, "ctr": round(clicks / imps * 100, 1) if imps else 0,
        "by_placement": by, "bumps": q, "from_ads": from_ads, "eligible_listings": eligible_count, "live_listings": live,
        "quality_bar": {"min_photos": MIN_PHOTOS, "min_description": MIN_DESCRIPTION, "verified_seller": True},
        "top_listings": [{"id": str(i), "title": t, "slug": s, "impressions": im, "clicks": cl} for i, t, s, im, cl in top],
    }


AD_SOURCES = ("google", "bing", "facebook", "instagram", "youtube", "tiktok")
ATTRIBUTION_DAYS = 7


def _from_ads(db: Session, seller: SellerProfile, since) -> dict:
    """Visits to this seller's listings that arrived from Google/Facebook/etc., and orders that followed them."""
    from sqlalchemy import exists

    from app.models import InterestSignal, Order, OrderItem

    visits = db.scalar(select(func.count()).select_from(InterestSignal).join(Product, Product.id == InterestSignal.product_id).where(
        Product.seller_id == seller.id, InterestSignal.kind == "landing", InterestSignal.source.in_(AD_SOURCES),
        InterestSignal.created_at >= since)) or 0
    landed = exists().where(
        InterestSignal.user_id == Order.buyer_id, InterestSignal.kind == "landing", InterestSignal.source.in_(AD_SOURCES),
        InterestSignal.product_id == OrderItem.product_id, InterestSignal.created_at <= Order.created_at,
        InterestSignal.created_at >= Order.created_at - timedelta(days=ATTRIBUTION_DAYS))
    orders = db.scalar(select(func.count(func.distinct(Order.id))).select_from(Order).join(OrderItem, OrderItem.order_id == Order.id).where(
        Order.seller_id == seller.id, Order.paid_at.isnot(None), Order.paid_at >= since, landed)) or 0
    return {"visits": visits, "orders": orders, "attribution_days": ATTRIBUTION_DAYS}
