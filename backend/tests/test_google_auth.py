from urllib.parse import parse_qs, urlparse

from app.core.security import totp_now

G = "/api/v1/auth/google"


def _google(client, email, name="Ada Okafor", next_="/saved", tamper_nonce=False):
    """Drive the mock Google flow and return the final callback response (not followed)."""
    client.cookies.clear()
    start = client.get(f"{G}/start", params={"next": next_}, follow_redirects=False)
    assert start.status_code == 302
    q = parse_qs(urlparse(start.headers["location"]).query)
    state, nonce = q["state"][0], q["nonce"][0]
    approve = client.get(f"{G}/mock-approve", follow_redirects=False,
                         params={"state": state, "nonce": "x" if tamper_nonce else nonce, "email": email, "name": name})
    return client.get(approve.headers["location"], follow_redirects=False)


def test_config_reports_mock_in_test(client):
    assert client.get(f"{G}/config").json() == {"enabled": True, "mock": True}


def test_new_google_user_is_created_signed_in_and_redirected(client):
    r = _google(client, "new.google@example.com")
    assert r.status_code == 302 and r.headers["location"] == "/saved"
    assert "gng_rt=" in r.headers.get("set-cookie", "")
    me = client.post("/api/v1/auth/refresh", headers={"X-Requested-With": "goodsng"}).json()["user"]
    assert me["email"] == "new.google@example.com" and me["full_name"] == "Ada Okafor"


def test_existing_account_with_same_verified_email_is_linked(client, make_user):
    u = make_user(name="Chidi Eze")
    r = _google(client, u.user["email"], name="Someone Else")
    assert r.headers["location"] == "/saved"
    me = client.post("/api/v1/auth/refresh", headers={"X-Requested-With": "goodsng"}).json()["user"]
    assert me["id"] == u.user["id"] and me["full_name"] == "Chidi Eze"
    # second Google sign-in finds the same account by Google id
    assert _google(client, u.user["email"]).headers["location"] == "/saved"


def test_staff_cannot_use_google(client, make_admin):
    admin = make_admin()
    assert _google(client, admin.user["email"]).headers["location"] == "/login?oauth_error=staff"


def test_two_factor_accounts_get_an_mfa_challenge(client, make_user):
    u = make_user()
    secret = u.post("/auth/2fa/setup").json()["secret"]
    u.post("/auth/2fa/enable", {"code": totp_now(secret)})
    r = _google(client, u.user["email"])
    loc = r.headers["location"]
    assert loc.startswith("/login?next=%2Fsaved#mfa=") and "gng_rt=" not in r.headers.get("set-cookie", "")


def test_state_and_nonce_are_enforced(client):
    assert _google(client, "n@example.com", tamper_nonce=True).headers["location"] == "/login?oauth_error=state"
    client.cookies.clear()
    r = client.get(f"{G}/callback", params={"code": "mock.e30", "state": "forged"}, follow_redirects=False)
    assert r.headers["location"] == "/login?oauth_error=state"


def test_open_redirects_are_neutralised(client):
    assert _google(client, "redir@example.com", next_="//evil.example/x").headers["location"] == "/"


def test_cancel_returns_to_login(client):
    r = client.get(f"{G}/callback", params={"error": "access_denied"}, follow_redirects=False)
    assert r.headers["location"] == "/login?oauth_error=cancelled"
