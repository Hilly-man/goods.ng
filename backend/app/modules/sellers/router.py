import uuid
from datetime import timedelta
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel, Field, field_validator
from slugify import slugify
from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.deps import DB, CurrentSeller, CurrentUser, OptionalUser, client_ip
from app.core.errors import AppError, Conflict, Forbidden, NotFound
from app.core.security import clean_text, encrypt_field
from app.core.time import utcnow
from app.integrations.storage import store_image, store_private_document
from app.models import (
    ContactEvent,
    Conversation,
    Negotiation,
    Order,
    Product,
    ProductView,
    SellerProfile,
    SellerVerification,
)
from app.models.enums import (
    ContactChannel,
    EscrowStatus,
    NegotiationStatus,
    ProductStatus,
    VerificationLevel,
    VerificationStatus,
)
from app.modules.auth.schemas import normalize_ng_phone
from app.modules.common import Page, PageParams
from app.modules.locations import canonical_city
from app.modules.products import service as products
from app.modules.products.schemas import NG_STATES, ProductCard
from app.modules.subscriptions.premium import active_subscription, is_premium

router = APIRouter(tags=["sellers"])

PREMIUM_FIELDS = {"whatsapp_enabled", "phone_enabled", "banner_url", "business_hours", "website"}
DIRECT_CONTACT_WARNING = (
    "You are contacting this seller directly. Transactions completed outside Goods.ng Protected Checkout are "
    "not covered by our escrow protection or transaction dispute resolution process. For safer transactions, "
    "use Goods.ng Protected Checkout."
)


class SellerCreate(BaseModel):
    store_name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(None, max_length=2000)
    state: str
    city: str = Field(min_length=2, max_length=80)
    address: str | None = Field(None, max_length=300)
    business_phone: str | None = None

    @field_validator("state")
    @classmethod
    def _state(cls, v):
        if v not in NG_STATES:
            raise ValueError("Select a valid Nigerian state")
        return v

    @field_validator("business_phone")
    @classmethod
    def _phone(cls, v):
        return normalize_ng_phone(v) if v else None


class SellerUpdate(BaseModel):
    store_name: str | None = Field(None, min_length=2, max_length=120)
    description: str | None = Field(None, max_length=2000)
    state: str | None = None
    city: str | None = Field(None, max_length=80)
    address: str | None = Field(None, max_length=300)
    business_phone: str | None = None
    whatsapp_number: str | None = None
    whatsapp_enabled: bool | None = None
    phone_enabled: bool | None = None
    business_hours: str | None = Field(None, max_length=200)
    website: str | None = Field(None, max_length=300, pattern=r"^https?://")

    @field_validator("business_phone", "whatsapp_number")
    @classmethod
    def _phone(cls, v):
        return normalize_ng_phone(v) if v else v


def seller_private_out(db, s: SellerProfile) -> dict:
    sub = active_subscription(db, s.id)
    return {
        "id": str(s.id), "store_name": s.store_name, "slug": s.slug, "description": s.description,
        "logo_url": s.logo_url, "banner_url": s.banner_url, "business_phone": s.business_phone,
        "whatsapp_number": s.whatsapp_number, "whatsapp_enabled": s.whatsapp_enabled, "phone_enabled": s.phone_enabled,
        "state": s.state, "city": s.city, "address": s.address, "business_hours": s.business_hours,
        "website": s.website, "verification_level": s.verification_level, "rating_avg": str(s.rating_avg),
        "rating_count": s.rating_count, "completed_sales": s.completed_sales, "is_suspended": s.is_suspended,
        "is_premium": sub is not None,
        "subscription": {"plan": sub.plan.name, "plan_code": sub.plan.code,
                         "current_period_end": sub.current_period_end} if sub else None,
        "created_at": s.created_at,
    }


def seller_public_out(db, s: SellerProfile) -> dict:
    premium = is_premium(db, s.id)
    card = products.seller_card(s, premium).model_dump(mode="json")
    card.update(
        description=s.description,
        banner_url=s.banner_url if premium else None,
        business_hours=s.business_hours if premium else None,
        website=s.website if premium else None,
        active_listings=db.scalar(select(func.count()).select_from(Product).where(
            Product.seller_id == s.id, Product.status == ProductStatus.ACTIVE, Product.deleted_at.is_(None))),
    )
    return card


