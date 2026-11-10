import hashlib
import re
import uuid
from datetime import timedelta

from slugify import slugify
from sqlalchemy import Float, and_, case, desc, func, or_, select, type_coerce, update
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.cache import cache
from app.core.config import settings
from app.core.errors import AppError, Forbidden, NotFound
from app.core.security import clean_text
from app.core.time import utcnow
from app.integrations.storage import delete_stored_image
from app.models import Category, Favourite, PlatformSetting, Product, ProductImage, ProductView, SellerProfile
from app.models.enums import ProductCondition, ProductStatus, VerificationLevel
from app.modules.categories.router import descendant_ids
from app.modules.locations import canonical_city
from app.modules.products.schemas import (
    CategoryRef,
    ImageOut,
    ProductCard,
    ProductDetail,
    ProductIn,
    ProductUpdate,
    SellerCard,
    SellerProductRow,
)
from app.modules.subscriptions.premium import is_premium, premium_exists_for, premium_seller_ids

FREE_MAX_IMAGES = 5
PREMIUM_MAX_IMAGES = 10

# ---------------- title suggestions ----------------

_CONDITION_WORDS = {
    ProductCondition.BRAND_NEW: "Brand New",
    ProductCondition.FOREIGN_USED: "Foreign Used",
    ProductCondition.NIGERIAN_USED: "Nigerian Used",
    ProductCondition.REFURBISHED: "Refurbished",
}
_COLORS = [
    "Natural Titanium", "Deep Purple", "Space Black", "Sierra Blue", "Pacific Blue", "Midnight",
    "Starlight", "Graphite", "Product Red", "Rose Gold", "Space Grey", "Space Gray",
    "Black", "White", "Silver", "Gold", "Grey", "Gray", "Blue", "Navy", "Red", "Green",
    "Purple", "Pink", "Yellow", "Orange", "Brown", "Beige", "Cream", "Maroon", "Teal",
]


def _clip_title(text: str, limit: int = 140) -> str:
    text = " ".join(text.split()).strip(" ,—-")
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0].rstrip(" ,—-")
    return cut + "…"


def _detected_specs(text: str) -> tuple[str | None, list[str]]:
    """Pull the details buyers actually search for out of the free-text description."""
    year = re.search(r"\b(19[5-9]\d|20[0-4]\d)\b", text)
    storage = re.search(r"\b(\d{2,4})\s*(GB|TB)\b", text, re.I)
    color = next((c for c in _COLORS if re.search(rf"\b{re.escape(c)}\b", text, re.I)), None)
    size = re.search(r'\b(\d{2,3})\s?(?:inch|inches|")\b', text, re.I)
    extras = []
    if storage:
        extras.append(f"{storage.group(1)}{storage.group(2).upper()}")
    if color:
        extras.append(color)
    if size:
        extras.append(f"{size.group(1)}-inch")
    return (year.group(1) if year else None), extras


def suggest_titles(*, brand: str | None = None, model: str | None = None,
                   condition: ProductCondition | str | None = None, description: str | None = None,
                   current_title: str | None = None, category_name: str | None = None) -> list[str]:
    """Deterministic, keyword-rich titles built from the listing details.

    No third-party AI: brand, model, condition, category and specs already typed by the seller are
    enough to produce titles that match how buyers search. The seller can pick one or keep their own.
    """
    brand = " ".join((brand or "").split())
    model = " ".join((model or "").split())
    desc = " ".join((description or "").split())
    current = " ".join((current_title or "").split())
    category = " ".join((category_name or "").split())

    try:
        cond = ProductCondition(condition) if condition else None
    except ValueError:
        cond = None
    cond_word = _CONDITION_WORDS.get(cond, "") if cond else ""

    year, extras = _detected_specs(" ".join([current, model, desc]))

    def build(parts: list[str]) -> str:
        seen = ""
        out = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if part.lower() in seen.lower():
                continue
            out.append(part)
            seen += " " + part
        return _clip_title(" ".join(out))

    base = [model] if model else []
    if brand and (not model or not model.lower().startswith(brand.lower())):
        base = [brand, *base]
    if not base and current:
        base = [current]

    start = [year] if year else []
    cond_tail = [f"— {cond_word}"] if cond_word else []
    cond_cat = [f"— {cond_word} {category}"] if (cond_word and category) else (
        cond_tail + ([category] if category else []))
    candidates = [
        build(start + base + extras + cond_tail),
        build(base + start + extras + cond_cat),
        build(([cond_word] if cond_word else []) + start + base + extras
              + ([category] if category and category.lower() not in " ".join(base + extras).lower() else [])),
        build(([category] if category else []) + base + cond_tail),
    ]

    out: list[str] = []
    for title in candidates:
        if len(title) < 8:
            continue
        if title.lower() not in {t.lower() for t in out}:
            out.append(title)
        if len(out) == 3:
            break
    return out


