"""Recommended for you — personalised listings from first-party interest signals.

Signals:
* search  — a query typed into Goods.ng search
* view    — a listing the visitor opened
* landing — the visitor arrived from an external site (Google, Bing, Facebook, Instagram, TikTok, X, WhatsApp…).
            We only store what that click itself carried to us: the referring site, the ad/UTM keyword or
            campaign, and the page they landed on. Nobody can read a person's search or social history on
            another site, and we don't try to.

Visitors are identified by account when signed in, otherwise by a random first-party id the browser keeps
(`X-Anon-Id`). Anonymous history is merged into the account on sign-in. Users can clear it at any time, and
the worker purges anything older than 90 days.
"""

import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Literal

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy import case, delete, desc, func, literal, or_, select, update
from sqlalchemy.orm import Session

from app.core.cache import check_rate_limit
from app.core.deps import DB, OptionalUser, client_ip
from app.core.security import clean_text
from app.core.time import utcnow
from app.models import Category, InterestSignal, Product, User
from app.modules.products.service import base_query, build_tsquery, home_feed, public_filter, to_cards

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

Source = Literal["goods", "google", "bing", "yahoo", "duckduckgo", "facebook", "instagram", "tiktok", "x",
                 "whatsapp", "youtube", "other"]
SOURCE_LABEL = {"google": "Google", "bing": "Bing", "yahoo": "Yahoo", "duckduckgo": "DuckDuckGo",
                "facebook": "Facebook", "instagram": "Instagram", "tiktok": "TikTok", "x": "X",
                "whatsapp": "WhatsApp", "youtube": "YouTube", "other": "another site"}
SEARCH_ENGINES = {"google", "bing", "yahoo", "duckduckgo"}
KIND_WEIGHT = {"search": 3.0, "landing": 3.0, "view": 1.0}
RETENTION_DAYS = 90
HISTORY_LIMIT = 60
HALF_LIFE_DAYS = 7


class SignalIn(BaseModel):
    kind: Literal["search", "view", "landing"]
    source: Source = "goods"
    query: str | None = Field(None, max_length=120)
    campaign: str | None = Field(None, max_length=120)
    product_slug: str | None = Field(None, max_length=200)
    category_slug: str | None = Field(None, max_length=120)


def _anon(anon_id: str | None) -> str | None:
    """Accept only a well-formed UUID so the header can't be used to stuff arbitrary keys."""
    if not anon_id:
        return None
    try:
        return str(uuid.UUID(anon_id))
    except ValueError:
        return None


def _owner(user: User | None, anon: str | None):
    if user:
        return InterestSignal.user_id == user.id
    if anon:
        return InterestSignal.anon_id == anon
    return None


def _merge_anon(db: Session, user: User | None, anon: str | None) -> None:
    if user and anon:
        db.execute(update(InterestSignal).where(InterestSignal.anon_id == anon, InterestSignal.user_id.is_(None))
                   .values(user_id=user.id, anon_id=None))


@router.post("/signals", status_code=202)
def record_signal(data: SignalIn, request: Request, db: DB, user: OptionalUser,
                  x_anon_id: str | None = Header(None)):
    anon = _anon(x_anon_id)
    if not user and not anon:
        return {"recorded": False}
    check_rate_limit(f"sig:{user.id if user else anon}:{client_ip(request)}", 60, 60)
    query = clean_text(data.query)[:120].strip().lower() if data.query else None
    product_id = category_id = None
    if data.product_slug:
        p = db.scalars(select(Product).where(Product.slug == data.product_slug)).first()
        if p:
            product_id, category_id = p.id, p.subcategory_id or p.category_id
    if not category_id and data.category_slug:
        category_id = db.scalar(select(Category.id).where(Category.slug == data.category_slug))
    if not (query or product_id or category_id):
        return {"recorded": False}
    owner = _owner(user, anon)
    # Collapse repeats: the same search/view within 10 minutes is one signal.
    dup = db.scalar(select(InterestSignal.id).where(
        owner, InterestSignal.kind == data.kind,
        InterestSignal.query.is_(None) if query is None else InterestSignal.query == query,
        InterestSignal.product_id.is_(None) if product_id is None else InterestSignal.product_id == product_id,
        InterestSignal.created_at > utcnow() - timedelta(minutes=10)).limit(1))
    if dup:
        return {"recorded": False}
    db.add(InterestSignal(user_id=user.id if user else None, anon_id=None if user else anon, kind=data.kind,
                          source=data.source, query=query or None,
                          campaign=clean_text(data.campaign)[:120] if data.campaign else None,
                          category_id=category_id, product_id=product_id))
    db.commit()
    return {"recorded": True}