@router.post("/sellers", status_code=201)
def become_seller(data: SellerCreate, user: CurrentUser, db: DB):
    if db.scalars(select(SellerProfile).where(SellerProfile.user_id == user.id)).first():
        raise Conflict("You already have a seller profile")
    base = slugify(data.store_name)[:120] or "store"
    slug = base
    if db.scalars(select(SellerProfile).where(SellerProfile.slug == slug)).first():
        slug = f"{base}-{uuid.uuid4().hex[:6]}"
    s = SellerProfile(
        user_id=user.id, store_name=clean_text(data.store_name), slug=slug, description=clean_text(data.description),
        state=data.state, city=canonical_city(db, data.state, clean_text(data.city)), address=clean_text(data.address),
        business_phone=data.business_phone or user.phone,
        verification_level=VerificationLevel.PHONE if user.phone_verified else VerificationLevel.UNVERIFIED,
    )
    db.add(s)
    db.commit()
    return seller_private_out(db, s)


@router.get("/sellers/me")
def my_seller(seller: CurrentSeller, db: DB):
    return seller_private_out(db, seller)


@router.patch("/sellers/me")
def update_seller(data: SellerUpdate, seller: CurrentSeller, db: DB):
    values = data.model_dump(exclude_unset=True)
    premium = is_premium(db, seller.id)
    # Premium features are enforced server-side; the client cannot grant them to itself.
    wants_premium = [k for k in PREMIUM_FIELDS & values.keys() if values[k] not in (None, False, "")]
    if wants_premium and not premium:
        raise Forbidden("This feature requires an active Premium Seller subscription", code="premium_required",
                        details={"fields": wants_premium})
    if values.get("state") and values["state"] not in NG_STATES:
        raise AppError("Select a valid Nigerian state")
    if values.get("whatsapp_enabled") and not (values.get("whatsapp_number") or seller.whatsapp_number):
        raise AppError("Add a WhatsApp number first")
    if values.get("phone_enabled") and not (values.get("business_phone") or seller.business_phone):
        raise AppError("Add a business phone number first")
    if "state" in values or "city" in values:
        values["city"] = canonical_city(db, values.get("state", seller.state), values.get("city", seller.city))
    for k, v in values.items():
        setattr(seller, k, clean_text(v) if isinstance(v, str) else v)
    db.commit()
    return seller_private_out(db, seller)


@router.post("/sellers/me/logo")
async def upload_logo(seller: CurrentSeller, db: DB, file: UploadFile = File(...)):
    seller.logo_url = store_image(await file.read(), "sellers/logos").thumb_url
    db.commit()
    return seller_private_out(db, seller)


@router.post("/sellers/me/banner")
async def upload_banner(seller: CurrentSeller, db: DB, file: UploadFile = File(...)):
    if not is_premium(db, seller.id):
        raise Forbidden("Storefront banners are a Premium Seller feature", code="premium_required")
    seller.banner_url = store_image(await file.read(), "sellers/banners").url
    db.commit()
    return seller_private_out(db, seller)


# ---------------- verification ----------------
DOC_TYPES = {"nin", "bvn", "drivers_licence", "intl_passport", "voters_card", "cac"}


@router.post("/sellers/me/verification", status_code=201)
async def submit_verification(
    seller: CurrentSeller,
    user: CurrentUser,
    db: DB,
    level: Literal["identity_verified", "business_verified"] = Form(...),
    document_type: str = Form(...),
    document_number: str = Form(..., min_length=5, max_length=40),
    business_name: str | None = Form(None, max_length=200),
    file: UploadFile = File(...),
):
    if document_type not in DOC_TYPES:
        raise AppError("Unsupported document type")
    if level == "business_verified" and document_type != "cac":
        raise AppError("Business verification requires a CAC registration document")
    if not user.phone_verified:
        raise AppError("Verify your phone number before submitting identity documents", code="phone_unverified")
    if db.scalars(select(SellerVerification).where(SellerVerification.seller_id == seller.id,
                                                   SellerVerification.status == VerificationStatus.PENDING)).first():
        raise Conflict("You already have a verification request under review")
    number = "".join(ch for ch in document_number if ch.isalnum())
    key = store_private_document(await file.read(), f"kyc/{seller.id}")
    v = SellerVerification(seller_id=seller.id, level_requested=VerificationLevel(level), document_type=document_type,
                           document_number_enc=encrypt_field(number), document_number_last4=number[-4:],
                           document_file_key=key, business_name=clean_text(business_name))
    db.add(v)
    db.commit()
    return {"id": str(v.id), "status": v.status, "level_requested": v.level_requested}


