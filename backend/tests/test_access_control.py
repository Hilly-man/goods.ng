"""Access control: nobody can read or act on another user's records by changing an ID in the URL,
and the wrong party (buyer vs seller) can't perform the other side's actions."""

import uuid

import pytest
from fastapi.routing import APIRoute

from app.main import app
from tests.conftest import ADDRESS
from tests.test_flex import apply, flex_product, setup_flex

DENIED = {401, 403, 404}


def _no(resp, what):
    assert resp.status_code in DENIED, f"{what}: expected denial, got {resp.status_code} {resp.text[:200]}"


def test_outsider_cannot_touch_someone_elses_order_chat_offer_or_payment(paid_order, make_user, make_seller, make_product):
    buyer, seller, product, order = paid_order()
    outsider = make_user("Outsider")
    oid = order["id"]
    # order: read + every action
    _no(outsider.get(f"/orders/{oid}"), "read order")
    for action in ["accept", "decline", "dispatch", "delivery-update", "delivered", "confirm", "cancel", "retry-payment"]:
        _no(outsider.post(f"/orders/{oid}/{action}", {"reason": "x" * 12, "courier": "GIG", "tracking_number": "T1", "note": "Out for delivery today"}), f"order {action}")
    _no(outsider.post(f"/orders/{oid}/disputes", {"reason": "not_received", "description": "x" * 30}), "open dispute")
    # payment reference
    ref = buyer.get("/orders", params={"role": "buyer"}).json()
    pay_ref = order.get("payment_reference") or (ref["items"][0].get("payment_reference") if isinstance(ref, dict) and ref.get("items") else None)
    if pay_ref:
        _no(outsider.get(f"/payments/{pay_ref}"), "read payment")
        _no(outsider.post(f"/payments/{pay_ref}/verify", {}), "verify payment")

    # conversation + offer on a fresh listing
    p2 = make_product(seller, title="Second phone for chat test")
    conv = buyer.post("/conversations", {"product_id": p2["id"], "body": "Is it available?"}).json()["conversation_id"]
    _no(outsider.get(f"/conversations/{conv}"), "read conversation")
    _no(outsider.post(f"/conversations/{conv}/messages", {"body": "hi"}), "post into conversation")
    _no(outsider.post(f"/conversations/{conv}/archive", {}), "archive conversation")
    msgs = seller.get(f"/conversations/{conv}").json()["messages"]
    _no(outsider.post(f"/messages/{msgs[0]['id']}/report", {"reason": "spam spam"}), "report a message in someone else's chat")

    p3 = make_product(seller, title="Third phone for offer test", price="500000.00")
    neg = buyer.post("/negotiations", {"product_id": p3["id"], "amount": "450000"}).json()
    nid = neg["id"]
    offer_id = neg["offers"][-1]["id"] if neg.get("offers") else None
    _no(outsider.get(f"/negotiations/{nid}"), "read negotiation")
    _no(outsider.post(f"/negotiations/{nid}/respond", {"offer_id": offer_id, "action": "accept"}), "accept offer")
    _no(outsider.post(f"/negotiations/{nid}/withdraw", {}), "withdraw offer")


def test_wrong_party_cannot_do_the_other_sides_actions(paid_order):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    # buyer can't act as seller
    _no(buyer.post(f"/orders/{oid}/accept", {}), "buyer accepting own order as seller")
    _no(buyer.post(f"/orders/{oid}/dispatch", {"courier": "GIG", "tracking_number": "T1"}), "buyer dispatching")
    # seller can't confirm receipt on the buyer's behalf (that would release escrow to themselves)
    _no(seller.post(f"/orders/{oid}/confirm", {}), "seller confirming delivery")


def test_sellers_cannot_edit_other_sellers_listings_or_reply_to_their_reviews(make_seller, make_product):
    a, b = make_seller(), make_seller()
    p = make_product(a)
    _no(b.get(f"/seller/products/{p['id']}"), "read other seller's listing (seller view)")
    _no(b.patch(f"/seller/products/{p['id']}", {"price": "1.00"}), "edit other seller's listing")
    _no(b.post(f"/seller/products/{p['id']}/status", {"status": "inactive"}), "change status")
    _no(b.delete(f"/seller/products/{p['id']}"), "delete")
    _no(b.post(f"/reviews/{uuid.uuid4()}/reply", {"reply": "thanks!"}), "reply to unknown review")


def test_outsider_cannot_see_or_accept_someone_elses_flex_application(make_user, make_seller, make_product):
    buyer, outsider = make_user("Flex Buyer"), make_user("Outsider")
    setup_flex(buyer)
    product = flex_product(make_product, make_seller())
    app_ = apply(buyer, product)
    assert app_.status_code in (200, 201), app_.text
    aid = app_.json()["id"]
    _no(outsider.get(f"/bnpl/applications/{aid}"), "read flex application")
    _no(outsider.post(f"/bnpl/applications/{aid}/accept", {"accept_terms": True}), "accept flex application")
    _no(outsider.post(f"/bnpl/applications/{aid}/withdraw", {}), "withdraw flex application")
    _no(outsider.post(f"/bnpl/installments/{uuid.uuid4()}/pay", {}), "pay unknown instalment")