def _reason(s: InterestSignal, cat_names: dict) -> dict:
    where = SOURCE_LABEL.get(s.source)
    if s.query and s.kind == "landing" and s.source in SEARCH_ENGINES:
        text = f"Your {where} search “{s.query}”"
    elif s.query and s.kind == "landing" and where:
        text = f"From {where}: “{s.query}”"  # social/ad keyword, not something the person typed
    elif s.query:
        text = f"You searched “{s.query}”"
    elif s.kind == "landing" and where:
        text = f"You came from {where}" + (f" looking at {cat_names[s.category_id]}" if s.category_id in cat_names else "")
    elif s.category_id in cat_names:
        text = f"You viewed {cat_names[s.category_id]}"
    else:
        return {}
    return {"text": text, "source": s.source}


def recommend(db: Session, user: User | None, anon: str | None, limit: int = 12) -> dict:
    owner = _owner(user, anon)
    signals = db.scalars(select(InterestSignal).where(owner).order_by(desc(InterestSignal.created_at))
                         .limit(HISTORY_LIMIT)).all() if owner is not None else []
    if not signals:
        return {"personalised": False, "reasons": [], "items": home_feed(db)["trending"][:limit]}

    now = utcnow()
    query_w: dict[str, float] = defaultdict(float)
    cat_w: dict[uuid.UUID, float] = defaultdict(float)
    for s in signals:
        w = KIND_WEIGHT[s.kind] * 0.5 ** ((now - s.created_at).total_seconds() / 86400 / HALF_LIFE_DAYS)
        if s.query:
            query_w[s.query] += w
        if s.category_id:
            cat_w[s.category_id] += w
    top_q = sorted(query_w.items(), key=lambda kv: -kv[1])[:4]
    top_c = sorted(cat_w.items(), key=lambda kv: -kv[1])[:5]

    score = literal(0.0)
    match = []
    for q, w in top_q:
        if tsq := build_tsquery(q):
            cond = Product.search_vector.op("@@")(func.to_tsquery("english", tsq))
            score = score + case((cond, w * 2), else_=0.0)
            match.append(cond)
    for cid, w in top_c:
        cond = or_(Product.subcategory_id == cid, Product.category_id == cid)
        score = score + case((cond, w), else_=0.0)
        match.append(cond)
    seen = {s.product_id for s in signals if s.product_id}

    items = []
    if match:
        stmt = base_query().where(public_filter(), or_(*match))
        if seen:
            stmt = stmt.where(Product.id.not_in(seen))
        if user:
            stmt = stmt.where(~Product.seller.has(user_id=user.id))
        rows = db.scalars(stmt.order_by(desc(score), desc(Product.created_at)).limit(limit)).unique().all()
        items = [c.model_dump(mode="json") for c in to_cards(db, list(rows), user.id if user else None)]
    # Sponsored: 1 slot in every 5, only from the visitor's own top categories (relevant, labelled).
    if top_c and items:
        from app.modules.ads import service as ads

        cats = [cid for cid, _ in top_c]
        n_slots = max(1, len(items) // 5)
        promo = ads.pick(db, [or_(Product.subcategory_id.in_(cats), Product.category_id.in_(cats))],
                         exclude_ids=[i["id"] for i in items] + list(seen), n=n_slots)
        promo_cards = [c.model_dump(mode="json") | {"sponsored": True}
                       for c in to_cards(db, promo, user.id if user else None)]
        for slot, card in zip((1, 6), promo_cards, strict=False):
            items.insert(min(slot, len(items)), card)
        items = items[:limit]
    if len(items) < limit:  # top up with trending so the row is never sparse
        have = {i["id"] for i in items} | {str(x) for x in seen}
        items += [t for t in home_feed(db)["trending"] if t["id"] not in have][: limit - len(items)]

    cat_ids = {s.category_id for s in signals if s.category_id}
    cat_names = dict(db.execute(select(Category.id, Category.name).where(Category.id.in_(cat_ids))).all()) if cat_ids else {}
    reasons, used = [], set()
    for s in signals:  # newest first
        r = _reason(s, cat_names)
        if r and r["text"] not in used:
            used.add(r["text"])
            reasons.append(r)
        if len(reasons) == 3:
            break
    return {"personalised": True, "reasons": reasons, "items": items}


@router.get("/for-you")
def for_you(db: DB, user: OptionalUser, x_anon_id: str | None = Header(None)):
    anon = _anon(x_anon_id)
    _merge_anon(db, user, anon)
    db.commit()
    return recommend(db, user, anon)


@router.delete("/history")
def clear_history(db: DB, user: OptionalUser, x_anon_id: str | None = Header(None)):
    anon = _anon(x_anon_id)
    conds = []
    if user:
        conds.append(InterestSignal.user_id == user.id)
    if anon:
        conds.append(InterestSignal.anon_id == anon)
    n = db.execute(delete(InterestSignal).where(or_(*conds))).rowcount if conds else 0
    db.commit()
    return {"cleared": n}


def purge_old_signals(db: Session) -> dict:
    n = db.execute(delete(InterestSignal).where(
        InterestSignal.created_at < utcnow() - timedelta(days=RETENTION_DAYS))).rowcount
    db.commit()
    return {"purged": n} if n else {}
