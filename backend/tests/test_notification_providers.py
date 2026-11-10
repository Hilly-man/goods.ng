"""Real SMS/email adapter tests (mocked transport; no external calls)."""

import json

import httpx
import pytest

from app.core.config import settings
from app.core.time import utcnow
from app.models import OutboundMessage
from app.modules.notifications.email_templates import render_email, render_text
from app.modules.notifications.service import (
    PostmarkSender,
    ResendSender,
    SmtpSender,
    TermiiSender,
    get_sender,
)


def msg(channel="sms", recipient="+2348012345678", body="Hello from Goods.ng", subject=None):
    return OutboundMessage(channel=channel, recipient=recipient, body=body, subject=subject, next_attempt_at=utcnow())


def test_termii_sms_payload_and_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/sms/send"
        body = json.loads(request.content)
        assert body == {"api_key": "test-key", "to": "+2348012345678", "from": "GoodsNG",
                        "sms": "Hello from Goods.ng", "type": "plain", "channel": "generic"}
        return httpx.Response(200, json={"code": "ok", "message": "Success"})

    TermiiSender(api_key="test-key", sender_id="GoodsNG", base_url="https://termii.test",
                 transport=httpx.MockTransport(handler)).send(msg())


def test_termii_sms_error_is_raised():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"message": "down"})

    with pytest.raises(RuntimeError):
        TermiiSender(api_key="test-key", base_url="https://termii.test",
                     transport=httpx.MockTransport(handler)).send(msg())


def test_postmark_email_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/email"
        assert request.headers["x-postmark-server-token"] == "server-token"
        body = json.loads(request.content)
        assert body["From"] == "notifications@goods.ng"
        assert body["To"] == "buyer@example.com"
        assert body["Subject"] == "Your order"
        assert body["TextBody"] == "Order confirmed"
        assert body["MessageStream"] == "outbound"
        return httpx.Response(200, json={"MessageID": "abc"})

    PostmarkSender(server_token="server-token", from_addr="notifications@goods.ng",
                   transport=httpx.MockTransport(handler)).send(
        msg("email", "buyer@example.com", "Order confirmed", "Your order"))


def test_branded_email_template():
    html = render_email("payment_confirmed", "Payment confirmed", "Your order is confirmed.", "/orders/123",
                        "Ada Nwosu")
    assert html.startswith("<!DOCTYPE html>")
    assert "Goods<span" in html
    assert "Hi Ada," in html
    assert f"{settings.frontend_url}/orders/123" in html
    assert "support@goods.ng" in html
    assert "+234 201 330 0000" in html
    assert "Lagos, Nigeria" in html


def test_email_template_escapes_body():
    html = render_email("new_message", "New message", "<script>alert(1)</script>", "/messages")
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_password_reset_template_shows_code():
    html = render_email("password_reset", "Reset your password", "Your code is 123456.", "/login", "Ada",
                        code="123456")
    assert "123456" in html
    assert "Expires in" in html
    assert html.count("123456") >= 2  # styled box + plain body (helps Gmail detect the code)


def test_plain_text_email_includes_contact_details():
    text = render_text("Payment confirmed", "Your order is confirmed.")
    assert "Payment confirmed" in text
    assert "support@goods.ng" in text
    assert f"{settings.frontend_url}/account/notifications" in text


def test_resend_html_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["html"] == "<p>Order confirmed</p>"
        assert body["text"] == "Order confirmed"
        return httpx.Response(200, json={"id": "email_123"})

    message = msg("email", "buyer@example.com", "Order confirmed", "Your order")
    message.html = "<p>Order confirmed</p>"
    ResendSender(api_key="re_test", from_addr="notifications@mail.goods.ng",
                 transport=httpx.MockTransport(handler)).send(message)


def test_resend_email_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/emails"
        assert request.headers["authorization"] == "Bearer re_test"
        body = json.loads(request.content)
        assert body == {"from": "notifications@mail.goods.ng", "to": ["buyer@example.com"],
                        "subject": "Your order", "text": "Order confirmed"}
        return httpx.Response(200, json={"id": "email_123"})

    ResendSender(api_key="re_test", from_addr="notifications@mail.goods.ng",
                 transport=httpx.MockTransport(handler)).send(
        msg("email", "buyer@example.com", "Order confirmed", "Your order"))


def test_resend_email_error_is_raised():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "invalid from"})

    with pytest.raises(RuntimeError):
        ResendSender(api_key="re_test", from_addr="notifications@mail.goods.ng",
                     transport=httpx.MockTransport(handler)).send(
            msg("email", "buyer@example.com", "Order confirmed", "Your order"))


class FakeSMTP:
    def __init__(self):
        self.started_tls = False
        self.login_credentials = None
        self.sent = []
        self.quit_called = False

    def starttls(self):
        self.started_tls = True

    def login(self, username, password):
        self.login_credentials = (username, password)

    def send_message(self, message):
        self.sent.append(message)

    def quit(self):
        self.quit_called = True


def test_smtp_login_starttls_and_send():
    fake = FakeSMTP()
    SmtpSender(host="smtp.test", port=587, username="user", password="pass",
               from_addr="notifications@goods.ng", smtp_factory=lambda *a, **k: fake).send(
        msg("email", "buyer@example.com", "Order confirmed", "Your order"))
    assert fake.started_tls and fake.login_credentials == ("user", "pass") and fake.quit_called
    assert len(fake.sent) == 1
    assert fake.sent[0]["To"] == "buyer@example.com"
    assert fake.sent[0]["From"] == "notifications@goods.ng"
    assert fake.sent[0]["Subject"] == "Your order"


def test_sender_selection_uses_console_by_default():
    assert get_sender("sms").__class__.__name__ == "ConsoleSender"
    assert get_sender("email").__class__.__name__ == "ConsoleSender"
