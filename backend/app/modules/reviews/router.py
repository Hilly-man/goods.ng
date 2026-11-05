"""Ratings & reviews.

Manipulation guards:
* verified-purchase reviews only from the buyer of a COMPLETED protected order, one per order
* unverified reviews require a real prior conversation in which the seller replied, one per seller
* no self-reviews; rating aggregates are recomputed server-side from published reviews only
"""

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentSeller, CurrentUser
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.security import clean_text
from app.core.time import utcnow
from app.models import Conversation, Message, Order, Product, Review, ReviewReport, SellerProfile
from app.models.enums import EscrowStatus, ReviewStatus
from app.modules.common import PageParams, paginate
from app.modules.notifications.service import notify

router = APIRouter(tags=["reviews"])


class ReviewIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(None, max_length=120)
    comment: str | None = Field(None, max_length=2000)
    order_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None  # for unverified reviews
    product_id: uuid.UUID | None = None


def recompute_rating(db: Session, seller_id) -> None:
    avg, cnt = db.execute(select(func.coalesce(func.avg(Review.rating), 0), func.count()).where(
        Review.seller_id == seller_id, Review.status == ReviewStatus.PUBLISHED)).one()
    s = db.get(SellerProfile, seller_id)
    s.rating_avg, s.rating_count = round(avg, 2), cnt


def review_out(r: Review) -> dict:
    name = r.reviewer.full_name.split()
    return {"id": str(r.id), "rating": r.rating, "title": r.title, "comment": r.comment,
            "reviewer": f"{name[0]} {name[-1][0]}." if len(name) > 1 else name[0],
            "is_verified_purchase": r.is_verified_purchase, "seller_reply": r.seller_reply,
            "product_id": str(r.product_id) if r.product_id else None, "created_at": r.created_at}


@router.post("/reviews", status_code=201)
def create_review(data: ReviewIn, user: CurrentUser, db: DB):
    check_rate_limit(f"review:{user.id}", 10, 86400)
    if data.order_id:
        o = db.get(Order, data.order_id)
        if not o or o.buyer_id != user.id:
            raise NotFound("Order not found")
        if o.status != EscrowStatus.COMPLETED:
            raise AppError("You can review an order once it is completed", code="order_not_completed")
        if db.scalars(select(Review).where(Review.order_id == o.id)).first():
            raise Conflict("You have already reviewed this order")
        seller_id, product_id, verified = o.seller_id, o.items[0].product_id, True
    else:
        if not data.seller_id:
            raise AppError("Choose a seller or an order to review")
        seller = db.get(SellerProfile, data.seller_id)
        if not seller:
            raise NotFound("Seller not found")
        if seller.user_id == user.id:
            raise Forbidden("You cannot review your own store")
        interacted = db.scalar(select(func.count()).select_from(Message).join(Conversation).where(
            Conversation.buyer_id == user.id, Conversation.seller_user_id == seller.user_id,
            Message.sender_id == seller.user_id))
        if not interacted:
            raise Forbidden("You can review a seller after you have chatted with them", code="no_interaction")
        if db.scalars(select(Review).where(Review.reviewer_id == user.id, Review.seller_id == seller.id,
                                           Review.order_id.is_(None))).first():
            raise Conflict("You have already reviewed this seller")
        seller_id, verified = seller.id, False
        product_id = data.product_id if data.product_id and (p := db.get(Product, data.product_id)) and \
            p.seller_id == seller.id else None
    r = Review(order_id=data.order_id, product_id=product_id, seller_id=seller_id, reviewer_id=user.id,
               rating=data.rating, title=clean_text(data.title), comment=clean_text(data.comment),
               is_verified_purchase=verified)
    db.add(r)
    db.flush()
    recompute_rating(db, seller_id)
    s = db.get(SellerProfile, seller_id)
    notify(db, s.user_id, "review", "New review", f"You received a {data.rating}-star review.", link=f"/store/{s.slug}")
    db.commit()
    db.refresh(r)
    return review_out(r)


@router.get("/sellers/{slug}/reviews")
def seller_reviews(slug: str, db: DB, params: PageParams = Depends()):
    s = db.scalars(select(SellerProfile).where(SellerProfile.slug == slug)).first()
    if not s:
        raise NotFound("Seller not found")
    stmt = select(Review).where(Review.seller_id == s.id, Review.status == ReviewStatus.PUBLISHED) \
        .order_by(Review.is_verified_purchase.desc(), Review.created_at.desc())
    page = paginate(db, stmt, params, review_out)
    dist = dict(db.execute(select(Review.rating, func.count()).where(
        Review.seller_id == s.id, Review.status == ReviewStatus.PUBLISHED).group_by(Review.rating)).all())
    page["summary"] = {"average": f"{s.rating_avg:.2f}", "count": s.rating_count,
                       "distribution": {str(k): dist.get(k, 0) for k in range(5, 0, -1)}}
    return page


@router.get("/products/{product_id}/reviews")
def product_reviews(product_id: uuid.UUID, db: DB, params: PageParams = Depends()):
    stmt = select(Review).where(Review.product_id == product_id, Review.status == ReviewStatus.PUBLISHED) \
        .order_by(Review.created_at.desc())
    return paginate(db, stmt, params, review_out)


class ReplyIn(BaseModel):
    reply: str = Field(min_length=2, max_length=1000)


@router.post("/reviews/{review_id}/reply")
def reply(review_id: uuid.UUID, data: ReplyIn, seller: CurrentSeller, db: DB):
    r = db.get(Review, review_id)
    if not r or r.seller_id != seller.id:
        raise NotFound("Review not found")
    r.seller_reply = clean_text(data.reply)
    db.commit()
    return review_out(r)


class ReportIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


@router.post("/reviews/{review_id}/report", status_code=201)
def report(review_id: uuid.UUID, data: ReportIn, user: CurrentUser, db: DB):
    r = db.get(Review, review_id)
    if not r:
        raise NotFound("Review not found")
    if not db.scalars(select(ReviewReport).where(ReviewReport.review_id == r.id,
                                                 ReviewReport.reporter_id == user.id)).first():
        db.add(ReviewReport(review_id=r.id, reporter_id=user.id, reason=clean_text(data.reason), created_at=utcnow()))
        db.commit()
    return {"reported": True}


@router.get("/reviews/eligible")
def eligible_orders(user: CurrentUser, db: DB):
    """Completed orders the buyer has not yet reviewed."""
    reviewed = select(Review.order_id).where(Review.order_id.isnot(None))
    rows = db.scalars(select(Order).where(Order.buyer_id == user.id, Order.status == EscrowStatus.COMPLETED,
                                          Order.id.not_in(reviewed)).order_by(Order.completed_at.desc())).all()
    return [{"order_id": str(o.id), "order_number": o.order_number, "title": o.items[0].title,
             "image_url": o.items[0].image_url, "seller": o.seller.store_name} for o in rows]
