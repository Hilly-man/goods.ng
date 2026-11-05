from tests.conftest import PASSWORD, Api

CSRF = {"X-Requested-With": "goodsng"}


def test_register_login_me(client):
    r = client.post("/api/v1/auth/register", json={"full_name": "Ada Obi", "email": "Ada@Example.com",
                                                   "phone": "0803 123 4567", "password": PASSWORD})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["phone"] == "+2348031234567"
    assert "password_hash" not in body["user"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["full_name"] == "Ada Obi"


def test_duplicate_email_and_weak_password(client):
    payload = {"full_name": "A B", "email": "dup@example.com", "password": PASSWORD}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).json()["error"]["code"] == "email_taken"
    weak = client.post("/api/v1/auth/register", json={**payload, "email": "x@example.com", "password": "abcdefgh"})
    assert weak.status_code == 422


def test_invalid_phone_rejected(client):
    r = client.post("/api/v1/auth/register", json={"full_name": "A B", "email": "p@example.com", "phone": "12345",
                                                   "password": PASSWORD})
    assert r.status_code == 422


def test_unauthenticated_and_tampered_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_lockout_after_failed_logins(client, make_user):
    u = make_user(phone_verified=False)
    email = u.user["email"]
    for _ in range(5):
        assert client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpass1"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 401 and r.json()["error"]["code"] == "account_locked"


def test_refresh_rotation_and_reuse_detection(client, make_user):
    u = make_user(phone_verified=False)
    old_cookie = client.cookies.get("gng_rt")
    assert old_cookie
    # CSRF header required for cookie-authenticated refresh
    assert client.post("/api/v1/auth/refresh").status_code == 403
    r = client.post("/api/v1/auth/refresh", headers=CSRF)
    assert r.status_code == 200
    new_cookie = client.cookies.get("gng_rt")
    assert new_cookie and new_cookie != old_cookie
    # Replaying the rotated token *after the grace window* revokes the whole family
    from datetime import timedelta

    from app.core.db import SessionLocal
    from app.core.time import utcnow
    from app.models import RefreshToken

    with SessionLocal() as db:
        db.query(RefreshToken).filter(RefreshToken.revoked_at.isnot(None)).update(
            {"revoked_at": utcnow() - timedelta(minutes=5)})
        db.commit()
    client.cookies.set("gng_rt", old_cookie, path="/api/v1/auth")
    r = client.post("/api/v1/auth/refresh", headers=CSRF)
    assert r.status_code == 401 and r.json()["error"]["code"] == "refresh_reuse"
    client.cookies.set("gng_rt", new_cookie, path="/api/v1/auth")
    assert client.post("/api/v1/auth/refresh", headers=CSRF).status_code == 401
    _ = u


def test_otp_flow_and_attempt_limit(make_user):
    u = make_user(phone_verified=False)
    code = u.post("/auth/otp/request", {}).json()["dev_code"]
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert u.post("/auth/otp/verify", {"code": wrong}).json()["error"]["code"] == "otp_invalid"
    assert u.post("/auth/otp/verify", {"code": code}).json()["error"]["code"] == "otp_locked"
    code = u.post("/auth/otp/request", {}).json()["dev_code"]
    assert u.post("/auth/otp/verify", {"code": code}).json()["phone_verified"] is True


def test_otp_request_rate_limited(make_user):
    u = make_user(phone_verified=False)
    for _ in range(3):
        assert u.post("/auth/otp/request", {}).status_code == 200
    assert u.post("/auth/otp/request", {}).status_code == 429


def test_password_change_revokes_existing_tokens(client, make_user):
    u = make_user(phone_verified=False)
    old_token = u.token
    r = u.post("/auth/password/change", {"current_password": PASSWORD, "new_password": "N3wPassword!"})
    assert r.status_code == 200
    assert Api(client, old_token).get("/auth/me").status_code == 401
    assert Api(client, r.json()["access_token"]).get("/auth/me").status_code == 200


def test_password_reset(client, make_user):
    u = make_user(phone_verified=False)
    code = client.post("/api/v1/auth/password/forgot", json={"email": u.user["email"]}).json()["dev_code"]
    r = client.post("/api/v1/auth/password/reset", json={"email": u.user["email"], "code": code,
                                                          "new_password": "Brand4NewPw"})
    assert r.status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": u.user["email"], "password": "Brand4NewPw"}).status_code == 200
    # unknown email does not reveal existence
    assert client.post("/api/v1/auth/password/forgot", json={"email": "nobody@example.com"}).status_code == 200


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"


def test_concurrent_refresh_within_grace_window(client, make_user):
    make_user(phone_verified=False)
    cookie = client.cookies.get("gng_rt")
    # Two tabs refresh with the same token at (nearly) the same time: both succeed.
    a = client.post("/api/v1/auth/refresh", headers=CSRF)
    client.cookies.set("gng_rt", cookie, path="/api/v1/auth")
    b = client.post("/api/v1/auth/refresh", headers=CSRF)
    assert a.status_code == 200 and b.status_code == 200
