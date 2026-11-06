"""Sponsored placements: item-page block, event beacons, seller bump + summary."""

import uuid
from typing import Literal

from fastapi import APIRouter, Header, Query, Request
from pydantic import BaseModel, Field

from app.core.cache import check_rate_limit
from app.core.deps import DB, CurrentSeller, OptionalUser, client_ip
from app.models import Product
from app.modules.ads import service
from app.modules.products import service as products
from app.modules.products.schemas import ProductCard

router = APIRouter(tags=["ads"])


@router.get("/products/{slug}/sponsored", response_model=list[ProductCard])
def item_sponsored(slug: str, db: DB, user: OptionalUser, limit: int = Query(4, ge=1, le=8)):
    """"More from trusted sellers" on an item page: same category, other sellers, quality-bar listings only."""
    p = products.get_public(db, slug)  # also works for sold items, where buyers most need an alternative
    rows = service.pick(db, [Product.category_id == p.category_id], exclude_ids=[p.id], exclude_sellers=[p.seller_id], n=limit)
    cards = products.to_cards(db, rows, user.id if user else None)
    for c in cards:
        c.sponsored = True
    return cards


class AdEventIn(BaseModel):
    kind: Literal["impression", "click"]
    placement: Literal["search", "category", "item", "for_you", "home"]
    product_id: uuid.UUID


class AdEventsIn(BaseModel):
    events: list[AdEventIn] = Field(max_length=50)
    anon_id: str | None = Field(None, max_length=64)


@router.post("/ads/events", status_code=202)
def ad_events(data: AdEventsIn, request: Request, db: DB, user: OptionalUser, x_anon_id: str | None = Header(None)):
    anon = x_anon_id or data.anon_id
    try:
        anon = str(uuid.UUID(anon)) if anon else None
    except ValueError:
        anon = None
    viewer = f"u:{user.id}" if user else (f"a:{anon}" if anon else f"ip:{client_ip(request)}")
    check_rate_limit(f"adevents:{viewer}", 120, 60)
    return {"recorded": service.record(db, [e.model_dump() for e in data.events], viewer)}


@router.get("/seller/ads/summary")
def ads_summary(seller: CurrentSeller, db: DB, days: int = Query(30, ge=1, le=90)):
    return service.seller_summary(db, seller, days)


@router.post("/seller/products/{product_id}/bump")
def bump(product_id: uuid.UUID, seller: CurrentSeller, db: DB):
    p = service.bump(db, seller, product_id)
    return {"bumped_at": p.bumped_at, "quota": service.bump_quota(db, seller)}
