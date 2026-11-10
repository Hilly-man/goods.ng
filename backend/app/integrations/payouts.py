"""Seller payout partner interface.

Goods.ng does not hold or move customer money itself. Approved seller withdrawals are executed by a
licensed payout partner (bank transfer / PSSP). Each partner implements this protocol; the ledger is
updated only from the partner's confirmed result, and retries are idempotent by payout reference.

Only a MOCK partner exists today (development/testing). Production boot refuses the mock.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache

from app.core.config import settings


@dataclass
class ResolvedAccount:
    account_name: str


@dataclass
class TransferResult:
    reference: str
    status: str  # paid | processing | failed
    raw: dict | None = None


class PayoutProvider:
    name: str

    def resolve_account(self, *, bank_code: str, account_number: str) -> ResolvedAccount: ...
    def create_transfer(self, *, reference: str, amount: Decimal, bank_code: str, account_number: str,
                        account_name: str) -> TransferResult: ...
    def get_transfer(self, *, reference: str) -> TransferResult: ...


class MockPayoutProvider(PayoutProvider):
    """DEVELOPMENT/TEST ONLY. Records the transfer locally; no money moves."""

    name = "mock"

    def _write(self, reference, status, amount, data):
        from app.core.db import SessionLocal
        from app.core.time import utcnow
        from app.models import MockProviderRecord

        with SessionLocal() as db:
            rec = db.query(MockProviderRecord).filter_by(kind="payout", reference=reference).one_or_none()
            now = utcnow()
            if rec:
                rec.status, rec.updated_at = status, now
                rec.data = {**rec.data, **data}
            else:
                db.add(MockProviderRecord(kind="payout", reference=reference, status=status, amount=amount,
                                          data=data, created_at=now, updated_at=now))
            db.commit()

    def resolve_account(self, *, bank_code, account_number):
        return ResolvedAccount(account_name=f"MOCK ACCOUNT {account_number[-4:]}")

    def create_transfer(self, *, reference, amount, bank_code, account_number, account_name):
        ref = f"MOCKPAY-{uuid.uuid4().hex[:12].upper()}"
        self._write(ref, "paid", amount, {"requested_reference": reference, "bank_code": bank_code,
                                          "account_last4": account_number[-4:], "account_name": account_name})
        return TransferResult(reference=ref, status="paid")

    def get_transfer(self, *, reference):
        return TransferResult(reference=reference, status="paid")


@lru_cache
def get_payout_provider() -> PayoutProvider:
    if settings.payout_provider == "mock":
        return MockPayoutProvider()
    raise RuntimeError("No licensed payout partner configured")
