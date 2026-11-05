"""Flutterwave (v3) adapter.

STATUS: implemented against Flutterwave's public API documentation; NOT yet verified against a
Flutterwave test account. Must be exercised end-to-end in staging before live use.
"""

import hmac
from decimal import Decimal

import httpx

from app.core.config import settings
from app.core.errors import ProviderError
from app.integrations.payments.base import InitResult, RefundResult, VerifyResult, WebhookEventData

BASE = "https://api.flutterwave.com/v3"


class FlutterwaveProvider:
    name = "flutterwave"

    def __init__(self):
        if not settings.flutterwave_secret_key or not settings.flutterwave_webhook_hash:
            raise RuntimeError("FLUTTERWAVE_SECRET_KEY and FLUTTERWAVE_WEBHOOK_HASH must be configured")
        self.secret = settings.flutterwave_secret_key
        self.webhook_hash = settings.flutterwave_webhook_hash

    def _call(self, method: str, path: str, **kw) -> dict:
        try:
            with httpx.Client(base_url=BASE, timeout=20, headers={"Authorization": f"Bearer {self.secret}"}) as c:
                r = c.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise ProviderError("Payment provider unreachable") from e
        body = r.json() if r.content else {}
        if r.status_code >= 400 or body.get("status") != "success":
            raise ProviderError(body.get("message") or "Payment provider error", details={"provider": "flutterwave"})
        return body.get("data", {})

    def initialize(self, *, reference, amount, currency, email, callback_url, metadata) -> InitResult:
        data = self._call("POST", "/payments", json={
            "tx_ref": reference, "amount": str(amount), "currency": currency, "redirect_url": callback_url,
            "customer": {"email": email}, "meta": metadata,
        })
        return InitResult(authorization_url=data["link"], provider_reference=reference, raw=data)

    def verify(self, reference: str) -> VerifyResult:
        data = self._call("GET", "/transactions/verify_by_reference", params={"tx_ref": reference})
        status = {"successful": "success", "failed": "failed"}.get(data.get("status"), "pending")
        return VerifyResult(
            reference=reference, status=status, amount=Decimal(str(data.get("amount", "0"))),
            currency=data.get("currency", "NGN"), provider_reference=str(data.get("id")),
            channel=data.get("payment_type"), raw=data,
        )

    def refund(self, *, reference, amount, reason) -> RefundResult:
        v = self.verify(reference)
        data = self._call("POST", f"/transactions/{v.provider_reference}/refund", json={"amount": str(amount), "comments": reason})
        return RefundResult(provider_refund_ref=str(data.get("id")), status="processing", raw=data)

    def verify_webhook_signature(self, body: bytes, headers: dict[str, str]) -> bool:
        sig = headers.get("verif-hash", "")
        return bool(sig) and hmac.compare_digest(sig, self.webhook_hash)

    def parse_webhook(self, payload: dict) -> WebhookEventData:
        data = payload.get("data", {})
        return WebhookEventData(
            event_key=f"{payload.get('event')}:{data.get('id')}",
            event_type=payload.get("event", "unknown"),
            reference=data.get("tx_ref"),
            raw=payload,
        )