# ---------------- serialisation ----------------
def seller_card(s: SellerProfile, premium: bool) -> SellerCard:
    return SellerCard(
        id=s.id, store_name=s.store_name, slug=s.slug, logo_url=s.logo_url, verification_level=s.verification_level,
        is_premium=premium, rating_avg=s.rating_avg, rating_count=s.rating_count, state=s.state, city=s.city,
        member_since=s.created_at, completed_sales=s.completed_sales,
        whatsapp_available=premium and s.whatsapp_enabled and bool(s.whatsapp_number),
        phone_available=premium and s.phone_enabled and bool(s.business_phone),
    )


def _card_kwargs(p: Product, premium: bool, fav: bool) -> dict:
    first = p.images[0] if p.images else None
    return dict(
        id=p.id, slug=p.slug, title=p.title, price=p.price, currency=p.currency, negotiable=p.negotiable,
        condition=p.condition, state=p.state, city=p.city, thumb_url=first.thumb_url if first else None,
        image_count=len(p.images), is_featured=_featured_now(p), promoted_tier=_promotion_tier_now(p),
        created_at=p.created_at,
        seller=seller_card(p.seller, premium), category=CategoryRef(id=p.category.id, name=p.category.name, slug=p.category.slug),
        protected_checkout_enabled=p.protected_checkout_enabled, bnpl_enabled=p.bnpl_enabled, is_favourite=fav,
        # Masonry cards (Jiji-style): the photo's real shape sets the card height, plus a short description.
        image_width=first.width if first else None, image_height=first.height if first else None,
        snippet=_snippet(p.description),
    )


def _snippet(text: str | None, limit: int = 110) -> str | None:
    t = " ".join((text or "").split())
    if not t:
        return None
    return t if len(t) <= limit else t[: limit - 1].rsplit(" ", 1)[0] + "…"


def _featured_now(p: Product) -> bool:
    return bool(p.is_featured and (p.featured_until is None or p.featured_until > utcnow()))


def _promotion_tier_now(p: Product) -> str | None:
    """Paid per-listing tier, only while the paid window is still running."""
    if not _featured_now(p):
        return None
    return p.promoted_tier


def favourite_ids(db: Session, user_id, product_ids) -> set:
    if not user_id or not product_ids:
        return set()
    return set(db.scalars(select(Favourite.product_id).where(Favourite.user_id == user_id,
                                                             Favourite.product_id.in_(list(product_ids)))).all())


def to_cards(db: Session, products: list[Product], user_id=None, cls=ProductCard) -> list:
    prem = premium_seller_ids(db, {p.seller_id for p in products})
    favs = favourite_ids(db, user_id, [p.id for p in products])
    out = []
    for p in products:
        kw = _card_kwargs(p, p.seller_id in prem, p.id in favs)
        if cls is SellerProductRow:
            kw.update(status=p.status, quantity=p.quantity, views_count=p.views_count, enquiries_count=p.enquiries_count,
                      contact_clicks=p.contact_clicks, favourites_count=p.favourites_count,
                      rejection_reason=p.rejection_reason, promoted_until=p.featured_until)
        out.append(cls(**kw))
    return out


def to_detail(db: Session, p: Product, user_id=None) -> ProductDetail:
    prem = bool(premium_seller_ids(db, {p.seller_id}))
    fav = bool(favourite_ids(db, user_id, [p.id]))
    path = []
    c = p.category
    while c is not None:
        path.insert(0, CategoryRef(id=c.id, name=c.name, slug=c.slug))
        c = c.parent
    return ProductDetail(
        **_card_kwargs(p, prem, fav), description=p.description, brand=p.brand, model=p.model, quantity=p.quantity,
        status=p.status, images=[ImageOut.model_validate(i) for i in p.images], delivery_options=p.delivery_options,
        views_count=p.views_count, favourites_count=p.favourites_count, published_at=p.published_at,
        updated_at=p.updated_at, category_path=path,
        subcategory=CategoryRef(id=p.subcategory.id, name=p.subcategory.name, slug=p.subcategory.slug) if p.subcategory else None,
    )


