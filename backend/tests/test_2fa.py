"""Two-factor authentication (TOTP) and admin enforcement."""

import time

from app.core.config import settings
from app.core.security import totp_now
from tests.conftest import PASSWORD


def login_challenge(api):
    r = api.post("/auth/login", {"email": api.user["email"], "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()


def test_totp_setup_login_recovery_and_disable(make_user):
    u = make_user()
    assert u.get("/auth/me").json()["two_factor_enabled"] is False

    setup = u.post("/auth/2fa/setup").json()
    secret = setup["secret"]
    assert setup["otpauth_url"].startswith("otpauth://totp/")
    assert setup["qr_svg"].startswith("data:image/svg+xml")
    assert u.post("/auth/2fa/enable", {"code": "000000"}).status_code == 401

    codes = u.post("/auth/2fa/enable", {"code": totp_now(secret)}).json()["recovery_codes"]
    assert len(codes) == 8 and u.get("/auth/me").json()["two_factor_enabled"] is True

    challenge = login_challenge(u)
    assert challenge["mfa_required"] is True and challenge["mfa_ticket"]
    ticket = challenge["mfa_ticket"]
    assert u.post("/auth/mfa/verify", {"mfa_ticket": ticket, "code": "000000"}).status_code == 401
    # The code used to enable 2FA cannot be replayed; use the next time step.
    assert u.post("/auth/mfa/verify", {"mfa_ticket": ticket, "code": totp_now(secret)}).status_code == 401
    ok = u.post("/auth/mfa/verify", {"mfa_ticket": ticket, "code": totp_now(secret, time.time() + 30)})
    assert ok.status_code == 200 and ok.json()["access_token"]

    # A recovery code works once, then is consumed.
    ticket = login_challenge(u)["mfa_ticket"]
    assert u.post("/auth/mfa/verify", {"mfa_ticket": ticket, "code": codes[0]}).status_code == 200
    ticket = login_challenge(u)["mfa_ticket"]
    assert u.post("/auth/mfa/verify", {"mfa_ticket": ticket, "code": codes[0]}).status_code == 401

    assert u.post("/auth/2fa/disable", {"password": "wrong", "code": codes[1]}).json()["error"]["code"] == "invalid_password"
    assert u.post("/auth/2fa/disable", {"password": PASSWORD, "code": codes[1]}).status_code == 200
    assert u.get("/auth/me").json()["two_factor_enabled"] is False
    assert "access_token" in login_challenge(u)


def test_admin_api_requires_2fa_when_enforced(make_admin, monkeypatch):
    admin = make_admin(["settings.manage"])
    monkeypatch.setattr(settings, "admin_2fa_required", True)

    blocked = admin.get("/admin/settings")
    assert blocked.status_code == 403 and blocked.json()["error"]["code"] == "admin_2fa_required"

    setup = admin.post("/auth/2fa/setup").json()
    assert admin.post("/auth/2fa/enable", {"code": totp_now(setup["secret"])}).status_code == 200
    assert admin.get("/admin/settings").status_code == 200
