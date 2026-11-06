import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from pydantic import BaseModel

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentSeller, CurrentUser, OptionalUser, client_ip
from app.core.errors import AppError
from app.integrations.storage import store_image
from app.models import Favourite, Product
from app.models.enums import ProductCondition
from app.modules.ads import service as ads
from app.modules.common import Page, PageParams, paginate
from app.modules.locations import cities_by_state
from app.modules.products import service
from app.modules.products.schemas import (
    NG_STATES,
    ProductCard,
    ProductDetail,
    ProductIn,
    ProductUpdate,
    SellerProductDetail,
    SellerProductRow,
    StatusIn,
)

router = APIRouter(tags=["products"])


def owner_detail(db, p) -> SellerProductDetail:
    d = service.to_detail(db, p)
    return SellerProductDetail(**d.model_dump(), enquiries_count=p.enquiries_count, contact_clicks=p.contact_clicks,
                               rejection_reason=p.rejection_reason, is_featured_until=p.featured_until)


@router.get("/locations")
def locations(db: DB):
    """All states with their cities (single request, cached; small enough for slow networks)."""
    by_state = cities_by_state(db)
    return {"states": NG_STATES, "cities": {s: by_state.get(s, []) for s in NG_STATES}}


@router.get("/locations/{state}/cities")
def state_cities(state: str, db: DB):
    if state not in NG_STATES:
        raise AppError("Unknown state", status_code=404, code="not_found")
    return cities_by_state(db).get(state, [])


class SearchFilters:
    """Query parameters shared by listing search and facet counts."""

    def __init__(
        self,
        q: str | None = Query(None, max_length=100),
        category: str | None = None,
        state: str | None = None,
        city: str | None = None,
        min_price: Decimal | None = Query(None, ge=0),
        max_price: Decimal | None = Query(None, ge=0),
        condition: list[ProductCondition] = Query(default=[]),
        brand: str | None = None,
        verified: bool = False,
        premium: bool = False,
        negotiable: bool = False,
        bnpl: bool = False,
        protected: bool = False,
        with_photos: bool = False,
        posted_within: int | None = Query(None, ge=1, le=365),
        seller_id: uuid.UUID | None = None,
    ):
        if min_price is not None and max_price is not None and min_price > max_price:
            raise AppError("Minimum price cannot exceed maximum price")
        self.values = dict(q=q, category=category, state=state, city=city, min_price=min_price, max_price=max_price,
                           conditions=condition, brand=brand, verified_only=verified, premium_only=premium,
                           negotiable=negotiable, bnpl=bnpl, protected=protected, with_photos=with_photos,
                           posted_within=posted_within, seller_id=seller_id)


@router.get("/products", response_model=Page[ProductCard])
def search_products(
    db: DB,
    user: OptionalUser,
    filters: SearchFilters = Depends(),
    sort: str = Query("relevance", pattern="^(relevance|newest|price_asc|price_desc)$"),
    params: PageParams = Depends(),
):
    page = paginate(db, service.search(db, sort=sort, **filters.values), params)
    organic = page["items"]
    sponsored = []
    f = filters.values
    # Sponsored slots: only when ranking by relevance/newest, never when sorting by price, browsing one store,
    # or already filtering to Premium sellers. They always match the buyer's filters.
    if sort in ("relevance", "newest") and not f.get("seller_id") and not f.get("premium_only"):
        sponsored = ads.pick(db, service.filter_conditions(db, f))
        promoted = {p.id for p in sponsored}
        organic = [p for p in organic if p.id not in promoted]  # shown once, in its labelled slot
    blended = ads.blend(organic, sponsored, params.page_size) if sponsored else [(p, False) for p in organic]
    cards = service.to_cards(db, [p for p, _ in blended], user.id if user else None)
    for card, (_, is_sponsored) in zip(cards, blended, strict=True):
        card.sponsored = is_sponsored
    page["items"] = cards
    return page


@router.get("/products/facets")
def search_facets(db: DB, filters: SearchFilters = Depends()):
    """Counts for every filter option given the other active filters (drives the filter sidebar)."""
    from app.core.cache import cache

    key = "facets:" + "|".join(f"{k}={v}" for k, v in sorted(filters.values.items()) if v not in (None, False, "", []))
    return cache.get_or_compute(key, 60, lambda: service.facets(db, **filters.values))


@router.get("/products/feed/home")
def home_feed(db: DB):
    return service.home_feed(db)


@router.get("/products/brands")
def brands(db: DB, category: str | None = None):
    return service.brands_for(db, category)


@router.get("/products/{slug}", response_model=ProductDetail)
def product_detail(slug: str, request: Request, db: DB, user: OptionalUser):
    return service.to_detail(db, service.get_public(db, slug), user.id if user else None)


@router.post("/products/{slug}/view", status_code=204)
def product_view(slug: str, request: Request, db: DB, user: OptionalUser):
    """View beacon sent by the browser (SSR fetches must not count as views). Deduplicated per viewer per day."""
    p = service.get_public(db, slug)
    service.record_view(db, p, user.id if user else None, client_ip(request), request.headers.get("user-agent", ""))


