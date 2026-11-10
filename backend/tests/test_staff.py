"""Staff accounts (separate from customers), admin roles, and super-admin-only management."""

from datetime import timedelta

from app.core.time import utcnow
from app.models import AdminAuditLog, User
from tests.conftest import Api

STRONG = "Str0ng!Passw0rd"


def role_id(sup, code):
    return next(r["id"] for r in sup.get("/admin/roles").json() if r["code"] == code)


def invite(sup, email, code="customer_support", name="Ngozi Staff"):
    r = sup.post("/admin/staff", {"full_name": name, "email": email, "role_id": role_id(sup, code)})
    assert r.status_code == 201, r.text
    return r.json()


def accept(client, link, password=STRONG):
    token = link.split("token=")[-1]
    return client.post(f"/api/v1/auth/staff-invite/{token}", json={"password": password})


def login(client, email, password=STRONG):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r, (Api(client, r.json()["access_token"], r.json()["user"]) if r.status_code == 200 else None)


def test_roles_are_seeded_and_super_admin_only(make_admin, make_user):
    sup = make_admin(super_admin=True)
    codes = {r["code"] for r in sup.get("/admin/roles").json()}
    assert {"super_admin", "operations_manager", "finance", "customer_support", "trust_safety", "kyc_officer",
            "marketing", "auditor"} <= codes
    assert len(sup.get("/admin/permissions").json()) == 18
    ordinary_admin = make_admin(["users.manage", "settings.manage"])
    for path in ("/admin/staff", "/admin/roles", "/admin/permissions"):
        r = ordinary_admin.get(path)
        assert r.status_code == 403 and r.json()["error"]["code"] == "super_admin_required", path
    assert make_user().get("/admin/staff").status_code == 403


def test_invite_accept_login_and_role_permissions(client, db, make_admin):
    sup = make_admin(super_admin=True)
    staff = invite(sup, "ngozi@goods.ng", "kyc_officer")
    assert staff["status"] == "invited" and staff["role"]["code"] == "kyc_officer"
    # Can't log in before accepting (password unknown), weak passwords refused
    assert login(client, "ngozi@goods.ng")[0].status_code == 401
    view = client.get(f"/api/v1/auth/staff-invite/{staff['dev_invite_link'].split('token=')[-1]}").json()
    assert view["role"] == "KYC Officer" and view["email"] == "ngozi@goods.ng"
    assert accept(client, staff["dev_invite_link"], "password123").status_code == 422
    assert accept(client, staff["dev_invite_link"]).status_code == 200
    assert accept(client, staff["dev_invite_link"]).status_code == 404  # single use

    r, api = login(client, "ngozi@goods.ng")
    assert r.status_code == 200
    me = r.json()["user"]
    assert me["account_type"] == "staff" and me["admin_role_name"] == "KYC Officer"
    perms = api.get("/admin/me").json()
    assert perms["permissions"] == ["sellers.verify"] and perms["role_name"] == "KYC Officer"
    assert api.get("/admin/verifications").status_code == 200   # allowed by role
    assert api.get("/admin/refunds").status_code == 403         # not in role
    assert db.query(AdminAuditLog).filter_by(action="staff.create").count() == 1


def test_staff_cannot_use_marketplace(client, make_admin, make_seller, make_product, leaf_category):
    from tests.conftest import ADDRESS

    sup = make_admin(super_admin=True)
    staff = invite(sup, "ops@goods.ng", "operations_manager")
    accept(client, staff["dev_invite_link"])
    _, api = login(client, "ops@goods.ng")
    p = make_product(make_seller())
    checks = [
        api.post("/sellers", {"store_name": "Staff store", "state": "Lagos", "city": "Ikeja"}),
        api.post("/checkout", {"product_id": p["id"], "address": ADDRESS}),
        api.post("/negotiations", {"product_id": p["id"], "amount": "1000000"}),
        api.post("/conversations", {"product_id": p["id"], "body": "hi"}),
        api.post(f"/products/{p['id']}/favourite"),
        api.post("/bnpl/profile/bvn", {"bvn": "12345678901"}),
    ]
    for r in checks:
        assert r.status_code == 403 and r.json()["error"]["code"] == "staff_account", r.text
    # but staff can still browse public pages and use their admin tools
    assert api.get(f"/products/{p['slug']}").status_code == 200
    assert api.get("/admin/orders").status_code == 200


