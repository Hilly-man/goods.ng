from decimal import Decimal

from tests.conftest import simulate_payment


def test_cannot_self_grant_premium_features(make_seller):
    s = make_seller()
    r = s.patch("/sellers/me", {"whatsapp_number": "08031234567", "whatsapp_enabled": True})
    assert r.status_code == 403 and r.json()["error"]["code"] == "premium_required"
    # Arbitrary client fields like is_premium are ignored
    r = s.patch("/sellers/me", {"is_premium": True, "description": "hello"})
    assert r.status_code == 200 and r.json()["is_premium"] is False


def test_direct_contact_blocked_for_standard_seller(client, make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    r = client.post(f"/api/v1/sellers/{s.seller['id']}/contact",
                    json={"channel": "whatsapp", "product_id": p["id"], "acknowledged_warning": True})
    assert r.status_code == 403 and r.json()["error"]["code"] == "direct_contact_unavailable"


def _subscribe(s, plan="premium_monthly"):
    r = s.post("/subscriptions", {"plan_code": plan})
    assert r.status_code == 201, r.text
    return r.json()


def test_subscription_payment_activates_premium(client, make_seller, make_product):
    s = make_seller()
    sub = _subscribe(s)
    assert sub["amount"] == "15000.00"
    assert s.get("/sellers/me").json()["is_premium"] is False  # not before verified payment
    simulate_payment(s, sub["payment_reference"])
    me = s.get("/sellers/me").json()
    assert me["is_premium"] is True and me["subscription"]["plan_code"] == "premium_monthly"

    s.patch("/sellers/me", {"whatsapp_number": "08031234567", "whatsapp_enabled": True})
    p = make_product(s)
    # warning acknowledgement required
    r = client.post(f"/api/v1/sellers/{s.seller['id']}/contact", json={"channel": "whatsapp", "product_id": p["id"]})
    assert r.json()["error"]["code"] == "warning_not_acknowledged"
    r = client.post(f"/api/v1/sellers/{s.seller['id']}/contact",
                    json={"channel": "whatsapp", "product_id": p["id"], "acknowledged_warning": True})
    assert r.status_code == 200
    assert r.json()["link"].startswith("https://wa.me/2348031234567?text=")
    assert "Goods.ng" in r.json()["warning"]
    assert s.get(f"/seller/products/{p['id']}").json()["contact_clicks"] == 1


def test_underpaid_subscription_does_not_activate(make_seller):
    s = make_seller()
    sub = _subscribe(s)
    res = simulate_payment(s, sub["payment_reference"], paid_amount=Decimal("100.00"))
    assert res["payment_status"] == "failed"
    assert s.get("/sellers/me").json()["is_premium"] is False


def test_forged_webhook_rejected(client, make_seller):
    s = make_seller()
    sub = _subscribe(s)
    import json

    body = json.dumps({"id": "evt_forged", "event": "charge.success",
                       "data": {"reference": sub["payment_reference"]}}).encode()
    r = client.post("/api/v1/payments/webhooks/mock/webhook", content=body, headers={"x-mock-signature": "deadbeef"})
    assert r.status_code == 403
    assert s.get("/sellers/me").json()["is_premium"] is False


def test_featured_quota_enforced(make_seller, make_product):
    s = make_seller()
    simulate_payment(s, _subscribe(s)["payment_reference"])
    products = [make_product(s, title=f"Listing number {i} phone") for i in range(4)]
    for p in products[:3]:
        assert s.post("/subscriptions/feature-listing", {"product_id": p["id"], "days": 7}).status_code == 200
    r = s.post("/subscriptions/feature-listing", {"product_id": products[3]["id"], "days": 7})
    assert r.status_code == 400 and r.json()["error"]["code"] == "quota_exhausted"


def test_premium_analytics_locked_for_standard(make_seller):
    s = make_seller()
    a = s.get("/sellers/me/analytics").json()
    assert a["premium"] is False and "top_products" in a["locked"]
