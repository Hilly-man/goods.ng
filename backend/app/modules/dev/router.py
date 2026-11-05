"""DEVELOPMENT/TEST ONLY routes. Mounted only when ENVIRONMENT is development or test.

Simulates the payer's actions on the mock provider's hosted checkout page. The resulting webhook is
HMAC-signed and processed through the exact same signature-check + server-verification path used
for real providers.
"""

from decimal import Decimal
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.deps import DB
from app.core.errors import NotFound
from app.integrations.payments.mock import MockPaymentProvider
from app.models import MockProviderRecord, Payment
from app.modules.payments import service

router = APIRouter(prefix="/dev/mock-provider", tags=["dev (mock providers)"])


class SimulateIn(BaseModel):
    outcome: Literal["success", "failed"] = "success"
    paid_amount: Decimal | None = None  # lets tests simulate tampered/partial payments


@router.get("/payments/{reference}")
def mock_payment_page(reference: str, db: DB):
    rec = db.query(MockProviderRecord).filter_by(kind="payment", reference=reference).one_or_none()
    p = db.query(Payment).filter_by(reference=reference).one_or_none()
    if not rec or not p:
        raise NotFound("Unknown mock payment")
    return {"reference": reference, "amount": f"{rec.amount:.2f}", "status": rec.status, "purpose": p.purpose,
            "callback_url": rec.data.get("callback_url"), "notice": "MOCK PROVIDER — no real money moves"}


@router.post("/payments/{reference}/simulate")
def simulate(reference: str, data: SimulateIn, db: DB):
    try:
        body, headers = MockPaymentProvider.simulate_outcome(reference, data.outcome, data.paid_amount)
    except ValueError as e:
        raise NotFound("Unknown mock payment") from e
    result = service.handle_webhook(db, "mock", body, headers)
    p = db.query(Payment).filter_by(reference=reference).one()
    db.refresh(p)
    return {"webhook": result, "payment_status": p.status}