def test_staff_email_must_be_new(make_admin, make_user):
    sup = make_admin(super_admin=True)
    customer = make_user()
    r = sup.post("/admin/staff", {"full_name": "X Y", "email": customer.user["email"], "role_id": role_id(sup, "finance")})
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_taken"


def test_role_change_deactivation_and_safeguards(client, db, make_admin):
    sup = make_admin(super_admin=True)
    staff = invite(sup, "fin@goods.ng", "finance")
    accept(client, staff["dev_invite_link"])
    _, api = login(client, "fin@goods.ng")
    assert api.get("/admin/refunds").status_code == 200

    # change role → their sessions are revoked, new permissions apply on next sign-in
    r = sup.patch(f"/admin/staff/{staff['id']}", {"role_id": role_id(sup, "marketing")})
    assert r.json()["role"]["code"] == "marketing"
    assert api.get("/auth/me").status_code == 401
    _, api = login(client, "fin@goods.ng")
    assert api.get("/admin/refunds").status_code == 403 and api.get("/admin/promotions").status_code == 200

    # deactivate → can't sign in
    sup.patch(f"/admin/staff/{staff['id']}", {"is_active": False})
    assert login(client, "fin@goods.ng")[0].status_code == 401

    # can't demote/deactivate yourself; can't remove the last super admin
    me = sup.user["id"]
    assert sup.patch(f"/admin/staff/{me}", {"is_active": False}).json()["error"]["code"] == "self_change"
    other = invite(sup, "boss@goods.ng", "super_admin", "Second Boss")
    accept(client, other["dev_invite_link"])
    _, boss = login(client, "boss@goods.ng")
    assert boss.get("/admin/staff").status_code == 200  # second super admin works
    for u in db.query(User).filter(User.email != "boss@goods.ng", User.role == "super_admin"):
        u.is_active = False
    db.commit()
    r = boss.patch(f"/admin/staff/{boss.user['id']}", {"role_id": role_id(boss, "finance")})
    assert r.json()["error"]["code"] == "self_change"


def test_last_super_admin_protected(client, db, make_admin):
    sup = make_admin(super_admin=True)
    second = invite(sup, "boss2@goods.ng", "super_admin", "Boss Two")
    accept(client, second["dev_invite_link"])
    # with two active super admins, one may be demoted
    assert sup.patch(f"/admin/staff/{second['id']}", {"role_id": role_id(sup, "auditor")}).status_code == 200
    # now only `sup` is left; the second (now auditor) can't be promoted-away scenario: try deactivating sup via boss3
    third = invite(sup, "boss3@goods.ng", "super_admin", "Boss Three")
    accept(client, third["dev_invite_link"])
    _, boss3 = login(client, "boss3@goods.ng")
    sup_row = db.query(User).filter_by(id=sup.user["id"]).one()
    sup_row.is_active = False
    db.commit()
    # boss3 is now the only active super admin and can't be demoted by anyone (self-change also blocked)
    assert boss3.patch(f"/admin/staff/{boss3.user['id']}", {"is_active": False}).json()["error"]["code"] == "self_change"
    sup_row.is_active = True
    db.commit()
    _, sup2 = login(client, sup.user["email"], "Passw0rd!x")
    r = sup2.patch(f"/admin/staff/{third['id']}", {"is_active": False})
    assert r.status_code == 200  # sup2 is still an active super admin, so boss3 may be deactivated
    r = boss3.get("/admin/staff")
    assert r.status_code == 401


