import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.enums import ProductCondition, ProductStatus, VerificationLevel
from app.modules.common import MoneyStr, Schema

NG_STATES = [
    "Abia", "Abuja", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River",
    "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi",
    "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto",
    "Taraba", "Yobe", "Zamfara",
]


class DeliveryOption(BaseModel):
    type: Literal["pickup", "seller_delivery", "courier"]
    label: str = Field(max_length=80)
    fee: Decimal = Field(ge=0, le=1_000_000, decimal_places=2)
    eta_days: int = Field(1, ge=0, le=60)


class ProductIn(BaseModel):
    title: str = Field(min_length=5, max_length=140)
    description: str = Field(min_length=20, max_length=8000)
    category_id: uuid.UUID
    brand: str | None = Field(None, max_length=80)
    model: str | None = Field(None, max_length=80)
    condition: ProductCondition
    price: Decimal = Field(gt=0, le=Decimal("10000000000"), decimal_places=2)
    negotiable: bool = True
    quantity: int = Field(1, ge=0, le=100_000)
    state: str
    city: str = Field(min_length=2, max_length=80)
    delivery_options: list[DeliveryOption] = Field(default_factory=lambda: [
        DeliveryOption(type="pickup", label="Pickup from seller", fee=Decimal("0"), eta_days=0)
    ], max_length=5)
    protected_checkout_enabled: bool = True
    bnpl_enabled: bool = False

    @field_validator("state")
    @classmethod
    def _state(cls, v):
        if v not in NG_STATES:
            raise ValueError("Select a valid Nigerian state")
        return v

    @field_validator("delivery_options")
    @classmethod
    def _opts(cls, v):
        if not v:
            raise ValueError("At least one delivery option is required")
        return v


class ProductUpdate(BaseModel):
    title: str | None = Field(None, min_length=5, max_length=140)
    description: str | None = Field(None, min_length=20, max_length=8000)
    category_id: uuid.UUID | None = None
    brand: str | None = Field(None, max_length=80)
    model: str | None = Field(None, max_length=80)
    condition: ProductCondition | None = None
    price: Decimal | None = Field(None, gt=0, le=Decimal("10000000000"), decimal_places=2)
    negotiable: bool | None = None
    quantity: int | None = Field(None, ge=0, le=100_000)
    state: str | None = None
    city: str | None = Field(None, min_length=2, max_length=80)
    delivery_options: list[DeliveryOption] | None = Field(None, min_length=1, max_length=5)
    protected_checkout_enabled: bool | None = None
    bnpl_enabled: bool | None = None

    @field_validator("state")
    @classmethod
    def _state(cls, v):
        if v is not None and v not in NG_STATES:
            raise ValueError("Select a valid Nigerian state")
        return v


class StatusIn(BaseModel):
    status: Literal["active", "inactive", "sold"]


class ImageOut(Schema):
    id: uuid.UUID
    url: str
    thumb_url: str
    width: int
    height: int
    position: int


class SellerCard(BaseModel):
    id: uuid.UUID
    store_name: str
    slug: str
    logo_url: str | None
    verification_level: VerificationLevel
    is_premium: bool
    rating_avg: MoneyStr
    rating_count: int
    state: str | None
    city: str | None
    member_since: datetime
    completed_sales: int = 0
    whatsapp_available: bool = False
    phone_available: bool = False


class CategoryRef(BaseModel):
    id: uuid.UUID
    name: str
    slug: str


class ProductCard(BaseModel):
    id: uuid.UUID
    slug: str
    title: str
    price: MoneyStr
    currency: str
    negotiable: bool
    condition: ProductCondition
    state: str
    city: str
    thumb_url: str | None
    image_count: int
    is_featured: bool
    promoted_tier: str | None = None
    created_at: datetime
    seller: SellerCard
    category: CategoryRef
    protected_checkout_enabled: bool
    bnpl_enabled: bool
    is_favourite: bool = False
    sponsored: bool = False  # paid placement — the UI must label it "Sponsored"
    image_width: int | None = None
    image_height: int | None = None
    snippet: str | None = None


class ProductDetail(ProductCard):
    description: str
    brand: str | None
    model: str | None
    quantity: int
    status: ProductStatus
    images: list[ImageOut]
    delivery_options: list[dict]
    views_count: int
    favourites_count: int
    published_at: datetime | None
    updated_at: datetime
    subcategory: CategoryRef | None = None
    category_path: list[CategoryRef] = []


class SellerProductRow(ProductCard):
    status: ProductStatus
    quantity: int
    views_count: int
    enquiries_count: int
    contact_clicks: int
    favourites_count: int
    rejection_reason: str | None
    promoted_until: datetime | None = None


class SellerProductDetail(ProductDetail):
    """Owner view of a listing, including private performance stats."""

    enquiries_count: int
    contact_clicks: int
    rejection_reason: str | None
    is_featured_until: datetime | None = None