def base_query():
    return select(Product).options(
        selectinload(Product.images), joinedload(Product.seller), joinedload(Product.category)
    )


def public_filter():
    return and_(Product.status == ProductStatus.ACTIVE, Product.deleted_at.is_(None),
                Product.seller.has(SellerProfile.is_suspended.is_(False)))


# ---------------- search ----------------
_TOKEN = re.compile(r"[\w]+", re.UNICODE)


def build_tsquery(q: str) -> str | None:
    tokens = [t for t in _TOKEN.findall(q.lower()) if t][:8]
    if not tokens:
        return None
    # prefix-match every token so partial words ("iph") still find results
    return " & ".join(f"{t}:*" for t in tokens)


VALID_SORTS = {"relevance", "newest", "price_asc", "price_desc"}


FILTER_KEYS = ("q", "category", "state", "city", "min_price", "max_price", "conditions", "brand", "verified_only",
               "premium_only", "negotiable", "bnpl", "protected", "with_photos", "posted_within", "seller_id")
FLAG_KEYS = ("verified_only", "premium_only", "negotiable", "bnpl", "protected", "with_photos")


def _verified_expr():
    return Product.seller.has(SellerProfile.verification_level.in_([VerificationLevel.IDENTITY, VerificationLevel.BUSINESS]))


def flag_expr(key: str):
    return {
        "verified_only": _verified_expr(),
        "premium_only": premium_exists_for(Product.seller_id),
        "negotiable": Product.negotiable.is_(True),
        "bnpl": Product.bnpl_enabled.is_(True),
        "protected": Product.protected_checkout_enabled.is_(True),
        "with_photos": Product.images.any(),
    }[key]


def resolve_category(db: Session, slug: str | None) -> Category | None:
    if not slug:
        return None
    cat = db.scalars(select(Category).where(Category.slug == slug)).first()
    if not cat:
        raise NotFound("Category not found")
    return cat


def filter_conditions(db: Session, f: dict, exclude: frozenset = frozenset()) -> list:
    """All WHERE clauses for the given filters, optionally leaving some out (used for facet counts)."""
    conds = [public_filter()]
    on = lambda k: k not in exclude and f.get(k) not in (None, False, "", [])  # noqa: E731
    if on("q"):
        tsq = build_tsquery(f["q"])
        if tsq:
            conds.append(or_(Product.search_vector.op("@@")(func.to_tsquery("english", tsq)),
                             Product.title.ilike(f"%{f['q'][:60]}%")))
    if on("category"):
        ids = descendant_ids(db, resolve_category(db, f["category"]).id)
        conds.append(or_(Product.category_id.in_(ids), Product.subcategory_id.in_(ids)))
    if on("state"):
        conds.append(Product.state == f["state"])
    if on("city"):
        conds.append(Product.city.ilike(f["city"]))
    if on("min_price"):
        conds.append(Product.price >= f["min_price"])
    if on("max_price"):
        conds.append(Product.price <= f["max_price"])
    if on("conditions"):
        conds.append(Product.condition.in_(f["conditions"]))
    if on("brand"):
        conds.append(func.lower(Product.brand) == f["brand"].lower())
    if on("seller_id"):
        conds.append(Product.seller_id == f["seller_id"])
    if on("posted_within"):
        conds.append(Product.created_at >= utcnow() - timedelta(days=int(f["posted_within"])))
    for k in FLAG_KEYS:
        if on(k):
            conds.append(flag_expr(k))
    return conds