def test_custom_roles(client, make_admin):
    sup = make_admin(super_admin=True)
    system = next(r for r in sup.get("/admin/roles").json() if r["code"] == "finance")
    assert sup.put(f"/admin/roles/{system['id']}", {"name": "Hacked", "permissions": ["users.manage"]}).status_code == 403
    r = sup.post("/admin/roles", {"name": "Dispute Desk", "description": "Disputes only",
                                  "permissions": ["disputes.resolve", "orders.view"]})
    assert r.status_code == 201
    rid = r.json()["id"]
    assert sup.post("/admin/roles", {"name": "Dispute Desk", "permissions": ["orders.view"]}).status_code == 409
    staff = sup.post("/admin/staff", {"full_name": "Desk Person", "email": "desk@goods.ng", "role_id": rid}).json()
    accept(client, staff["dev_invite_link"])
    _, api = login(client, "desk@goods.ng")
    assert api.get("/admin/disputes").status_code == 200 and api.get("/admin/payments").status_code == 403
    # editing the role revokes holders' sessions and applies new permissions
    sup.put(f"/admin/roles/{rid}", {"name": "Dispute Desk", "permissions": ["disputes.resolve", "payments.view"]})
    assert api.get("/admin/disputes").status_code == 401
    _, api = login(client, "desk@goods.ng")
    assert api.get("/admin/payments").status_code == 200
    assert sup.delete(f"/admin/roles/{rid}").json()["error"]["code"] == "role_in_use"


def test_invite_expiry_and_resend(client, db, make_admin):
    sup = make_admin(super_admin=True)
    staff = invite(sup, "late@goods.ng", "auditor")
    db.query(User).filter_by(email="late@goods.ng").update({"invite_expires_at": utcnow() - timedelta(hours=1)})
    db.commit()
    assert accept(client, staff["dev_invite_link"]).json()["error"]["code"] == "invite_expired"
    fresh = sup.post(f"/admin/staff/{staff['id']}/resend-invite").json()
    assert accept(client, fresh["dev_invite_link"]).status_code == 200
    assert sup.post(f"/admin/staff/{staff['id']}/resend-invite").json()["error"]["code"] == "already_active"


def test_users_page_lists_customers_only(make_admin, make_user):
    sup = make_admin(super_admin=True)
    c = make_user()
    emails = {u["email"] for u in sup.get("/admin/users", params={"page_size": 100}).json()["items"]}
    assert c.user["email"] in emails and sup.user["email"] not in emails
    r = sup.post(f"/admin/users/{sup.user['id']}/status", {"is_active": False, "reason": "testing"})
    assert r.json()["error"]["code"] == "staff_account"


def test_nav_counts_only_include_permitted_queues(make_admin, make_user):
    full = make_admin(super_admin=True).get("/admin/nav-counts").json()
    assert {"disputes", "refunds", "verifications", "products", "reports", "reviews"} <= full.keys()
    assert all(isinstance(v, int) for v in full.values())
    limited = make_admin(permissions=["disputes.resolve"]).get("/admin/nav-counts").json()
    assert set(limited) == {"disputes"}
    assert make_user().get("/admin/nav-counts").status_code == 403


def test_overview_trends_shape_and_permission(make_admin, make_seller, make_product):
    from app.core.cache import cache

    make_product(make_seller())
    cache.invalidate("admin:trends:")
    r = make_admin(super_admin=True).get("/admin/overview/trends", params={"days": 7})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["days"] == 7 and len(d["series"]) == 7
    assert d["series"][-1]["new_listings"] >= 1
    assert {"full", "bnpl"} == set(d["payment_mix"])
    assert any(c["count"] >= 1 for c in d["top_categories"])
    assert make_admin(permissions=["disputes.resolve"]).get("/admin/overview/trends").status_code == 403


def test_admin_seller_dashboard(make_seller, make_product, make_admin):
    seller = make_seller()
    make_product(seller)
    sid = seller.seller["id"]

    admin = make_admin(["sellers.verify"])
    d = admin.get(f"/admin/sellers/{sid}").json()
    assert d["seller"]["store_name"] and d["stats"]["active_listings"] >= 1
    assert d["listings"] and d["wallet"] is None  # wallet needs payments.view

    finance = make_admin(["sellers.verify", "payments.view"]).get(f"/admin/sellers/{sid}").json()
    assert finance["wallet"] is not None and "available" in finance["wallet"]

    assert make_admin(["orders.view"]).get(f"/admin/sellers/{sid}").status_code == 403


def test_admin_wallets_by_seller(make_seller, make_admin):
    make_seller()
    finance = make_admin(["payments.view"]).get("/admin/wallets").json()
    assert finance["items"] and "available" in finance["items"][0]
    assert make_admin(["sellers.verify"]).get("/admin/wallets").status_code == 403
