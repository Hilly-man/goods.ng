"""Advertising Premium listings on Google and Facebook/Instagram.

* Product feeds — Google Merchant Center (RSS 2.0 XML) and Meta Commerce Manager (CSV) read these on a
  schedule. Only Premium listings that pass the ads quality bar (ads/service.eligible: verified seller,
  3+ real photos, proper description) are included, minus any categories excluded in admin settings.
  Every link carries UTM tags so visits and sales are attributed (and feed Recommended-for-you).
* Tracking IDs (Meta Pixel, GA4, Google Ads) are public identifiers, editable in Admin › Platform settings.
  The browser only loads those scripts after the visitor accepts marketing cookies (NDPA).
* Meta Conversions API — server-side Purchase events, ONLY for orders whose buyer consented at checkout.
  The access token is a secret: environment variable META_CAPI_ACCESS_TOKEN, never stored in the database.
"""

import csv
import hashlib
import io
import logging
import re
from datetime import timedelta
from decimal import Decimal
from urllib.parse import urlencode
from xml.sax.saxutils import escape

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.time import utcnow
from app.models import Category, Order, PlatformSetting, Product, User
from app.models.enums import ProductCondition
from app.modules.ads.service import eligible
from app.modules.products.service import base_query

log = logging.getLogger("goodsng.marketing")

SETTING_KEY = "marketing"
DEFAULTS = {
    "feed_enabled": False,
    # Google Shopping doesn't take property; vehicles are restricted. Start with goods that sell well online.
    "feed_excluded_categories": ["property", "vehicles", "jobs", "services"],
    "meta_pixel_id": "", "ga4_id": "", "google_ads_id": "", "google_ads_purchase_label": "",
}
ID_RULES = {
    "meta_pixel_id": re.compile(r"^\d{10,20}$"),
    "ga4_id": re.compile(r"^G-[A-Z0-9]{4,15}$"),
    "google_ads_id": re.compile(r"^AW-\d{6,15}$"),
    "google_ads_purchase_label": re.compile(r"^[A-Za-z0-9_-]{4,40}$"),
}
CONDITION = {ProductCondition.BRAND_NEW: "new", ProductCondition.REFURBISHED: "refurbished",
             ProductCondition.FOREIGN_USED: "used", ProductCondition.NIGERIAN_USED: "used"}
MAX_FEED_ITEMS = 5000


def config(db: Session) -> dict:
    row = db.get(PlatformSetting, SETTING_KEY)
    return {**DEFAULTS, **(row.value if row else {})}


def public_tracking(db: Session) -> dict:
    """What the browser needs (all public identifiers) — no secrets."""
    c = config(db)
    return {k: c[k] or None for k in ("meta_pixel_id", "ga4_id", "google_ads_id", "google_ads_purchase_label")}


# ---------------- feeds ----------------

def _abs(url: str | None) -> str | None:
    if not url:
        return None
    return url if url.startswith("http") else f"{settings.frontend_url.rstrip('/')}{url}"


def _link(p: Product, source: str, medium: str) -> str:
    q = urlencode({"utm_source": source, "utm_medium": medium, "utm_campaign": "premium_feed", "utm_content": p.slug})
    return f"{settings.frontend_url.rstrip('/')}/item/{p.slug}?{q}"


def feed_products(db: Session) -> list[Product]:
    excluded = set(config(db)["feed_excluded_categories"] or [])
    stmt = base_query().where(eligible())
    if excluded:
        ids = select(Category.id).where(Category.slug.in_(excluded))
        stmt = stmt.where(and_(Product.category_id.not_in(ids),
                               or_(Product.subcategory_id.is_(None), Product.subcategory_id.not_in(ids))))
    return list(db.scalars(stmt.order_by(Product.created_at.desc()).limit(MAX_FEED_ITEMS)).unique().all())


def _plain(text: str, limit: int) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit]


def _row(p: Product, source: str, medium: str) -> dict:
    images = [_abs(i.url) for i in sorted(p.images, key=lambda i: i.position or 0)]
    return {
        "id": str(p.id),
        "title": _plain(p.title, 150),
        "description": _plain(p.description, 5000),
        "link": _link(p, source, medium),
        "image_link": images[0],
        "additional_image_link": images[1:11],
        "availability": "in stock" if p.quantity > 0 else "out of stock",
        "price": f"{Decimal(p.price):.2f} NGN",
        "condition": CONDITION.get(p.condition, "used"),
        "brand": _plain(p.brand or "", 70),
        "product_type": " > ".join(x for x in [p.category.name if p.category else "", p.subcategory.name if p.subcategory else ""] if x),
        "custom_label_0": p.category.slug if p.category else "",
    }