def search(db: Session, *, sort="relevance", **filters):
    f = {k: filters.get(k) for k in FILTER_KEYS}
    stmt = base_query().where(*filter_conditions(db, f))
    rank = None
    if f["q"] and (tsq := build_tsquery(f["q"])):
        rank = func.ts_rank(Product.search_vector, func.to_tsquery("english", tsq))
    featured = case((and_(Product.is_featured.is_(True),
                          or_(Product.featured_until.is_(None), Product.featured_until > func.now())), 1), else_=0)
    # Freshness: a Premium "bump" counts as fresh, without changing the real posted date shown to buyers.
    fresh = func.coalesce(Product.bumped_at, Product.published_at, Product.created_at)
    if sort == "newest":
        stmt = stmt.order_by(desc(fresh), desc(Product.created_at))
    elif sort == "price_asc":
        stmt = stmt.order_by(Product.price, desc(Product.created_at))
    elif sort == "price_desc":
        stmt = stmt.order_by(desc(Product.price), desc(Product.created_at))
    else:
        # Relevance: Featured listings, then Premium sellers ("priority search visibility" they pay for),
        # then text match, then freshness. Extra promoted slots (tagged "TOP") come from ads/service.py.
        premium_expr = premium_exists_for(Product.seller_id)
        order = [desc(featured), desc(case((premium_expr, 1), else_=0))]
        if rank is not None:
            order.append(desc(rank))
        order.append(desc(fresh))
        stmt = stmt.order_by(*order)
    return stmt


def _nice(v: float) -> int:
    """Round to 2 significant figures (25 000, 140 000, 8 600 000) for friendly price brackets."""
    if v <= 0:
        return 0
    mag = 10 ** (len(str(int(v))) - 2) if v >= 100 else 1
    return int(round(v / mag) * mag)


def facets(db: Session, **filters) -> dict:
    """Counts for every filter option. Each facet applies all *other* active filters (disjunctive faceting)."""
    f = {k: filters.get(k) for k in FILTER_KEYS}

    def count_where(*conds):
        return db.scalar(select(func.count()).select_from(Product).where(*conds)) or 0

    total = count_where(*filter_conditions(db, f))

    # ---- price brackets from the distribution of the current result set (ignoring the price filter)
    base_price = filter_conditions(db, f, frozenset({"min_price", "max_price"}))
    pct = type_coerce(func.percentile_cont(pg_array([0.2, 0.4, 0.6, 0.8])).within_group(Product.price), ARRAY(Float))
    qs = db.execute(select(pct).where(*base_price)).scalar()
    edges = sorted({_nice(float(x)) for x in (qs or []) if x})
    edges = [e for e in edges if e > 0]
    price_ranges = []
    if edges:
        bounds = [(None, edges[0])] + list(zip(edges, edges[1:], strict=False)) + [(edges[-1], None)]
        cols = []
        for lo, hi in bounds:
            c = and_(*([Product.price >= lo] if lo is not None else []), *([Product.price < hi] if hi is not None else []))
            cols.append(func.sum(case((c, 1), else_=0)))
        counts = db.execute(select(*cols).where(*base_price)).one()
        price_ranges = [{"min": lo, "max": hi, "count": int(n or 0)} for (lo, hi), n in zip(bounds, counts, strict=True)]

    # ---- condition
    cond_rows = db.execute(select(Product.condition, func.count())
                           .where(*filter_conditions(db, f, frozenset({"conditions"})))
                           .group_by(Product.condition)).all()
    conditions = {(c.value if hasattr(c, "value") else c): n for c, n in cond_rows}

    # ---- brand
    brand_rows = db.execute(select(Product.brand, func.count())
                            .where(*filter_conditions(db, f, frozenset({"brand"})), Product.brand.isnot(None),
                                   Product.brand != "")
                            .group_by(Product.brand).order_by(desc(func.count()), Product.brand).limit(20)).all()
    brands = [{"name": b, "count": n} for b, n in brand_rows]

    # ---- boolean flags: each counted with every other active flag applied
    base_flags = filter_conditions(db, f, frozenset(FLAG_KEYS))
    active = [k for k in FLAG_KEYS if f.get(k)]
    cols = [func.sum(case((and_(flag_expr(k), *[flag_expr(o) for o in active if o != k]), 1), else_=0)) for k in FLAG_KEYS]
    flag_counts = dict(zip(FLAG_KEYS, (int(x or 0) for x in db.execute(select(*cols).where(*base_flags)).one()), strict=True))

    # ---- categories: roots (no category) / children (root selected) / siblings (leaf selected)
    cat = resolve_category(db, f["category"])
    base_cat = filter_conditions(db, f, frozenset({"category"}))
    if cat is None:
        parent, items_of = None, db.scalars(select(Category).where(Category.parent_id.is_(None), Category.is_active.is_(True))
                                            .order_by(Category.sort_order)).all()
        rows = dict(db.execute(select(Product.category_id, func.count()).where(*base_cat).group_by(Product.category_id)).all())
    else:
        parent = cat if not cat.parent_id else db.get(Category, cat.parent_id)
        items_of = [c for c in parent.children if c.is_active]
        rows = dict(db.execute(select(Product.subcategory_id, func.count())
                               .where(*base_cat, Product.category_id == parent.id).group_by(Product.subcategory_id)).all())
    parent_total = sum(rows.values()) if parent else None
    categories = {
        "parent": {"slug": parent.slug, "name": parent.name, "count": parent_total} if parent else None,
        "current": cat.slug if cat else None,
        "items": [{"slug": c.slug, "name": c.name, "count": rows.get(c.id, 0)} for c in items_of],
    }

    return {"total": total, "price_ranges": price_ranges, "conditions": conditions, "brands": brands,
            "flags": flag_counts, "categories": categories}


