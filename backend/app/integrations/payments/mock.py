"""MOCK payment provider — development and automated testing ONLY.

It behaves like an external provider: it keeps its own state (mock_provider_records, written in a
separate DB session as if it were a remote system), sends HMAC-signed webhooks, and answers
server-side verification calls. This lets the full verify-before-trust flow run end-to-end locally.
It moves no real money. Production boot is refused while this provider is configured.
"""

import hashlib
import hmac
import json
import uuid
from decimal import Decimal

from app.core.config import settings
from app.core.time import utcnow
from app.integrations.payments.base import InitResult, RefundResult, VerifyResult, WebhookEventData

SIGNATURE_HEADER = "x-mock-signature"


def _session():
    from app.core.db import SessionLocal

    return SessionLocal()


def _get(db, kind, reference):
    from app.models import MockProviderRecord

    return db.query(MockProviderRecord).filter_by(kind=kind, reference=reference).one_or_none()


def sign(body: bytes) -> str:
    return hmac.new(settings.mock_provider_secret.encode(), body, hashlib.sha512).hexdigest()


class MockPaymentProvider:
    name = "mock"

    def initialize(self, *, reference, amount, currency, email, callback_url, metadata) -> InitResult:
        from app.models import MockProviderRecord

        provider_ref = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
        with _session() as db:
            now = utcnow()
            db.add(
                MockProviderRecord(
                    kind="payment",
                    reference=reference,
                    status="pending",
                    amount=amount,
                    data={"provider_reference": provider_ref, "currency": currency, "email": email,
                          "callback_url": callback_url, "metadata": metadata},
                    created_at=now,
                    updated_at=now,
                )
            )
            db.commit()
        # Relative URL: the mock "hosted page" is part of the frontend itself, on whatever origin the buyer uses.
        url = f"/dev/mock-checkout?reference={reference}"
        return InitResult(authorization_url=url, provider_reference=provider_ref)

    def verify(self, reference: str) -> VerifyResult:
        with _session() as db:
            rec = _get(db, "payment", reference)
            if not rec:
                return VerifyResult(reference=reference, status="failed", amount=Decimal("0"), currency="NGN")
            return VerifyResult(
                reference=reference,
                status={"pending": "pending", "success": "success", "failed": "failed"}.get(rec.status, "failed"),
                amount=Decimal(rec.data.get("paid_amount", rec.amount)),
                currency=rec.data.get("currency", "NGN"),
                provider_reference=rec.data.get("provider_reference"),
                channel=rec.data.get("channel", "card"),
                raw={"mock": True},
            )

    def refund(self, *, reference, amount, reason) -> RefundResult:
        from app.models import MockProviderRecord

        ref = f"MOCKRF-{uuid.uuid4().hex[:10].upper()}"
        with _session() as db:
            now = utcnow()
            db.add(MockProviderRecord(kind="refund", reference=ref, status="completed", amount=amount,
                                      data={"payment_reference": reference, "reason": reason},
                                      created_at=now, updated_at=now))
            db.commit()
        return RefundResult(provider_refund_ref=ref, status="completed")

    def verify_webhook_signature(self, body: bytes, headers: dict[str, str]) -> bool:
        sig = headers.get(SIGNATURE_HEADER, "")
        return bool(sig) and hmac.compare_digest(sig, sign(body))

    def parse_webhook(self, payload: dict) -> WebhookEventData:
        data = payload.get("data", {})
        return WebhookEventData(
            event_key=str(payload.get("id")),
            event_type=payload.get("event", "unknown"),
            reference=data.get("reference"),
            raw=payload,
        )

    # ---- dev-only simulation helpers (used by the /dev router and tests) ----
    @staticmethod
    def simulate_outcome(reference: str, outcome: str, paid_amount: Decimal | None = None) -> tuple[bytes, dict]:
        """Mark the mock transaction paid/failed and return a signed webhook (body, headers)."""
        with _session() as db:
            rec = _get(db, "payment", reference)
            if not rec:
                raise ValueError("unknown reference")
            rec.status = "success" if outcome == "success" else "failed"
            data = dict(rec.data)
            if paid_amount is not None:
                data["paid_amount"] = str(paid_amount)
            rec.data = data
            rec.updated_at = utcnow()
            db.commit()
            amount = paid_amount if paid_amount is not None else rec.amount
        payload = {
            "id": f"evt_{uuid.uuid4().hex}",
            "event": "charge.success" if outcome == "success" else "charge.failed",
            "data": {"reference": reference, "amount": str(amount), "currency": "NGN"},
        }
        body = json.dumps(payload).encode()
        return body, {SIGNATURE_HEADER: sign(body)}