@router.get("/sellers/me/verification")
def my_verifications(seller: CurrentSeller, db: DB):
    rows = db.scalars(select(SellerVerification).where(SellerVerification.seller_id == seller.id)
                      .order_by(SellerVerification.created_at.desc())).all()
    return {
        "current_level": seller.verification_level,
        "requests": [{"id": str(v.id), "level_requested": v.level_requested, "document_type": v.document_type,
                      "document_number": f"••••{v.document_number_last4}", "status": v.status,
                      "review_notes": v.review_notes, "created_at": v.created_at, "reviewed_at": v.reviewed_at}
                     for v in rows],
    }


# ---------------- dashboard & analytics ----------------
@router.get("/sellers/me/dashboard")
def dashboard(seller: CurrentSeller, db: DB):
    def count(stmt):
        return db.scalar(stmt) or 0

    P = Product
    live = (P.seller_id == seller.id) & P.deleted_at.is_(None)
    agg = db.execute(select(func.count(), func.coalesce(func.sum(P.views_count), 0),
                            func.coalesce(func.sum(P.enquiries_count), 0), func.coalesce(func.sum(P.contact_clicks), 0))
                     .where(live)).one()
    active = count(select(func.count()).select_from(P).where(live, P.status == ProductStatus.ACTIVE))
    pending_statuses = [EscrowStatus.AWAITING_SELLER, EscrowStatus.PROCESSING]
    in_transit = [EscrowStatus.DISPATCHED, EscrowStatus.DELIVERED, EscrowStatus.AWAITING_BUYER_CONFIRMATION]
    o = Order
    pending = count(select(func.count()).select_from(o).where(o.seller_id == seller.id, o.status.in_(pending_statuses)))
    shipping = count(select(func.count()).select_from(o).where(o.seller_id == seller.id, o.status.in_(in_transit)))
    completed = count(select(func.count()).select_from(o).where(o.seller_id == seller.id,
                                                                o.status == EscrowStatus.COMPLETED))
    protected = count(select(func.count()).select_from(o).where(o.seller_id == seller.id, o.paid_at.isnot(None)))
    revenue = db.scalar(select(func.coalesce(func.sum(o.subtotal), 0)).where(
        o.seller_id == seller.id, o.status == EscrowStatus.COMPLETED))
    open_offers = count(select(func.count()).select_from(Negotiation).where(
        Negotiation.seller_id == seller.id, Negotiation.status == NegotiationStatus.OPEN))
    unread_convos = count(select(func.count()).select_from(Conversation).where(
        Conversation.seller_user_id == seller.user_id))
    return {
        "total_listings": agg[0], "active_listings": active, "product_views": int(agg[1]),
        "enquiries": int(agg[2]), "contact_clicks": int(agg[3]), "pending_orders": pending,
        "orders_in_transit": shipping, "completed_orders": completed, "protected_sales": protected,
        "revenue_completed": f"{revenue:.2f}", "open_negotiations": open_offers, "conversations": unread_convos,
        "is_premium": is_premium(db, seller.id), "verification_level": seller.verification_level,
    }


@router.get("/sellers/me/analytics")
def analytics(seller: CurrentSeller, db: DB, days: int = 30):
    days = max(7, min(days, 90))
    since = utcnow() - timedelta(days=days)
    premium = is_premium(db, seller.id)
    day = func.date_trunc("day", ProductView.created_at)
    views = db.execute(select(day, func.count()).where(ProductView.seller_id == seller.id, ProductView.created_at >= since)
                       .group_by(day).order_by(day)).all()
    result = {"premium": premium, "days": days,
              "views_by_day": [{"date": d.date().isoformat(), "views": c} for d, c in views]}
    if not premium:
        result["locked"] = ["contacts_by_channel", "contacts_by_day", "top_products", "conversion"]
        return result
    cday = func.date_trunc("day", ContactEvent.created_at)
    by_channel = db.execute(select(ContactEvent.channel, func.count()).where(
        ContactEvent.seller_id == seller.id, ContactEvent.created_at >= since).group_by(ContactEvent.channel)).all()
    by_day = db.execute(select(cday, func.count()).where(ContactEvent.seller_id == seller.id,
                                                         ContactEvent.created_at >= since).group_by(cday).order_by(cday)).all()
    top = db.execute(select(Product.id, Product.title, Product.slug, Product.views_count, Product.contact_clicks,
                            Product.enquiries_count, Product.favourites_count)
                     .where(Product.seller_id == seller.id, Product.deleted_at.is_(None))
                     .order_by(Product.views_count.desc()).limit(10)).all()
    total_views = sum(c for _, c in views) or 0
    total_contacts = sum(c for _, c in by_channel) or 0
    result.update(
        contacts_by_channel={ch.value if hasattr(ch, "value") else ch: c for ch, c in by_channel},
        contacts_by_day=[{"date": d.date().isoformat(), "contacts": c} for d, c in by_day],
        top_products=[{"id": str(r[0]), "title": r[1], "slug": r[2], "views": r[3], "contact_clicks": r[4],
                       "enquiries": r[5], "favourites": r[6]} for r in top],
        conversion={"views": total_views, "contacts": total_contacts,
                    "rate": round(total_contacts / total_views * 100, 1) if total_views else 0},
    )
    return result


