"""Off-platform ads: product feeds, tracking IDs, consent-gated server events, and attribution."""

import uuid
import xml.etree.ElementTree as ET

import httpx

from app.core.cache import cache
from app.core.config import settings
from app.models import Order
from app.modules.marketing import service as mk
from tests.conftest import ADDRESS, simulate_payment
from tests.test_ads import DESC, _listing, _premium

G = "{http://base.google.com/ns/1.0}"


def _enable(admin, **extra):
    body = {"marketing": {"feed_enabled": True, "feed_excluded_categories": [], **extra}}
    r = admin.put("/admin/settings", body)
    assert r.status_code == 200, r.text
    cache.invalidate("feed:")
    return r.json()


def _feed_ids(client, path="/api/v1/feeds/google.xml", **params):
    r = client.get(path, params=params)
    return r, ({i.findtext(f"{G}id") for i in ET.fromstring(r.text).iter("item")} if r.status_code == 200 and path.endswith("xml") else None)


def test_feed_is_off_until_enabled_then_lists_only_quality_premium_listings(client, db, make_admin, make_seller, make_product):
    admin = make_admin(super_admin=True)
    _enable(admin, feed_enabled=False)
    assert client.get("/api/v1/feeds/google.xml").status_code == 404

    good = _listing(_premium(make_seller(), db), make_product, title="Feedable phone with photos")
    weak = _listing(_premium(make_seller(), db), make_product, photos=1, title="Feed phone one photo")
    std = _listing(make_seller(), make_product, title="Feed phone standard seller")
    _enable(admin)
    r, ids = _feed_ids(client)
    assert r.status_code == 200 and good["id"] in ids and weak["id"] not in ids and std["id"] not in ids
    item = next(i for i in ET.fromstring(r.text).iter("item") if i.findtext(f"{G}id") == good["id"])
    assert item.findtext(f"{G}price").endswith(" NGN")
    assert item.findtext(f"{G}condition") == "new"
    assert item.findtext(f"{G}image_link").startswith("http")
    assert "utm_source=google" in item.findtext("link") and "utm_campaign=premium_feed" in item.findtext("link")

    meta = client.get("/api/v1/feeds/meta.csv")
    assert meta.status_code == 200 and good["id"] in meta.text and "utm_source=facebook" in meta.text


def test_excluded_categories_are_left_out(client, db, make_admin, make_seller, make_product):
    admin = make_admin(super_admin=True)
    p = _listing(_premium(make_seller(), db), make_product)
    _enable(admin, feed_excluded_categories=["phones-tablets"])
    _, ids = _feed_ids(client)
    assert p["id"] not in ids


def test_feed_token_protects_feeds_when_configured(client, db, make_admin, monkeypatch):
    _enable(make_admin(super_admin=True))
    monkeypatch.setattr(settings, "feed_token", "s3cret-feed")
    assert client.get("/api/v1/feeds/google.xml").status_code == 404
    assert client.get("/api/v1/feeds/google.xml", params={"token": "s3cret-feed"}).status_code == 200


def test_tracking_ids_are_validated_and_public(client, make_admin):
    admin = make_admin(super_admin=True)
    bad = admin.put("/admin/settings", {"marketing": {"meta_pixel_id": "<script>"}})
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_tracking_id"
    _enable(admin, meta_pixel_id="123456789012345", ga4_id="G-ABC123XYZ", google_ads_id="AW-123456789")
    cache.invalidate("tracking:")
    cfg = client.get("/api/v1/tracking/config").json()
    assert cfg == {"meta_pixel_id": "123456789012345", "ga4_id": "G-ABC123XYZ", "google_ads_id": "AW-123456789",
                   "google_ads_purchase_label": None}
    s = admin.get("/admin/settings").json()["marketing"]
    assert "meta_capi_access_token" not in s and s["capi_configured"] is False  # the secret never leaves the env


def _checkout(buyer, product, consent):
    r = buyer.post("/checkout", {"product_id": product["id"], "quantity": 1, "delivery_option_index": 0,
                                 "address": ADDRESS, "marketing_consent": consent})
    assert r.status_code == 201, r.text
    simulate_payment(buyer, r.json()["payment_reference"])
    return r.json()["order_id"]


def test_server_purchase_events_only_for_consenting_buyers(db, make_admin, make_user, make_seller, make_product, monkeypatch):
    _enable(make_admin(super_admin=True), meta_pixel_id="123456789012345")
    seller = make_seller()
    yes = _checkout(make_user(), make_product(seller, description=DESC), True)
    no = _checkout(make_user(), make_product(seller, description=DESC), False)
    sent = {}

    def fake_post(url, params=None, json=None, timeout=None):
        sent.update(url=url, data=json["data"])
        return httpx.Response(200, json={"events_received": len(json["data"])}, request=httpx.Request("POST", url))

    monkeypatch.setattr(mk.httpx, "post", fake_post)
    assert mk.send_capi_purchases(db) == {}  # no token configured → nothing sent
    monkeypatch.setattr(settings, "meta_capi_access_token", "test-token")
    out = mk.send_capi_purchases(db)
    ids = {e["event_id"] for e in sent["data"]}
    assert f"purchase-{yes}" in ids and f"purchase-{no}" not in ids and out["capi_sent"] >= 1
    ev = next(e for e in sent["data"] if e["event_id"] == f"purchase-{yes}")
    assert len(ev["user_data"]["em"][0]) == 64 and "@" not in ev["user_data"]["em"][0]  # hashed, never raw
    db.expire_all()
    assert db.get(Order, uuid.UUID(yes)).capi_sent_at is not None
    sent.clear()
    mk.send_capi_purchases(db)
    assert f"purchase-{yes}" not in {e["event_id"] for e in sent.get("data", [])}  # sent once


def test_from_ads_attribution_in_seller_summary(client, db, make_user, make_seller, make_product):
    seller = _premium(make_seller(), db)
    p = _listing(seller, make_product)
    buyer = make_user()
    r = buyer.post("/recommendations/signals", {"kind": "landing", "source": "google", "product_slug": p["slug"],
                                                "campaign": "premium_feed"})
    assert r.json() == {"recorded": True}
    _checkout(buyer, p, True)
    s = seller.get("/seller/ads/summary").json()["from_ads"]
    assert s["visits"] == 1 and s["orders"] == 1
