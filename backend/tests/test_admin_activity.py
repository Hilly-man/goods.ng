import uuid

from tests.conftest import PASSWORD


def _log(api, **params):
    r = api.get("/admin/audit-logs", params={"page_size": 100, **params})
    assert r.status_code == 200, r.text
    return r.json()["items"]


def test_staff_sign_ins_and_failures_are_recorded_customers_are_not(client, make_admin, make_user):
    viewer = make_admin(super_admin=True)
    admin = make_admin(permissions=["users.manage"])
    # a failed attempt on a staff account
    assert client.post("/api/v1/auth/login", json={"email": admin.user["email"], "password": "wrong-pass-1"}).status_code == 401
    customer = make_user()
    client.post("/api/v1/auth/login", json={"email": customer.user["email"], "password": PASSWORD})

    auth = _log(viewer, category="auth", actor_id=admin.user["id"])
    actions = {(e["action"], e["outcome"]) for e in auth}
    assert ("auth.sign_in", "success") in actions and ("auth.sign_in_failed", "failed") in actions
    assert auth[0]["actor"]["email"] == admin.user["email"]
    assert not _log(viewer, category="auth", actor_id=customer.user["id"])


def test_admin_actions_carry_actor_ip_and_user_agent(make_admin, make_user):
    viewer = make_admin(super_admin=True)
    admin = make_admin(permissions=["users.manage"])
    target = make_user()
    r = admin.post(f"/admin/users/{target.user['id']}/status", {"is_active": False, "reason": "Fraud investigation"},
                   headers={"User-Agent": "pytest-browser/1.0"})
    assert r.status_code == 200, r.text
    e = next(x for x in _log(viewer, actor_id=admin.user["id"], category="action") if x["action"] == "user.status")
    assert e["actor"]["name"] == "Admin" and e["user_agent"] == "pytest-browser/1.0" and e["outcome"] == "success"


def test_refused_admin_attempts_are_recorded_by_the_safety_net(make_admin):
    viewer = make_admin(super_admin=True)
    limited = make_admin(permissions=["users.manage"])
    r = limited.post(f"/admin/refunds/{uuid.uuid4()}/approve", {})
    assert r.status_code == 403
    denied = _log(viewer, actor_id=limited.user["id"], outcome="denied")
    assert denied and denied[0]["category"] == "api" and denied[0]["details"]["status"] == 403
    assert "/refunds/" in denied[0]["target_id"]


def test_page_views_are_deduplicated_and_hidden_by_default(make_admin):
    viewer = make_admin(super_admin=True)
    a = make_admin(permissions=["orders.view"])
    assert a.post("/admin/activity/view", {"path": "/orders", "title": "Orders"}).json() == {"recorded": True}
    assert a.post("/admin/activity/view", {"path": "/orders"}).json() == {"recorded": False}
    assert len(_log(viewer, actor_id=a.user["id"], category="view")) == 1
    assert all(e["category"] != "view" for e in _log(viewer, actor_id=a.user["id"]))


def test_summary_lists_every_admin_and_export_is_itself_logged(make_admin):
    viewer = make_admin(super_admin=True)
    idle = make_admin(permissions=["orders.view"])
    summ = viewer.get("/admin/audit-logs/summary", params={"days": 7}).json()
    row = next(x for x in summ["admins"] if x["id"] == idle.user["id"])
    assert row["sign_ins"] >= 1 and row["actions"] == 0
    csv = viewer.get("/admin/audit-logs/export", params={"days": 7})
    assert csv.status_code == 200 and csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[0].startswith("time_utc,admin,email,role")
    assert _log(viewer, q="activity.export", actor_id=viewer.user["id"])


def test_activity_report_requires_audit_permission(make_admin):
    assert make_admin(permissions=["orders.view"]).get("/admin/audit-logs").status_code == 403
