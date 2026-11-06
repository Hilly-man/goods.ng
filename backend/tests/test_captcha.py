import time

import pytest

from app.core.config import settings
from app.modules.auth import captcha
from tests.conftest import PASSWORD

L = "/api/v1/auth/login"


@pytest.fixture
def mock_captcha(monkeypatch):
    monkeypatch.setattr(settings, "captcha_provider", "mock")


def _login(client, email, password=PASSWORD, token=None):
    body = {"email": email, "password": password, **({"captcha_token": token} if token else {})}
    return client.post(L, json=body)


def test_new_device_must_pass_captcha_then_is_remembered(client, make_user, mock_captcha):
    u = make_user()
    client.cookies.clear()
    assert client.get("/api/v1/auth/captcha").json()["required"] is True
    r = _login(client, u.user["email"])
    assert r.status_code == 400 and r.json()["error"]["code"] == "captcha_required"
    assert _login(client, u.user["email"], token="wrong").json()["error"]["code"] == "captcha_required"
    ok = _login(client, u.user["email"], token=captcha.MOCK_TOKEN)
    assert ok.status_code == 200, ok.text
    assert "gng_seen=" in ok.headers.get("set-cookie", "")
    # Same browser within 24h: no check
    assert client.get("/api/v1/auth/captcha").json()["required"] is False
    assert _login(client, u.user["email"]).status_code == 200


def test_device_returning_after_24_hours_is_checked_again(client, make_user, mock_captcha):
    u = make_user()
    old = int(time.time()) - captcha.WINDOW_SECONDS - 60
    client.cookies.clear()
    client.cookies.set(captcha.SEEN_COOKIE, f"{old}.{captcha._sig(old)}", path="/api/v1/auth")
    assert _login(client, u.user["email"]).json()["error"]["code"] == "captcha_required"


def test_forged_seen_cookie_is_ignored(client, make_user, mock_captcha):
    u = make_user()
    now = int(time.time())
    client.cookies.clear()
    client.cookies.set(captcha.SEEN_COOKIE, f"{now}.deadbeef", path="/api/v1/auth")
    assert _login(client, u.user["email"]).json()["error"]["code"] == "captcha_required"


def test_repeated_wrong_passwords_bring_the_check_back(client, make_user, mock_captcha):
    u = make_user()
    client.cookies.clear()
    assert _login(client, u.user["email"], token=captcha.MOCK_TOKEN).status_code == 200  # device now trusted
    for _ in range(captcha.FAILED_ATTEMPTS_THRESHOLD):
        assert _login(client, u.user["email"], password="wrong-pass-1").status_code == 401
    r = _login(client, u.user["email"])
    assert r.json()["error"]["code"] == "captcha_required"


def test_password_is_not_checked_before_captcha(client, make_user, mock_captcha):
    """Bots can't learn whether a password is right without solving the captcha."""
    u = make_user()
    client.cookies.clear()
    bad = _login(client, u.user["email"], password="wrong-pass-1")
    good = _login(client, u.user["email"])
    assert bad.json()["error"]["code"] == good.json()["error"]["code"] == "captcha_required"


def test_mock_token_rejected_outside_dev(client, make_user, monkeypatch):
    monkeypatch.setattr(settings, "captcha_provider", "mock")
    monkeypatch.setattr(settings, "environment", "staging")
    assert captcha.verify(captcha.MOCK_TOKEN, None) is False


def test_production_requires_a_real_provider(monkeypatch):
    from app.core.config import Settings

    s = Settings(environment="production", captcha_provider="mock")
    with pytest.raises(Exception) as e:
        s.validate_for_production()
    assert "CAPTCHA_PROVIDER" in str(e.value)
