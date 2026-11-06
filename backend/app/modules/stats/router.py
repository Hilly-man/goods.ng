"""Public marketplace figures for the About page and other marketing surfaces.

Every number comes straight from the database: nothing is hard-coded or inflated. The result is
cached for a few seconds (single-flight) so a burst of visitors polling the page costs one set of
COUNT queries, not one per visitor.
"""

from datetime import timedelta

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.deps import DB
from app.core.time import utcnow
from app.models import Category, Order, Product, SellerProfile
from app.models.enums import EscrowStatus, ProductStatus, VerificationLevel

router = APIRouter(prefix="/stats", tags=["stats"])
CACHE_KEY = "stats:public"
CACHE_TTL = 10  # seconds — clients poll every ~15s


def compute_public_stats(db: Session) -> dict:
    now = utcnow()
    live = (Product.status == ProductStatus.ACTIVE, Product.deleted_at.is_(None))
    live_ads, new_24h, states, cities = db.execute(
        select(
            func.count(),
            func.count().filter(Product.created_at >= now - timedelta(hours=24)),
            func.count(func.distinct(Product.state)),
            func.count(func.distinct(func.concat(Product.state, "|", Product.city))),
        ).where(*live)
    ).one()
    sellers, verified = db.execute(
        select(func.count(), func.count().filter(SellerProfile.verification_level != VerificationLevel.UNVERIFIED))
        .where(SellerProfile.is_suspended.is_(False))
    ).one()
    categories = db.scalar(select(func.count()).select_from(Category).where(
        Category.is_active.is_(True), Category.parent_id.is_(None)))
    completed = db.scalar(select(func.count()).select_from(Order).where(Order.status == EscrowStatus.COMPLETED))
    return {
        "live_ads": live_ads, "new_ads_24h": new_24h, "sellers": sellers, "verified_sellers": verified,
        "completed_orders": completed or 0, "categories": categories or 0,
        "states_with_ads": states, "cities_with_ads": cities, "updated_at": now.isoformat(),
    }


@router.get("/public")
def public_stats(db: DB):
    return cache.get_or_compute(CACHE_KEY, CACHE_TTL, lambda: compute_public_stats(db))
