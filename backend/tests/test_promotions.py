from tests.conftest import simulate_payment


def test_packages_are_public(client):
    r = client.get("/api/v1/promotions/packages")
    assert r.status_code == 200
    packages = {p["code"]: p for p in r.json()}
    assert {"top_7", "top_30", "premium_28"} <= set(packages)
    assert packages["top_7"]["price"] == "3099.00"
    assert packages["top_30"]["days"] == 30
    assert packages["premium_28"]["tier"] == "premium"
    assert packages["premium_28"]["price"] == "31999.00"


def test_single_listing_promotion_without_subscription(make_seller, make_product):
    """The core promise: one listing, one payment, no account-level plan."""
    s = make_seller()
    p = make_product(s)
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "top_7"})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["amount"] == "3099.00" and body["days"] == 7

    # Nothing unlocks before the provider confirms payment.
    row = s.get("/seller/products").json()["items"][0]
    assert row["is_featured"] is False and row["promoted_tier"] is None

    simulate_payment(s, body["payment_reference"])
    row = s.get("/seller/products").json()["items"][0]
    assert row["is_featured"] is True
    assert row["promoted_tier"] == "top"
    assert row["promoted_until"]


def _make_boost_eligible(s, product, db):
    from app.models import SellerProfile
    from app.models.enums import VerificationLevel
    from tests.conftest import png_bytes

    seller = db.get(SellerProfile, s.seller["id"])
    seller.verification_level = VerificationLevel.BUSINESS
    db.commit()
    files = [("files", (f"p{i}.png", png_bytes(), "image/png")) for i in range(3)]
    assert s.post(f"/seller/products/{product['id']}/images", files=files).status_code == 200


def test_premium_boost_sets_premium_tier(make_seller, make_product, db):
    s = make_seller()
    p = make_product(s, description="A long, detailed description with everything a serious buyer needs to know about this item. " * 2)
    _make_boost_eligible(s, p, db)
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "premium_28"})
    assert r.status_code == 201, r.text
    simulate_payment(s, r.json()["payment_reference"])
    row = s.get("/seller/products").json()["items"][0]
    assert row["promoted_tier"] == "premium"
    assert row["is_featured"] is True


def test_premium_boost_requires_quality_bar(make_seller, make_product):
    s = make_seller()  # unverified, no photos
    p = make_product(s)
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "premium_28"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "promotion_verification_required"


def test_cannot_promote_someone_elses_listing(make_seller, make_product):
    owner = make_seller()
    other = make_seller()
    p = make_product(owner)
    r = other.post("/promotions", {"product_id": p["id"], "package_code": "top_7"})
    assert r.status_code == 404


def test_duplicate_pending_payment_is_blocked(make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    assert s.post("/promotions", {"product_id": p["id"], "package_code": "top_7"}).status_code == 201
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "top_30"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "promotion_payment_pending"


def test_failed_payment_does_not_promote(make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "top_7"})
    assert r.status_code == 201
    simulate_payment(s, r.json()["payment_reference"], outcome="failed")
    row = s.get("/seller/products").json()["items"][0]
    assert row["is_featured"] is False and row["promoted_tier"] is None


def test_underpaid_promotion_does_not_activate(make_seller, make_product):
    from decimal import Decimal

    s = make_seller()
    p = make_product(s)
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "top_7"})
    res = simulate_payment(s, r.json()["payment_reference"], paid_amount=Decimal("100.00"))
    assert res["payment_status"] == "failed"
    assert s.get("/seller/products").json()["items"][0]["promoted_tier"] is None


def test_inactive_listing_cannot_be_promoted(make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    assert s.post(f"/seller/products/{p['id']}/status", {"status": "inactive"}).status_code == 200
    r = s.post("/promotions", {"product_id": p["id"], "package_code": "top_7"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "listing_not_live"
