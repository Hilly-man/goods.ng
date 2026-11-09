import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.deps import DB, CurrentSeller, CurrentUser
from app.modules.promotions import service
from app.modules.promotions.packages import get_packages

router = APIRouter(tags=["promotions"])


@router.get("/promotions/packages")
def packages(db: DB):
    """One-off packages a seller can buy for a single listing (no subscription)."""
    return [{**p, "price": f"{p['price']:.2f}"} for p in get_packages(db)]


class PromoteIn(BaseModel):
    product_id: uuid.UUID
    package_code: str = Field(min_length=2, max_length=30)


@router.post("/promotions", status_code=201)
def promote(data: PromoteIn, seller: CurrentSeller, user: CurrentUser, db: DB):
    return service.create(db, seller, user, data.product_id, data.package_code)
