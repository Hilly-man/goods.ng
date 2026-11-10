import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utcnow
from app.models.base import Base, SoftDelete, StrEnum, Timestamps, UUIDPk
from app.models.enums import ContactChannel, ProductCondition, ProductStatus, PromotionStatus


class Category(UUIDPk, Timestamps, Base):
    __tablename__ = "categories"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    icon: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent", order_by="Category.sort_order")


SEARCH_EXPR = (
    "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
    "setweight(to_tsvector('english', coalesce(brand, '') || ' ' || coalesce(model, '')), 'B') || "
    "setweight(to_tsvector('english', coalesce(description, '')), 'C')"
)


class Product(UUIDPk, Timestamps, SoftDelete, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
        Index("ix_products_search", "search_vector", postgresql_using="gin"),
        Index("ix_products_status_created", "status", "created_at"),
        Index("ix_products_category_status", "category_id", "status"),
        Index("ix_products_state_city", "state", "city"),
        Index("ix_products_price", "price"),
    )

    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("categories.id"))
    title: Mapped[str] = mapped_column(String(140))
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(String(80))
    model: Mapped[str | None] = mapped_column(String(80))
    condition: Mapped[ProductCondition] = mapped_column(StrEnum(ProductCondition))
    price: Mapped[Decimal]
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    negotiable: Mapped[bool] = mapped_column(Boolean, default=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    state: Mapped[str] = mapped_column(String(60))
    city: Mapped[str] = mapped_column(String(80))
    # [{"type": "pickup"|"seller_delivery"|"courier"|"arrange", "fee": "1500.00", "eta_days": 2, "label": "..."}]
    delivery_options: Mapped[list] = mapped_column(JSONB, default=list)
    protected_checkout_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    bnpl_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Seller acknowledgement of the Goods Flex terms (versioned, for audit).
    bnpl_terms_version: Mapped[str | None] = mapped_column(String(20))
    bnpl_terms_accepted_at: Mapped[datetime | None]
    status: Mapped[ProductStatus] = mapped_column(StrEnum(ProductStatus), default=ProductStatus.ACTIVE)
    rejection_reason: Mapped[str | None] = mapped_column(String(300))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    featured_until: Mapped[datetime | None]
    # Premium "bump to top": counts as fresh for ordering (without faking the posted date).
    bumped_at: Mapped[datetime | None] = mapped_column(index=True)
    # Paid per-listing promotion tier: "top" or "premium" while featured_until is in the future.
    promoted_tier: Mapped[str | None] = mapped_column(String(20))
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    enquiries_count: Mapped[int] = mapped_column(Integer, default=0)
    contact_clicks: Mapped[int] = mapped_column(Integer, default=0)
    favourites_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None]
    search_vector = mapped_column(TSVECTOR, Computed(SEARCH_EXPR, persisted=True))

    seller = relationship("SellerProfile")
    category: Mapped[Category] = relationship(foreign_keys=[category_id])
    subcategory: Mapped[Category | None] = relationship(foreign_keys=[subcategory_id])
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product", order_by="ProductImage.position", cascade="all, delete-orphan"
    )


class ProductImage(UUIDPk, Base):
    __tablename__ = "product_images"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(String(500))
    thumb_url: Mapped[str] = mapped_column(String(500))
    storage_key: Mapped[str] = mapped_column(String(500))
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    product: Mapped[Product] = relationship(back_populates="images")


class Favourite(UUIDPk, Base):
    __tablename__ = "favourites"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ContactEvent(UUIDPk, Base):
    """Analytics record whenever a buyer initiates direct contact (WhatsApp / call / chat)."""

    __tablename__ = "contact_events"
    __table_args__ = (Index("ix_contact_events_seller_created", "seller_id", "created_at"),)

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL")
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller_profiles.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    channel: Mapped[ContactChannel] = mapped_column(StrEnum(ContactChannel))
    warning_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ProductView(UUIDPk, Base):
    __tablename__ = "product_views"
    __table_args__ = (Index("ix_product_views_product_created", "product_id", "created_at"),)

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    viewer_key: Mapped[str] = mapped_column(String(64))  # user id or hashed ip+ua
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Promotion(UUIDPk, Timestamps, Base):
    __tablename__ = "promotions"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE")
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seller_profiles.id"))
    kind: Mapped[str] = mapped_column(String(30), default="featured")
    starts_at: Mapped[datetime]
    ends_at: Mapped[datetime]
    status: Mapped[PromotionStatus] = mapped_column(StrEnum(PromotionStatus), default=PromotionStatus.ACTIVE)
    source: Mapped[str] = mapped_column(String(30), default="subscription_quota")  # or paid / admin
    package_code: Mapped[str | None] = mapped_column(String(30))  # paid single-listing package
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("payments.id"))
    notes: Mapped[str | None] = mapped_column(Text)
