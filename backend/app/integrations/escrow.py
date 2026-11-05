"""Escrow partner interface.

Goods.ng does NOT hold customer funds itself. Funds collected through Protected Checkout are held
by a licensed escrow/payment partner; Goods.ng instructs the partner to release or refund based on
the order state machine. Our ledger mirrors (does not replace) the partner's books.

Only a MOCK partner exists today (development/testing). A licensed partner adapter must be added and
approved before live protected transactions are enabled; production boot refuses the mock.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from typing import Protocol

from app.core.config import settings
from app.core.time import utcnow


@dataclass
class EscrowResult:
    reference: str
    status: str  # held | released | refunded | failed


class EscrowProvider(Protocol):
    name: str

    def create_hold(self, *, order_reference: str, payment_reference: str, amount: Decimal) -> EscrowResult: ...

    def release(self, *, escrow_reference: str, seller_amount: Decimal, platform_amount: Decimal, seller_ref: str) -> EscrowResult: ...

    def refund(self, *, escrow_reference: str, amount: Decimal, reason: str) -> EscrowResult: ...


class MockEscrowProvider:
    """DEVELOPMENT/TEST ONLY."""

    name = "mock"

    def _write(self, kind, reference, status, amount, data):
        from app.core.db import SessionLocal
        from app.models import MockProviderRecord

        with SessionLocal() as db:
            rec = db.query(MockProviderRecord).filter_by(kind=kind, reference=reference).one_or_none()
            now = utcnow()
            if rec:
                rec.status, rec.updated_at = status, now
                rec.data = {**rec.data, **data}
            else:
                db.add(MockProviderRecord(kind=kind, reference=reference, status=status, amount=amount, data=data,
                                          created_at=now, updated_at=now))
            db.commit()

    def create_hold(self, *, order_reference, payment_reference, amount):
        ref = f"MOCKESC-{uuid.uuid4().hex[:12].upper()}"
        self._write("escrow", ref, "held", amount, {"order": order_reference, "payment": payment_reference})
        return EscrowResult(reference=ref, status="held")

    def release(self, *, escrow_reference, seller_amount, platform_amount, seller_ref):
        self._write("escrow", escrow_reference, "released", seller_amount + platform_amount,
                    {"seller_amount": str(seller_amount), "platform_amount": str(platform_amount), "seller": seller_ref})
        return EscrowResult(reference=escrow_reference, status="released")

    def refund(self, *, escrow_reference, amount, reason):
        self._write("escrow", escrow_reference, "refunded", amount, {"refund_reason": reason})
        return EscrowResult(reference=escrow_reference, status="refunded")


@lru_cache
def get_escrow_provider() -> EscrowProvider:
    if settings.escrow_provider == "mock":
        return MockEscrowProvider()
    raise RuntimeError("No licensed escrow partner configured")
