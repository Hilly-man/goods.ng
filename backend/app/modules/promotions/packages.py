"""One-off, per-listing promotion packages.

Sellers can buy visibility for a single listing without subscribing to an account-level Premium
plan. Prices live in code as safe defaults and can be overridden by admins through the
`promotion_packages` PlatformSetting (a JSON list using the same shape).
"""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import PlatformSetting

DEFAULT_PACKAGES: list[dict] = [
    {
        "code": "top_7",
        "name": "TOP promo",
        "tier": "top",
        "days": 7,
        "price": "3099.00",
        "tagline": "Featured for 7 days with priority in search, category and home.",
        "sort_order": 1,
    },
    {
        "code": "top_30",
        "name": "TOP promo",
        "tier": "top",
        "days": 30,
        "price": "9999.00",
        "tagline": "Featured for 30 days — better value per day.",
        "sort_order": 2,
    },
    {
        "code": "premium_28",
        "name": "Boost Premium",
        "tier": "premium",
        "days": 28,
        "price": "31999.00",
        "tagline": "Premium placement for 28 days: sponsored slots, daily top placement and a Premium badge.",
        "sort_order": 3,
    },
]


def _normalise(item: dict) -> dict | None:
    try:
        code = str(item["code"]).strip()[:30]
        name = str(item["name"]).strip()[:60]
        tier = str(item["tier"]).strip().lower()
        days = int(item["days"])
        price = Decimal(str(item["price"]))
        tagline = str(item.get("tagline", "")).strip()[:200]
        sort_order = int(item.get("sort_order", 99))
    except (KeyError, TypeError, ValueError, ArithmeticError):
        return None
    if not code or not name or tier not in ("top", "premium"):
        return None
    if not 1 <= days <= 365 or price <= 0:
        return None
    return {"code": code, "name": name, "tier": tier, "days": days, "price": price,
            "tagline": tagline, "sort_order": sort_order}


def get_packages(db: Session) -> list[dict]:
    row = db.get(PlatformSetting, "promotion_packages")
    raw = row.value if row and isinstance(row.value, list) and row.value else DEFAULT_PACKAGES
    out = [p for p in (_normalise(item) for item in raw if isinstance(item, dict)) if p]
    if not out:
        out = [p for p in (_normalise(item) for item in DEFAULT_PACKAGES) if p]
    return sorted(out, key=lambda p: p["sort_order"])


def get_package(db: Session, code: str) -> dict | None:
    return next((p for p in get_packages(db) if p["code"] == code), None)