def home_feed(db: Session) -> dict:
    return cache.get_or_compute("feed:home", 60, lambda: _build_home_feed(db))


def _build_home_feed(db: Session) -> dict:
    now = utcnow()
    featured = db.scalars(base_query().where(public_filter(), Product.is_featured.is_(True),
                                             or_(Product.featured_until.is_(None), Product.featured_until > now))
                          .order_by(func.random()).limit(12)).unique().all()
    trending = db.scalars(base_query().where(public_filter(), Product.created_at > now - timedelta(days=30))
                          .order_by(desc(Product.views_count + Product.favourites_count * 3 + Product.enquiries_count * 5))
                          .limit(12)).unique().all()
    recent = db.scalars(base_query().where(public_filter()).order_by(desc(Product.created_at)).limit(24)).unique().all()
    premium = db.scalars(base_query().where(public_filter(), premium_exists_for(Product.seller_id))
                         .order_by(desc(Product.created_at)).limit(12)).unique().all()
    sellers_q = select(SellerProfile).where(SellerProfile.is_suspended.is_(False))
    verified = db.scalars(sellers_q.where(SellerProfile.verification_level.in_(
        [VerificationLevel.IDENTITY, VerificationLevel.BUSINESS])).order_by(desc(SellerProfile.rating_avg)).limit(10)).all()
    prem_ids = premium_seller_ids(db, {s.id for s in verified})
    premium_sellers = db.scalars(sellers_q.where(premium_exists_for(SellerProfile.id))
                                 .order_by(desc(SellerProfile.rating_avg)).limit(10)).all()
    data = {
        "featured": [c.model_dump(mode="json") for c in to_cards(db, featured)],
        "trending": [c.model_dump(mode="json") for c in to_cards(db, trending)],
        "recent": [c.model_dump(mode="json") for c in to_cards(db, recent)],
        "premium": [c.model_dump(mode="json") for c in to_cards(db, premium)],
        "verified_sellers": [seller_card(s, s.id in prem_ids).model_dump(mode="json") for s in verified],
        "premium_sellers": [seller_card(s, True).model_dump(mode="json") for s in premium_sellers],
    }
    return data


# ---------------- CRUD ----------------
def _unique_slug(db: Session, title: str) -> str:
    base = slugify(title)[:150] or "item"
    return f"{base}-{uuid.uuid4().hex[:8]}"


def _resolve_category(db: Session, category_id) -> tuple[uuid.UUID, uuid.UUID | None]:
    cat = db.get(Category, category_id)
    if not cat or not cat.is_active:
        raise AppError("Select a valid category", code="invalid_category")
    if cat.parent_id:
        return cat.parent_id, cat.id
    if any(c.is_active for c in cat.children):
        raise AppError("Select a subcategory", code="validation_error", status_code=422,
                       details=[{"field": "subcategory", "message": f"Choose a subcategory of {cat.name}"}])
    return cat.id, None


def _moderation_required(db: Session) -> bool:
    s = db.get(PlatformSetting, "listing_moderation_required")
    return bool(s and s.value.get("enabled"))


def create_product(db: Session, seller: SellerProfile, data: ProductIn) -> Product:
    cat_id, sub_id = _resolve_category(db, data.category_id)
    city = canonical_city(db, data.state, clean_text(data.city))
    status = ProductStatus.PENDING_REVIEW if _moderation_required(db) else ProductStatus.ACTIVE
    p = Product(
        seller_id=seller.id, category_id=cat_id, subcategory_id=sub_id, title=clean_text(data.title),
        slug=_unique_slug(db, data.title), description=clean_text(data.description), brand=clean_text(data.brand),
        model=clean_text(data.model), condition=data.condition, price=data.price, negotiable=data.negotiable,
        quantity=data.quantity, state=data.state, city=city,
        delivery_options=[o.model_dump(mode="json") for o in data.delivery_options],
        protected_checkout_enabled=data.protected_checkout_enabled, bnpl_enabled=data.bnpl_enabled, status=status,
        published_at=utcnow() if status == ProductStatus.ACTIVE else None,
    )
    db.add(p)
    db.commit()
    cache.invalidate("feed:")
    cache.invalidate("categories:")
    return p


