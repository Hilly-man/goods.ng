"""Single source of truth for premium status: an ACTIVE subscription whose period covers *now*.

Never derived from client input or a cached flag.
"""

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.time import utcnow
from app.models import SellerProfile, Subscription
from app.models.enums import SubscriptionStatus


def active_subscription_clause():
    now = utcnow()
    return (
        (Subscription.status == SubscriptionStatus.ACTIVE)
        & (Subscription.current_period_start <= now)
        & (Subscription.current_period_end > now)
    )


def is_premium(db: Session, seller_id) -> bool:
    return bool(db.scalar(select(exists().where(Subscription.seller_id == seller_id, active_subscription_clause()))))


def active_subscription(db: Session, seller_id) -> Subscription | None:
    return db.scalars(
        select(Subscription).where(Subscription.seller_id == seller_id, active_subscription_clause())
        .order_by(Subscription.current_period_end.desc())
    ).first()


def premium_seller_ids(db: Session, seller_ids) -> set:
    if not seller_ids:
        return set()
    return set(db.scalars(
        select(Subscription.seller_id).where(Subscription.seller_id.in_(list(seller_ids)), active_subscription_clause())
    ).all())


def premium_exists_for(seller_col):
    """SQL expression usable in queries: EXISTS active subscription for seller_col."""
    return exists().where(Subscription.seller_id == seller_col, active_subscription_clause())


__all__ = ["is_premium", "active_subscription", "premium_seller_ids", "premium_exists_for", "SellerProfile"]