# ---------------- public storefront ----------------
@router.get("/sellers/{slug}")
def storefront(slug: str, db: DB):
    s = db.scalars(select(SellerProfile).where(SellerProfile.slug == slug)).first()
    if not s or s.is_suspended:
        raise NotFound("Seller not found")
    return seller_public_out(db, s)


@router.get("/sellers/{slug}/products", response_model=Page[ProductCard])
def storefront_products(slug: str, db: DB, user: OptionalUser, sort: str = "newest", params: PageParams = Depends()):
    from app.modules.common import paginate

    s = db.scalars(select(SellerProfile).where(SellerProfile.slug == slug)).first()
    if not s or s.is_suspended:
        raise NotFound("Seller not found")
    page = paginate(db, products.search(db, seller_id=s.id, sort=sort if sort in products.VALID_SORTS else "newest"),
                    params)
    page["items"] = products.to_cards(db, page["items"], user.id if user else None)
    return page


class ContactIn(BaseModel):
    channel: Literal["whatsapp", "phone"]
    product_id: uuid.UUID | None = None
    acknowledged_warning: bool = False


@router.get("/contact-warning")
def contact_warning():
    return {"warning": DIRECT_CONTACT_WARNING}


@router.post("/sellers/{seller_id}/contact")
def contact_seller(seller_id: uuid.UUID, data: ContactIn, request: Request, db: DB, user: OptionalUser):
    """Reveal a premium seller's WhatsApp/phone link. Requires acknowledging the off-platform warning."""
    from app.core.cache import check_rate_limit

    check_rate_limit(f"contact:{user.id if user else client_ip(request)}", 30, 3600)
    s = db.get(SellerProfile, seller_id)
    if not s or s.is_suspended:
        raise NotFound("Seller not found")
    if not data.acknowledged_warning:
        raise AppError(DIRECT_CONTACT_WARNING, code="warning_not_acknowledged")
    if not is_premium(db, s.id):
        raise Forbidden("Direct contact is not available for this seller. Use in-app chat instead.",
                        code="direct_contact_unavailable")
    product = None
    if data.product_id:
        product = db.get(Product, data.product_id)
        if not product or product.seller_id != s.id:
            raise AppError("Listing does not belong to this seller")
    if data.channel == "whatsapp":
        if not (s.whatsapp_enabled and s.whatsapp_number):
            raise Forbidden("This seller has not enabled WhatsApp contact", code="direct_contact_unavailable")
        msg = "Hello, I found your store on Goods.ng."
        if product:
            msg = (f"Hello, I'm interested in your listing \"{product.title}\" on Goods.ng: "
                   f"{settings.frontend_url}/item/{product.slug}")
        link = f"https://wa.me/{s.whatsapp_number.lstrip('+')}?text={quote(msg)}"
        display = s.whatsapp_number
    else:
        if not (s.phone_enabled and s.business_phone):
            raise Forbidden("This seller has not enabled phone contact", code="direct_contact_unavailable")
        link, display = f"tel:{s.business_phone}", s.business_phone
    db.add(ContactEvent(product_id=product.id if product else None, seller_id=s.id, user_id=user.id if user else None,
                        channel=ContactChannel(data.channel), warning_acknowledged=True, created_at=utcnow()))
    if product:
        db.execute(update(Product).where(Product.id == product.id).values(contact_clicks=Product.contact_clicks + 1))
    db.commit()
    return {"link": link, "display": display, "channel": data.channel, "warning": DIRECT_CONTACT_WARNING}
