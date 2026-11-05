import uuid

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.deps import DB, client_ip, require_permission
from app.core.errors import AppError, Conflict, NotFound
from app.models import Category, Product, User
from app.models.enums import AdminPermission, ProductStatus
from app.modules.audit import audit

router = APIRouter(prefix="/categories", tags=["categories"])
CACHE_KEY = "categories:tree"


def category_tree(db: Session, include_inactive: bool = False) -> list[dict]:
    if not include_inactive:
        cached = cache.get_json(CACHE_KEY)
        if cached is not None:
            return cached
    q = select(Category).order_by(Category.sort_order, Category.name)
    if not include_inactive:
        q = q.where(Category.is_active.is_(True))
    cats = db.scalars(q).all()
    # Count each listing against its most specific category; parents then aggregate their children below.
    leaf = func.coalesce(Product.subcategory_id, Product.category_id)
    counts = dict(
        db.execute(
            select(leaf, func.count()).where(Product.status == ProductStatus.ACTIVE,
                                             Product.deleted_at.is_(None)).group_by(leaf)
        ).all()
    )
    nodes = {
        c.id: {"id": str(c.id), "name": c.name, "slug": c.slug, "icon": c.icon, "description": c.description,
               "sort_order": c.sort_order, "is_active": c.is_active, "parent_id": str(c.parent_id) if c.parent_id else None,
               "listing_count": counts.get(c.id, 0), "children": []}
        for c in cats
    }
    roots = []
    for c in cats:
        n = nodes[c.id]
        if c.parent_id and c.parent_id in nodes:
            nodes[c.parent_id]["children"].append(n)
            nodes[c.parent_id]["listing_count"] += n["listing_count"]
        elif not c.parent_id:
            roots.append(n)
    if not include_inactive:
        cache.set_json(CACHE_KEY, roots, ttl=300)
    return roots


def descendant_ids(db: Session, category_id: uuid.UUID) -> list[uuid.UUID]:
    cte = select(Category.id).where(Category.id == category_id).cte(recursive=True)
    cte = cte.union_all(select(Category.id).where(Category.parent_id == cte.c.id))
    return list(db.scalars(select(cte.c.id)).all())


@router.get("")
def list_categories(db: DB):
    return category_tree(db)


@router.get("/{slug}")
def get_category(slug: str, db: DB):
    c = db.scalars(select(Category).where(Category.slug == slug, Category.is_active.is_(True))).first()
    if not c:
        raise NotFound("Category not found")
    parent = db.get(Category, c.parent_id) if c.parent_id else None
    children = [
        {"id": str(x.id), "name": x.name, "slug": x.slug, "icon": x.icon}
        for x in c.children if x.is_active
    ]
    return {"id": str(c.id), "name": c.name, "slug": c.slug, "icon": c.icon, "description": c.description,
            "parent": {"name": parent.name, "slug": parent.slug} if parent else None, "children": children}


# ---------------- admin ----------------
class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    parent_id: uuid.UUID | None = None
    icon: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=300)
    sort_order: int = 0
    is_active: bool = True


class ReorderIn(BaseModel):
    ids: list[uuid.UUID]


perm = Depends(require_permission(AdminPermission.CATEGORIES_MANAGE))


@router.get("/admin/all")
def admin_list(db: DB, admin: User = perm):
    return category_tree(db, include_inactive=True)


@router.post("/admin", status_code=201)
def create_category(data: CategoryIn, request: Request, db: DB, admin: User = perm):
    if data.parent_id and not db.get(Category, data.parent_id):
        raise AppError("Parent category not found")
    slug = slugify(data.name)
    if db.scalars(select(Category).where(Category.slug == slug)).first():
        raise Conflict("A category with this name already exists")
    c = Category(**data.model_dump(), slug=slug)
    db.add(c)
    db.flush()
    audit(db, admin, "category.create", "category", c.id, data.model_dump(mode="json"), client_ip(request))
    db.commit()
    cache.invalidate("categories:")
    return {"id": str(c.id), "slug": c.slug}


@router.patch("/admin/{category_id}")
def update_category(category_id: uuid.UUID, data: CategoryIn, request: Request, db: DB, admin: User = perm):
    c = db.get(Category, category_id)
    if not c:
        raise NotFound("Category not found")
    if data.parent_id == c.id or (data.parent_id and data.parent_id in descendant_ids(db, c.id)):
        raise AppError("A category cannot be its own ancestor")
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    audit(db, admin, "category.update", "category", c.id, data.model_dump(mode="json"), client_ip(request))
    db.commit()
    cache.invalidate("categories:")
    return {"id": str(c.id), "slug": c.slug}


@router.post("/admin/reorder")
def reorder(data: ReorderIn, request: Request, db: DB, admin: User = perm):
    for i, cid in enumerate(data.ids):
        c = db.get(Category, cid)
        if c:
            c.sort_order = i
    audit(db, admin, "category.reorder", "category", None, {"ids": [str(i) for i in data.ids]}, client_ip(request))
    db.commit()
    cache.invalidate("categories:")
    return {"ok": True}
