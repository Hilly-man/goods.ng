"""Paystack adapter.

STATUS: implemented against Paystack's public API documentation; NOT yet verified against a
Paystack test account. Must be exercised end-to-end in staging with test keys before live use.
Amounts are sent in kobo (minor units) as Paystack requires.
"""

import hashlib
import hmac
from decimal import Decimal

import httpx

from app.core.config import settings
from app.core.errors import ProviderError
from app.integrations.payments.base import InitResult, RefundResult, VerifyResult, WebhookEventData

BASE = "https://api.paystack.co"


def _to_kobo(amount: Decimal) -> int:
    return int((amount * 100).quantize(Decimal("1")))


class PaystackProvider:
    name = "paystack"

    def __init__(self, secret_key: str | None = None):
        self.secret = secret_key or settings.paystack_secret_key
        if not self.secret:
            raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=BASE, timeout=20, headers={"Authorization": f"Bearer {self.secret}"})

    def _call(self, method: str, path: str, **kw) -> dict:
        try:
            with self._client() as c:
                r = c.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise ProviderError("Payment provider unreachable") from e
        body = r.json() if r.content else {}
        if r.status_code >= 400 or not body.get("status"):
            raise ProviderError(body.get("message") or "Payment provider error", details={"provider": "paystack"})
        return body["data"]

    def initialize(self, *, reference, amount, currency, email, callback_url, metadata) -> InitResult:
        data = self._call("POST", "/transaction/initialize", json={
            "reference": reference, "amount": _to_kobo(amount), "currency": currency, "email": email,
            "callback_url": callback_url, "metadata": metadata,
        })
        return InitResult(authorization_url=data["authorization_url"], provider_reference=data.get("access_code", ""), raw=data)

    def verify(self, reference: str) -> VerifyResult:
        data = self._call("GET", f"/transaction/verify/{reference}")
        status = {"success": "success", "failed": "failed", "abandoned": "abandoned"}.get(data.get("status"), "pending")
        return VerifyResult(
            reference=reference, status=status, amount=Decimal(data["amount"]) / 100, currency=data.get("currency", "NGN"),
            provider_reference=str(data.get("id")), channel=data.get("channel"), raw=data,
        )

    def refund(self, *, reference, amount, reason) -> RefundResult:
        data = self._call("POST", "/refund", json={"transaction": reference, "amount": _to_kobo(amount), "merchant_note": reason})
        status = "completed" if data.get("status") == "processed" else "processing"
        return RefundResult(provider_refund_ref=str(data.get("id")), status=status, raw=data)

    def verify_webhook_signature(self, body: bytes, headers: dict[str, str]) -> bool:
        sig = headers.get("x-paystack-signature", "")
        expected = hmac.new(self.secret.encode(), body, hashlib.sha512).hexdigest()
        return bool(sig) and hmac.compare_digest(sig, expected)

    def parse_webhook(self, payload: dict) -> WebhookEventData:
        data = payload.get("data", {})
        return WebhookEventData(
            event_key=f"{payload.get('event')}:{data.get('id')}",
            event_type=payload.get("event", "unknown"),
            reference=data.get("reference"),
            raw=payload,
        )
