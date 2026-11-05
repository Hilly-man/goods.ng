import uuid
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated, Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, PlainSerializer
from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")

CENT = Decimal("0.01")


def money(v: Decimal | int | str) -> Decimal:
    return Decimal(v).quantize(CENT, rounding=ROUND_HALF_UP)


# Money is serialised as a string ("1500000.00") so clients never round-trip through floats.
MoneyStr = Annotated[Decimal, PlainSerializer(lambda v: f"{v:.2f}", return_type=str)]


class Schema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class PageParams:
    def __init__(self, page: int = Query(1, ge=1, le=10_000), page_size: int = Query(24, ge=1, le=100)):
        self.page = page
        self.page_size = page_size


def paginate(db: Session, stmt, params: PageParams, mapper=None) -> dict:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)).unique().all()
    items = [mapper(r) for r in rows] if mapper else rows
    return {
        "items": items,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "pages": (total + params.page_size - 1) // params.page_size,
    }


class Msg(BaseModel):
    message: str


class IdOut(Schema):
    id: uuid.UUID


__all__ = ["Schema", "Page", "PageParams", "paginate", "money", "MoneyStr", "Msg", "IdOut", "datetime"]
