"""Goods Flex financing-partner interface.

Goods.ng does not lend. Credit decisions, financing charges and repayment terms come from a licensed
lending partner and are shown to the buyer verbatim before acceptance. Goods.ng stores the partner's
decision reference and the exact accepted terms for audit.

Only a MOCK partner exists today. Its pricing (30% down payment, 3.5% flat monthly charge) and
affordability rule are ILLUSTRATIVE PLACEHOLDERS for development, not real credit terms.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Protocol

from app.core.config import settings

CENT = Decimal("0.01")


def q(v: Decimal) -> Decimal:
    return v.quantize(CENT, rounding=ROUND_HALF_UP)


def add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    import calendar

    year, month = d.year + y, m + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


@dataclass
class FinancingOption:
    tenor_months: int
    down_payment: Decimal
    financed_amount: Decimal
    financing_charge: Decimal
    total_payable: Decimal
    monthly_installment: Decimal
    schedule: list[dict] = field(default_factory=list)  # [{sequence, due_date, amount}]
    apr_disclosure: str = ""

    def as_dict(self) -> dict:
        return {
            "tenor_months": self.tenor_months,
            "down_payment": str(self.down_payment),
            "financed_amount": str(self.financed_amount),
            "financing_charge": str(self.financing_charge),
            "total_payable": str(self.total_payable),
            "monthly_installment": str(self.monthly_installment),
            "schedule": self.schedule,
            "apr_disclosure": self.apr_disclosure,
        }


@dataclass
class CreditDecision:
    approved: bool
    application_ref: str
    decision_ref: str
    option: FinancingOption | None
    reason: str | None = None


class FinancingProvider(Protocol):
    name: str
    min_amount: Decimal
    max_amount: Decimal
    tenors: tuple[int, ...]

    def quote(self, amount: Decimal, start: date) -> list[FinancingOption]: ...

    def apply(self, *, applicant: dict, amount: Decimal, tenor_months: int, start: date) -> CreditDecision: ...

    def accept(self, *, application_ref: str) -> str: ...  # returns agreement ref

    def cancel(self, *, application_ref: str, reason: str) -> None: ...


class MockFinancingProvider:
    """DEVELOPMENT/TEST ONLY. Illustrative terms; not a real credit product."""

    name = "mock"
    min_amount = Decimal("20000")
    max_amount = Decimal("3000000")
    tenors = (3, 6)
    down_rate = Decimal("0.30")
    monthly_charge_rate = Decimal("0.035")

    def _option(self, amount: Decimal, tenor: int, start: date) -> FinancingOption:
        down = q(amount * self.down_rate)
        financed = amount - down
        charge = q(financed * self.monthly_charge_rate * tenor)
        repay = financed + charge
        monthly = q(repay / tenor)
        schedule, remaining = [], repay
        for i in range(1, tenor + 1):
            amt = monthly if i < tenor else remaining
            remaining -= amt
            schedule.append({"sequence": i, "due_date": add_months(start, i).isoformat(), "amount": str(amt)})
        return FinancingOption(
            tenor_months=tenor, down_payment=down, financed_amount=financed, financing_charge=charge,
            total_payable=down + financed + charge, monthly_installment=monthly, schedule=schedule,
            apr_disclosure="ILLUSTRATIVE mock terms (3.5% flat per month). Real terms come from the lending partner.",
        )

    def quote(self, amount, start):
        if amount < self.min_amount or amount > self.max_amount:
            return []
        return [self._option(amount, t, start) for t in self.tenors]

    def apply(self, *, applicant, amount, tenor_months, start):
        app_ref = f"MOCKAPP-{uuid.uuid4().hex[:10].upper()}"
        decision_ref = f"MOCKDEC-{uuid.uuid4().hex[:10].upper()}"
        if tenor_months not in self.tenors:
            return CreditDecision(False, app_ref, decision_ref, None, "Unsupported tenor")
        if not (self.min_amount <= amount <= self.max_amount):
            return CreditDecision(False, app_ref, decision_ref, None, "Amount outside financing limits")
        if not applicant.get("phone_verified"):
            return CreditDecision(False, app_ref, decision_ref, None, "A verified phone number is required")
        option = self._option(amount, tenor_months, start)
        income = Decimal(str(applicant.get("monthly_income") or 0))
        # Affordability: instalment must not exceed one third of declared monthly income.
        if income <= 0 or option.monthly_installment > q(income / 3):
            return CreditDecision(False, app_ref, decision_ref, None,
                                  "Instalment exceeds affordability limit for declared income")
        return CreditDecision(True, app_ref, decision_ref, option)

    def accept(self, *, application_ref):
        return f"MOCKAGR-{uuid.uuid4().hex[:10].upper()}"

    def cancel(self, *, application_ref, reason):
        return None


@lru_cache
def get_financing_provider() -> FinancingProvider:
    if settings.bnpl_provider == "mock":
        return MockFinancingProvider()
    raise RuntimeError("No licensed financing partner configured")