@router.get("/products/{slug}/similar", response_model=list[ProductCard])
def product_similar(slug: str, db: DB, user: OptionalUser):
    p = service.get_public(db, slug)
    return service.to_cards(db, service.similar(db, p), user.id if user else None)


# ---------------- seller listing management ----------------
@router.get("/seller/products", response_model=Page[SellerProductRow])
def my_products(seller: CurrentSeller, db: DB, status: str | None = None, q: str | None = None,
                params: PageParams = Depends()):
    stmt = service.base_query().where(Product.seller_id == seller.id, Product.deleted_at.is_(None))
    if status:
        stmt = stmt.where(Product.status == status)
    if q:
        stmt = stmt.where(Product.title.ilike(f"%{q[:60]}%"))
    page = paginate(db, stmt.order_by(Product.created_at.desc()), params)
    page["items"] = service.to_cards(db, page["items"], cls=SellerProductRow)
    return page


@router.get("/seller/products/{product_id}", response_model=SellerProductDetail)
def my_product(product_id: uuid.UUID, seller: CurrentSeller, db: DB):
    return owner_detail(db, service.get_owned(db, seller, product_id))


@router.post("/seller/products", response_model=SellerProductDetail, status_code=201)
def create_product(data: ProductIn, seller: CurrentSeller, db: DB):
    check_rate_limit(f"listing:create:{seller.id}", 100, 86400)
    p = service.create_product(db, seller, data)
    return owner_detail(db, service.get_owned(db, seller, p.id))


@router.patch("/seller/products/{product_id}", response_model=SellerProductDetail)
def update_product(product_id: uuid.UUID, data: ProductUpdate, seller: CurrentSeller, db: DB):
    service.update_product(db, seller, product_id, data)
    return owner_detail(db, service.get_owned(db, seller, product_id))


@router.post("/seller/products/{product_id}/status", response_model=SellerProductDetail)
def change_status(product_id: uuid.UUID, data: StatusIn, seller: CurrentSeller, db: DB):
    service.set_status(db, seller, product_id, data.status)
    return owner_detail(db, service.get_owned(db, seller, product_id))


@router.delete("/seller/products/{product_id}", status_code=204)
def delete_product(product_id: uuid.UUID, seller: CurrentSeller, db: DB):
    service.delete_product(db, seller, product_id)


@router.post("/seller/products/{product_id}/images", response_model=SellerProductDetail)
async def upload_images(product_id: uuid.UUID, seller: CurrentSeller, db: DB, files: list[UploadFile] = File(...)):
    check_rate_limit(f"listing:images:{seller.id}", 200, 3600)
    service.get_owned(db, seller, product_id)  # authorise before doing any work
    if len(files) > service.MAX_IMAGES:
        raise AppError(f"Upload at most {service.MAX_IMAGES} photos at once")
    # Check before writing files, so rejected uploads don't consume storage.
    service.ensure_image_capacity(db, seller, len(files))
    stored = [store_image(await f.read(), f"products/{product_id}") for f in files]
    service.add_images(db, seller, product_id, stored)
    return owner_detail(db, service.get_owned(db, seller, product_id))


@router.delete("/seller/products/{product_id}/images/{image_id}", response_model=SellerProductDetail)
def remove_image(product_id: uuid.UUID, image_id: uuid.UUID, seller: CurrentSeller, db: DB):
    service.delete_image(db, seller, product_id, image_id)
    return owner_detail(db, service.get_owned(db, seller, product_id))


class ReorderIn(BaseModel):
    ids: list[uuid.UUID]


@router.put("/seller/products/{product_id}/images/order", response_model=SellerProductDetail)
def reorder_images(product_id: uuid.UUID, data: ReorderIn, seller: CurrentSeller, db: DB):
    service.reorder_images(db, seller, product_id, data.ids)
    return owner_detail(db, service.get_owned(db, seller, product_id))


# ---------------- favourites ----------------
@router.post("/products/{product_id}/favourite")
def favourite(product_id: uuid.UUID, user: CurrentUser, db: DB):
    from app.core.deps import ensure_customer

    ensure_customer(user)
    return {"favourite": service.toggle_favourite(db, user.id, product_id, True)}


@router.delete("/products/{product_id}/favourite")
def unfavourite(product_id: uuid.UUID, user: CurrentUser, db: DB):
    return {"favourite": service.toggle_favourite(db, user.id, product_id, False)}


@router.get("/users/me/favourites", response_model=Page[ProductCard])
def my_favourites(user: CurrentUser, db: DB, params: PageParams = Depends()):
    stmt = (service.base_query().join(Favourite, Favourite.product_id == Product.id)
            .where(Favourite.user_id == user.id, Product.deleted_at.is_(None)).order_by(Favourite.created_at.desc()))
    page = paginate(db, stmt, params)
    page["items"] = service.to_cards(db, page["items"], user.id)
    return page