def google_xml(db: Session) -> str:
    items = []
    for p in feed_products(db):
        r = _row(p, "google", "shopping")
        extra = "".join(f"<g:additional_image_link>{escape(u)}</g:additional_image_link>" for u in r["additional_image_link"])
        brand = f"<g:brand>{escape(r['brand'])}</g:brand>" if r["brand"] else "<g:identifier_exists>no</g:identifier_exists>"
        items.append(
            "<item>"
            f"<g:id>{r['id']}</g:id><title>{escape(r['title'])}</title><description>{escape(r['description'])}</description>"
            f"<link>{escape(r['link'])}</link><g:image_link>{escape(r['image_link'])}</g:image_link>{extra}"
            f"<g:availability>{r['availability']}</g:availability><g:price>{r['price']}</g:price>"
            f"<g:condition>{r['condition']}</g:condition>{brand}"
            f"<g:product_type>{escape(r['product_type'])}</g:product_type><g:custom_label_0>{escape(r['custom_label_0'])}</g:custom_label_0>"
            "</item>"
        )
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0"><channel>'
            f"<title>Goods.ng</title><link>{escape(settings.frontend_url)}</link><description>Goods.ng marketplace listings</description>"
            + "".join(items) + "</channel></rss>")


def meta_csv(db: Session) -> str:
    buf = io.StringIO()
    cols = ["id", "title", "description", "availability", "condition", "price", "link", "image_link", "brand",
            "additional_image_link", "product_type"]
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for p in feed_products(db):
        r = _row(p, "facebook", "paid_social")
        r["additional_image_link"] = ",".join(r["additional_image_link"])
        w.writerow({k: r[k] for k in cols})
    return buf.getvalue()


# ---------------- Meta Conversions API (server-side purchases) ----------------

def _h(value: str | None) -> str | None:
    return hashlib.sha256(value.strip().lower().encode()).hexdigest() if value else None


def _phone_digits(phone: str | None) -> str | None:
    d = re.sub(r"\D", "", phone or "")
    return d or None


def send_capi_purchases(db: Session) -> dict:
    """Worker job: one Purchase event per consenting paid order (deduplicated with the browser via event_id)."""
    token, pixel = settings.meta_capi_access_token, config(db)["meta_pixel_id"]
    if not token or not pixel:
        return {}
    since = utcnow() - timedelta(days=7)
    orders = db.scalars(select(Order).where(Order.marketing_consent.is_(True), Order.paid_at.isnot(None),
                                            Order.paid_at >= since, Order.capi_sent_at.is_(None))
                        .with_for_update(skip_locked=True).limit(200)).all()
    if not orders:
        return {}
    events = []
    for o in orders:
        buyer = db.get(User, o.buyer_id)
        events.append({
            "event_name": "Purchase", "event_time": int(o.paid_at.timestamp()), "event_id": f"purchase-{o.id}",
            "action_source": "website", "event_source_url": f"{settings.frontend_url.rstrip('/')}/orders/{o.id}",
            "user_data": {k: v for k, v in {"em": [_h(buyer.email)] if buyer else None,
                                             "ph": [_h(_phone_digits(buyer.phone))] if buyer and buyer.phone else None,
                                             "external_id": [_h(str(o.buyer_id))]}.items() if v},
            "custom_data": {"currency": "NGN", "value": float(o.total), "content_type": "product",
                            "content_ids": [str(i.product_id) for i in o.items], "order_id": o.order_number},
        })
    try:
        r = httpx.post(f"https://graph.facebook.com/{settings.meta_graph_version}/{pixel}/events",
                       params={"access_token": token}, json={"data": events}, timeout=15)
        r.raise_for_status()
    except httpx.HTTPError as e:
        db.rollback()
        log.warning("meta_capi_failed", extra={"error": str(e)[:200]})
        return {"capi_failed": len(events)}
    now = utcnow()
    for o in orders:
        o.capi_sent_at = now
    db.commit()
    return {"capi_sent": len(events)}