def test_notifications_are_private(make_user):
    a, b = make_user(), make_user()
    items = a.get("/notifications").json()
    items = items["items"] if isinstance(items, dict) else items
    assert items, "registration should create a welcome notification"
    _no(b.post(f"/notifications/{items[0]['id']}/read", {}), "mark someone else's notification read")


def _routes():
    for r in app.routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "effective_route_contexts"):
            yield from r.effective_route_contexts()


def _deps(d, acc):
    for sub in d.dependencies:
        if sub.call is not None:
            acc.add(getattr(sub.call, "__qualname__", repr(sub.call)))
        _deps(sub, acc)
    return acc


def test_every_admin_route_requires_a_permission():
    """Regression guard: a new /admin route without a permission check fails the build."""
    missing = []
    for r in _routes():
        if "/admin" in r.path:
            names = " ".join(_deps(r.dependant, set()))
            if not any(k in names for k in ("require_permission", "require_admin", "super_admin", "SuperAdmin")) \
                    and "nav_counts" not in r.endpoint.__name__ and "admin_me" not in r.endpoint.__name__ \
                    and "record_page_view" not in r.endpoint.__name__:
                missing.append(f"{sorted(r.methods)} {r.path}")
    assert not missing, f"admin routes without a permission dependency: {missing}"


def test_dev_routes_are_not_mounted_outside_dev(monkeypatch):
    from app.core.config import settings
    from app.main import create_app

    monkeypatch.setattr(settings, "environment", "staging")
    monkeypatch.setattr(settings, "jwt_secret", "x" * 48)
    monkeypatch.setattr(settings, "otp_secret", "y" * 48)
    monkeypatch.setattr(settings, "data_encryption_key", "Z" * 43 + "=")
    monkeypatch.setattr(settings, "cors_origins", ["https://staging.goods.ng"])
    monkeypatch.setattr(settings, "frontend_url", "https://staging.goods.ng")
    monkeypatch.setattr(settings, "admin_url", "https://admin.staging.goods.ng")
    staging = create_app()
    paths = [r.path for r in staging.routes if hasattr(r, "path") and r.path] + \
            [c.path for r in staging.routes if hasattr(r, "effective_route_contexts") for c in r.effective_route_contexts()]
    assert not [p for p in paths if "/dev/" in p], "dev/mock routes must not exist outside development/test"
    assert "/docs" not in paths or settings.environment != "production"
    _ = ADDRESS


def test_html_is_stripped_from_names_addresses_and_notes(client, make_seller, make_product):
    r = client.post("/api/v1/auth/register", json={"full_name": "<img src=x onerror=alert(1)>Ada <b>Obi</b>",
                                                    "email": f"x{uuid.uuid4().hex[:8]}@example.com", "password": "GoodsNG2026!"})
    assert r.status_code == 201, r.text
    assert r.json()["user"]["full_name"] == "Ada Obi"
    only_html = client.post("/api/v1/auth/register", json={"full_name": "<script>alert(1)</script>",
                                                           "email": f"y{uuid.uuid4().hex[:8]}@example.com", "password": "GoodsNG2026!"})
    assert only_html.status_code == 422


def test_checkout_address_and_note_are_cleaned(make_user, make_seller, make_product):
    buyer = make_user()
    p = make_product(make_seller())
    addr = {**ADDRESS, "street": "12 <script>steal()</script>Herbert Macaulay Way", "landmark": "<i>Opposite</i> the bank"}
    r = buyer.post("/checkout", {"product_id": p["id"], "quantity": 1, "delivery_option_index": 0, "address": addr,
                                 "note": "<a href='javascript:alert(1)'>call me</a> before delivery"})
    assert r.status_code == 201, r.text
    o = buyer.get(f"/orders/{r.json()['order_id']}").json()
    blob = str(o)
    assert "<script" not in blob and "<a " not in blob and "<i>" not in blob and "javascript:" not in blob


def test_production_config_refuses_unsafe_settings():
    from app.core.config import Settings

    s = Settings(environment="production", jwt_secret="short", cors_origins=["*"], frontend_url="http://goods.ng",
                 database_url="postgresql+psycopg://db/goods")
    with pytest.raises(RuntimeError) as e:
        s.validate_for_production()
    msg = str(e.value)
    for needle in ("JWT_SECRET", "CORS_ORIGINS", "FRONTEND_URL", "sslmode", "STORAGE_BACKEND", "CAPTCHA_PROVIDER"):
        assert needle in msg, needle
