from decimal import Decimal

from app.models import AdminAuditLog

# Goods Flex tests live in tests/test_flex.py


def test_bnpl_quote_matches_partner_terms(client, make_seller, make_product):
    s = make_seller()
    p = make_product(s)
    opts = client.get("/api/v1/bnpl/quote", params={"product_id": p["id"]}).json()["options"]
    three = next(o for o in opts if o["tenor_months"] == 3)
    assert three["down_payment"] == "1050000.00" and three["financed_amount"] == "600000.00"
    assert Decimal(three["total_payable"]) == Decimal(three["down_payment"]) + Decimal(three["financed_amount"]) + \
        Decimal(three["financing_charge"])


# ---------------- Reviews ----------------
def test_verified_review_only_after_completion(paid_order, make_user):
    buyer, seller, _, order = paid_order()
    oid = order["id"]
    r = buyer.post("/reviews", {"order_id": oid, "rating": 5, "comment": "Great"})
    assert r.json()["error"]["code"] == "order_not_completed"
    seller.post(f"/orders/{oid}/accept")
    seller.post(f"/orders/{oid}/dispatch", {"carrier": "GIG", "tracking_reference": "T1"})
    buyer.post(f"/orders/{oid}/confirm")
    assert make_user().post("/reviews", {"order_id": oid, "rating": 1}).status_code == 404
    r = buyer.post("/reviews", {"order_id": oid, "rating": 5, "comment": "Original phone, fast delivery"})
    assert r.status_code == 201 and r.json()["is_verified_purchase"] is True
    assert buyer.post("/reviews", {"order_id": oid, "rating": 1}).status_code == 409
    rev = seller.get(f"/sellers/{seller.seller['slug']}/reviews").json()
    assert rev["summary"]["count"] == 1 and rev["summary"]["average"] == "5.00"


def test_unverified_review_requires_real_interaction(make_seller, make_user, make_product):
    s, buyer = make_seller(), make_user()
    p = make_product(s)
    r = buyer.post("/reviews", {"seller_id": s.seller["id"], "rating": 1})
    assert r.json()["error"]["code"] == "no_interaction"
    cid = buyer.post("/conversations", {"product_id": p["id"], "body": "Hi"}).json()["conversation_id"]
    assert buyer.post("/reviews", {"seller_id": s.seller["id"], "rating": 4}).status_code == 403  # seller hasn't replied
    s.post(f"/conversations/{cid}/messages", {"body": "Hello!"})
    r = buyer.post("/reviews", {"seller_id": s.seller["id"], "rating": 4})
    assert r.status_code == 201 and r.json()["is_verified_purchase"] is False
    assert buyer.post("/reviews", {"seller_id": s.seller["id"], "rating": 5}).status_code == 409
    assert s.post("/reviews", {"seller_id": s.seller["id"], "rating": 5}).status_code == 403


# ---------------- Admin ----------------
def test_admin_endpoints_require_permissions(make_user, make_admin):
    u = make_user()
    for url in ["/admin/overview", "/admin/users", "/admin/disputes", "/admin/audit-logs", "/admin/ledger"]:
        assert u.get(url).status_code == 403, url
    limited = make_admin(["analytics.view"])
    assert limited.get("/admin/overview").status_code == 200
    assert limited.get("/admin/users").status_code == 403
    # only super admins can create staff accounts
    assert limited.post("/admin/staff", {"full_name": "X Y", "email": "x@goods.ng",
                                         "role_id": "00000000-0000-0000-0000-000000000000"}).status_code == 403


def test_customers_cannot_be_promoted_to_admin(db, make_user, make_admin):
    u = make_user()
    sup = make_admin(super_admin=True)
    # The old "promote a user" endpoint is gone; staff are created separately by a super admin.
    assert sup.post(f"/admin/users/{u.user['id']}/role", {"role": "admin"}).status_code in (404, 405)
    # Even if a customer row were tampered with to say "admin", it grants nothing.
    from app.models import User

    db.query(User).filter_by(id=u.user["id"]).update({"role": "super_admin"})
    db.commit()
    assert u.get("/admin/overview").status_code == 403
    _ = AdminAuditLog


def test_verification_flow_with_encrypted_kyc(db, make_seller, make_admin):
    from app.models import SellerVerification
    from tests.conftest import png_bytes

    s = make_seller()
    r = s.post("/sellers/me/verification", data={"level": "identity_verified", "document_type": "nin",
                                                 "document_number": "12345678901"},
               files={"file": ("id.png", png_bytes(), "image/png")})
    assert r.status_code == 201, r.text
    v = db.query(SellerVerification).one()
    assert "12345678901" not in v.document_number_enc  # encrypted at rest
    assert s.get("/sellers/me/verification").json()["requests"][0]["document_number"] == "••••8901"
    admin = make_admin(["sellers.verify"])
    assert admin.get(f"/admin/verifications/{v.id}/document-number").json()["document_number"] == "12345678901"
    admin.post(f"/admin/verifications/{v.id}/decide", {"approve": True, "notes": "NIN matched"})
    assert s.get("/sellers/me").json()["verification_level"] == "identity_verified"
    assert db.query(AdminAuditLog).filter(AdminAuditLog.action.in_(["kyc.reveal", "verification.decide"])).count() == 2


def test_listing_moderation(client, make_seller, make_product, make_admin):
    s = make_seller()
    p = make_product(s)
    admin = make_admin(["listings.moderate"])
    assert admin.post(f"/admin/products/{p['id']}/moderate", {"action": "reject"}).status_code == 400
    admin.post(f"/admin/products/{p['id']}/moderate", {"action": "reject", "reason": "Counterfeit suspected"})
    assert client.get(f"/api/v1/products/{p['slug']}").status_code == 404
    sp = s.get(f"/seller/products/{p['id']}").json()
    assert sp["status"] == "rejected" and sp["rejection_reason"] == "Counterfeit suspected"


def test_admin_overview_metrics(paid_order, make_admin):
    paid_order()
    o = make_admin(["analytics.view"]).get("/admin/overview").json()
    assert o["total_orders"] == 1 and o["in_escrow_value"] == "1508500.00"


def test_notifications_created(paid_order):
    buyer, seller, _, _ = paid_order()
    assert any(n["event_type"] == "new_order" for n in seller.get("/notifications").json())
    assert buyer.get("/notifications/unread-count").json()["unread"] >= 1
    buyer.post("/notifications/read-all")
    assert buyer.get("/notifications/unread-count").json()["unread"] == 0