def get_owned(db: Session, seller: SellerProfile, product_id) -> Product:
    p = db.scalars(base_query().where(Product.id == product_id, Product.deleted_at.is_(None))).first()
    if not p:
        raise NotFound("Listing not found")
    if p.seller_id != seller.id:
        raise Forbidden("You can only manage your own listings")
    return p


def update_product(db: Session, seller: SellerProfile, product_id, data: ProductUpdate) -> Product:
    p = get_owned(db, seller, product_id)
    values = data.model_dump(exclude_unset=True)
    if "category_id" in values:
        p.category_id, p.subcategory_id = _resolve_category(db, values.pop("category_id"))
    for k in ("title", "description", "brand", "model", "city"):
        if k in values:
            values[k] = clean_text(values[k])
    if "delivery_options" in values:
        values["delivery_options"] = [o.model_dump(mode="json") for o in data.delivery_options]
    if "state" in values or "city" in values:
        values["city"] = canonical_city(db, values.get("state", p.state), values.get("city", p.city))
    for k, v in values.items():
        setattr(p, k, v)
    if p.status == ProductStatus.REJECTED:
        p.status, p.rejection_reason = ProductStatus.PENDING_REVIEW, None
    db.commit()
    cache.invalidate("feed:")
    return p


def set_status(db: Session, seller: SellerProfile, product_id, status: str) -> Product:
    p = get_owned(db, seller, product_id)
    if p.status in (ProductStatus.REJECTED, ProductStatus.PENDING_REVIEW) and status == "active":
        raise AppError("This listing is awaiting moderation", code="moderation")
    p.status = ProductStatus(status)
    if status == "active" and not p.published_at:
        p.published_at = utcnow()
    db.commit()
    cache.invalidate("feed:")
    return p


def delete_product(db: Session, seller: SellerProfile, product_id) -> None:
    p = get_owned(db, seller, product_id)
    p.deleted_at = utcnow()
    p.status = ProductStatus.INACTIVE
    db.commit()
    cache.invalidate("feed:")


def seller_image_count(db: Session, seller_id) -> int:
    """All listing photos, including those on soft-deleted products (their files still occupy storage)."""
    return db.scalar(select(func.count()).select_from(ProductImage).join(Product).where(
        Product.seller_id == seller_id)) or 0


def ensure_image_capacity(db: Session, seller: SellerProfile, count: int) -> None:
    used = seller_image_count(db, seller.id)
    limit = settings.max_images_per_seller
    if used + count > limit:
        raise AppError(f"Your photo limit is full ({used}/{limit}). Delete photos or listings to free space.",
                       code="seller_image_limit", details={"used": used, "limit": limit})


def listing_image_limit(db: Session, seller: SellerProfile) -> int:
    return PREMIUM_MAX_IMAGES if is_premium(db, seller.id) else FREE_MAX_IMAGES


def ensure_listing_image_capacity(db: Session, seller: SellerProfile, product_id, count: int) -> None:
    p = get_owned(db, seller, product_id)
    premium = is_premium(db, seller.id)
    limit = PREMIUM_MAX_IMAGES if premium else FREE_MAX_IMAGES
    if len(p.images) + count > limit:
        message = (f"A listing can have at most {PREMIUM_MAX_IMAGES} photos" if premium else
                   f"Free sellers can add up to {FREE_MAX_IMAGES} photos per listing. Upgrade to Premium for up to "
                   f"{PREMIUM_MAX_IMAGES}.")
        raise AppError(message, code="too_many_images",
                       details={"limit": limit, "premium": premium, "used": len(p.images)})


def add_images(db: Session, seller: SellerProfile, product_id, stored: list) -> Product:
    ensure_listing_image_capacity(db, seller, product_id, len(stored))
    p = get_owned(db, seller, product_id)
    ensure_image_capacity(db, seller, len(stored))
    start = len(p.images)
    for i, s in enumerate(stored):
        p.images.append(ProductImage(url=s.url, thumb_url=s.thumb_url, storage_key=s.key, width=s.width,
                                     height=s.height, position=start + i, created_at=utcnow()))
    db.commit()
    cache.invalidate("feed:")
    return p


def purge_deleted_listings(db: Session, retention_days: int | None = None) -> dict:
    """Hard-delete listings that have been soft-deleted past the retention window and remove their files."""
    days = settings.deleted_listing_retention_days if retention_days is None else retention_days
    cutoff = utcnow() - timedelta(days=days)
    products = db.scalars(select(Product).where(
        Product.deleted_at.isnot(None), Product.deleted_at < cutoff)).all()
    images = 0
    for p in products:
        for img in list(p.images):
            delete_stored_image(img.storage_key)
            images += 1
        db.delete(p)
    if products:
        db.commit()
        cache.invalidate("feed:")
    return {"products": len(products), "images": images}


def delete_image(db: Session, seller: SellerProfile, product_id, image_id) -> Product:
    p = get_owned(db, seller, product_id)
    img = next((i for i in p.images if i.id == image_id), None)
    if not img:
        raise NotFound("Image not found")
    p.images.remove(img)
    for i, im in enumerate(p.images):
        im.position = i
    db.commit()
    return p


def reorder_images(db: Session, seller: SellerProfile, product_id, ids: list[uuid.UUID]) -> Product:
    p = get_owned(db, seller, product_id)
    by_id = {i.id: i for i in p.images}
    if set(ids) != set(by_id):
        raise AppError("Provide every image id exactly once")
    for pos, iid in enumerate(ids):
        by_id[iid].position = pos
    db.commit()
    db.refresh(p)
    return p


def get_public(db: Session, slug: str) -> Product:
    p = db.scalars(base_query().where(Product.slug == slug, Product.deleted_at.is_(None))).first()
    if not p or p.status not in (ProductStatus.ACTIVE, ProductStatus.SOLD) or p.seller.is_suspended:
        raise NotFound("This listing is no longer available")
    return p


def record_view(db: Session, p: Product, user_id, ip: str, ua: str) -> None:
    viewer = str(user_id) if user_id else hashlib.sha256(f"{ip}|{ua}".encode()).hexdigest()[:32]
    since = utcnow() - timedelta(hours=24)
    seen = db.scalar(select(func.count()).select_from(ProductView).where(
        ProductView.product_id == p.id, ProductView.viewer_key == viewer, ProductView.created_at > since))
    if seen:
        return
    db.add(ProductView(product_id=p.id, seller_id=p.seller_id, viewer_key=viewer, created_at=utcnow()))
    db.execute(update(Product).where(Product.id == p.id).values(views_count=Product.views_count + 1))
    db.commit()


def toggle_favourite(db: Session, user_id, product_id, on: bool) -> bool:
    p = db.get(Product, product_id)
    if not p or p.deleted_at:
        raise NotFound("Listing not found")
    existing = db.scalars(select(Favourite).where(Favourite.user_id == user_id, Favourite.product_id == product_id)).first()
    if on and not existing:
        db.add(Favourite(user_id=user_id, product_id=product_id, created_at=utcnow()))
        db.execute(update(Product).where(Product.id == product_id).values(favourites_count=Product.favourites_count + 1))
    elif not on and existing:
        db.delete(existing)
        db.execute(update(Product).where(Product.id == product_id).values(
            favourites_count=func.greatest(Product.favourites_count - 1, 0)))
    db.commit()
    return on


def brands_for(db: Session, category_slug: str | None) -> list[str]:
    stmt = select(Product.brand, func.count()).where(public_filter(), Product.brand.isnot(None), Product.brand != "")
    if category_slug:
        cat = db.scalars(select(Category).where(Category.slug == category_slug)).first()
        if cat:
            ids = descendant_ids(db, cat.id)
            stmt = stmt.where(or_(Product.category_id.in_(ids), Product.subcategory_id.in_(ids)))
    rows = db.execute(stmt.group_by(Product.brand).order_by(desc(func.count())).limit(30)).all()
    return [r[0] for r in rows]


def similar(db: Session, p: Product, limit=8) -> list[Product]:
    return db.scalars(base_query().where(public_filter(), Product.id != p.id,
                                         Product.category_id == p.category_id)
                      .order_by(func.abs(Product.price - p.price)).limit(limit)).unique().all()

