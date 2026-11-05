"""Goods Flex credit engine: turns 6 months of bank transactions into an affordability-based credit limit.

Pure functions (no DB, no I/O) so the rules are easy to test, audit and explain to customers.

Method
------
1. Classify every transaction by its narration (salary, loan disbursement/repayment, reversal, gambling,
   failed debit). Loan disbursements and reversals are not income.
2. Per calendar month: eligible inflow = all credits − loan disbursements − reversals − self transfers.
3. Income:
   * salary detected (salary keywords in ≥3 months, or a regular credit of similar size each month)
     → monthly income = median salary amount;
   * otherwise → 70% of the median eligible monthly inflow (haircut for irregular income).
4. Risk factor (0.25–1.0) from income stability (coefficient of variation), months with income,
   gambling share and failed debits.
5. Affordable instalment = (income × max debt-to-income − existing loan repayments) × risk factor.
6. Statement limit = the purchase price whose instalment (after the down payment and financing charge,
   at the longest tenor) fits the affordable instalment.
The final limit applies further caps (verification tier, repayment history, lender maximum) in flex.py.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from decimal import ROUND_DOWN, Decimal

ENGINE_VERSION = "flex-credit-1.0"

LENDER_KEYWORDS = ("CARBON", "FAIRMONEY", "PALMCREDIT", "BRANCH", "RENMONEY", "AELLA", "QUICKCHECK", "EASYBUY",
                   "LOAN DISB", "LOAN REPAY", "LOAN-REPAY", "LOAN RPMT")
GAMBLING_KEYWORDS = ("BET9JA", "SPORTYBET", "NAIRABET", "BETKING", "1XBET", "MSPORT", "MERRYBET", "BETWAY")
SALARY_KEYWORDS = ("SALARY", "SAL/", " SAL ", "PAYROLL", "WAGES")
REVERSAL_KEYWORDS = ("REVERSAL", "REV/", "REFUND")
SELF_KEYWORDS = ("OWN ACCOUNT", "SELF TRANSFER", "TRF TO SELF")
FAILED_DEBIT_KEYWORDS = ("INSUFFICIENT", "RETURNED", "DD FAILED", "UNPAID")


@dataclass
class Txn:
    date: date
    amount: Decimal  # always positive
    type: str  # "credit" | "debit"
    narration: str
    balance: Decimal | None = None


@dataclass
class Policy:
    max_dti: Decimal = Decimal("0.33")          # instalments + existing loans ≤ 33% of income
    down_payment_rate: Decimal = Decimal("0.30")
    monthly_charge_rate: Decimal = Decimal("0.035")
    max_tenor_months: int = 6
    irregular_income_haircut: Decimal = Decimal("0.70")
    min_months: int = 3                          # need at least 3 full months of data


@dataclass
class Assessment:
    months_analysed: int
    monthly_income: Decimal
    income_source: str  # salary | business_inflows | none
    salary_detected: bool
    monthly_inflows: list[dict] = field(default_factory=list)  # [{month, eligible_inflow, salary}]
    monthly_loan_repayments: Decimal = Decimal("0")
    gambling_ratio: Decimal = Decimal("0")
    failed_debits: int = 0
    income_cv: Decimal = Decimal("0")
    avg_month_end_balance: Decimal | None = None
    risk_factor: Decimal = Decimal("0")
    affordable_instalment: Decimal = Decimal("0")
    statement_limit: Decimal = Decimal("0")
    score: int = 0
    reasons: list[str] = field(default_factory=list)

    def as_json(self) -> dict:
        d = asdict(self)
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


def classify(t: Txn) -> str:
    n = f" {t.narration.upper()} "
    if any(k in n for k in FAILED_DEBIT_KEYWORDS):
        return "failed_debit"
    if t.type == "credit":
        if any(k in n for k in REVERSAL_KEYWORDS):
            return "reversal"
        if any(k in n for k in SELF_KEYWORDS):
            return "self"
        if any(k in n for k in LENDER_KEYWORDS):
            return "loan_in"
        if any(k in n for k in SALARY_KEYWORDS):
            return "salary"
        return "credit"
    if any(k in n for k in LENDER_KEYWORDS):
        return "loan_out"
    if any(k in n for k in GAMBLING_KEYWORDS):
        return "gambling"
    return "debit"


def _q(v: Decimal, step: str = "0.01") -> Decimal:
    return v.quantize(Decimal(step), rounding=ROUND_DOWN)


def _full_months(txns: list[Txn]) -> list[tuple[int, int]]:
    """Calendar months fully covered by the data (drop the partial first and last month)."""
    if not txns:
        return []
    months = sorted({(t.date.year, t.date.month) for t in txns})
    first, last = min(t.date for t in txns), max(t.date for t in txns)
    if first.day > 3:
        months = months[1:]
    if months and (last.year, last.month) == months[-1] and last.day < 25:
        months = months[:-1]
    return months[-6:]


def _regular_credit(by_month: dict, months: list) -> Decimal | None:
    """A dominant credit of similar size (±10%) in ≥3 months → likely salary even without keywords.

    "Dominant" (≥40% of that month's inflows) stops a trader's many similar-sized POS settlements
    from being mistaken for a salary.
    """
    vals = []
    for m in months:
        credits = [t.amount for t in by_month[m] if classify(t) in ("credit", "salary")]
        if not credits:
            continue
        top, total = max(credits), sum(credits, Decimal("0"))
        if total > 0 and top / total >= Decimal("0.40"):
            vals.append(top)
    if len(vals) < 3:
        return None
    med = statistics.median(vals)
    similar = [v for v in vals if abs(v - med) <= med * Decimal("0.10")]
    return Decimal(statistics.median(similar)) if len(similar) >= 3 else None


def assess(txns: list[Txn], policy: Policy | None = None) -> Assessment:
    p = policy or Policy()
    months = _full_months(txns)
    by_month: dict = defaultdict(list)
    for t in txns:
        by_month[(t.date.year, t.date.month)].append(t)

    if len(months) < p.min_months:
        return Assessment(months_analysed=len(months), monthly_income=Decimal("0"), income_source="none",
                          salary_detected=False, reasons=[f"At least {p.min_months} full months of bank history are needed"])

    rows, eligible, salaries, loan_out, gambling, failed, balances = [], [], [], [], Decimal("0"), 0, []
    for m in months:
        mt = by_month[m]
        kinds = [(classify(t), t) for t in mt]
        inflow = sum((t.amount for k, t in kinds if k in ("credit", "salary")), Decimal("0"))
        sal = sum((t.amount for k, t in kinds if k == "salary"), Decimal("0"))
        loan_out.append(sum((t.amount for k, t in kinds if k == "loan_out"), Decimal("0")))
        gambling += sum((t.amount for k, t in kinds if k == "gambling"), Decimal("0"))
        failed += sum(1 for k, _ in kinds if k == "failed_debit")
        dated = [t for t in mt if t.balance is not None]
        if dated:
            balances.append(max(dated, key=lambda t: t.date).balance)
        eligible.append(inflow)
        if sal:
            salaries.append(sal)
        rows.append({"month": f"{m[0]}-{m[1]:02d}", "eligible_inflow": str(_q(inflow)), "salary": str(_q(sal))})

    reasons: list[str] = []
    regular = _regular_credit(by_month, months)
    salary_detected = len(salaries) >= 3 or regular is not None
    median_inflow = Decimal(statistics.median(eligible))
    if len(salaries) >= 3:
        income, source = Decimal(statistics.median(salaries)), "salary"
    elif regular is not None:
        income, source = regular, "salary"
    elif median_inflow > 0:
        income, source = median_inflow * p.irregular_income_haircut, "business_inflows"
        reasons.append("No regular salary detected — income estimated conservatively from account inflows")
    else:
        income, source = Decimal("0"), "none"
        reasons.append("No qualifying income found in the statement")

    mean = sum(eligible, Decimal("0")) / len(eligible)
    cv = Decimal(str(statistics.pstdev([float(x) for x in eligible]) / float(mean))) if mean > 0 else Decimal("1")
    months_with_income = sum(1 for x in eligible if x > 0)
    debt = sum(loan_out, Decimal("0")) / len(loan_out)
    total_in = sum(eligible, Decimal("0"))
    gambling_ratio = gambling / total_in if total_in > 0 else Decimal("0")

    factor = max(Decimal("0.4"), min(Decimal("1"), Decimal("1") - cv))
    if months_with_income < len(months) - 1:
        factor *= Decimal("0.7")
        reasons.append("Income was missing in some months")
    if gambling_ratio > Decimal("0.20"):
        factor *= Decimal("0.5")
        reasons.append("High share of spending on betting")
    elif gambling_ratio > Decimal("0.10"):
        factor *= Decimal("0.8")
        reasons.append("Noticeable spending on betting")
    if failed >= 2:
        factor *= Decimal("0.6")
        reasons.append(f"{failed} failed or returned debits in the period")
    if debt > 0:
        reasons.append(f"Existing loan repayments of about ₦{debt:,.0f}/month were deducted")
    factor = max(Decimal("0.25"), factor) if income > 0 else Decimal("0")

    affordable = max(Decimal("0"), income * p.max_dti - debt) * factor
    t = p.max_tenor_months
    financed_share = Decimal("1") - p.down_payment_rate
    # instalment = P × financed_share × (1 + rate × T) / T  ≤ affordable  →  solve for purchase price P
    limit = affordable * t / (financed_share * (1 + p.monthly_charge_rate * t)) if affordable > 0 else Decimal("0")
    limit = (limit / 1000).to_integral_value(rounding=ROUND_DOWN) * 1000

    dti_used = (debt / income) if income > 0 else Decimal("1")
    score = int(max(0, min(100, float(factor) * 70 + float(max(Decimal("0"), Decimal("0.33") - dti_used)) * 90)))

    return Assessment(
        months_analysed=len(months), monthly_income=_q(income), income_source=source, salary_detected=salary_detected,
        monthly_inflows=rows, monthly_loan_repayments=_q(debt), gambling_ratio=_q(gambling_ratio, "0.001"),
        failed_debits=failed, income_cv=_q(cv, "0.001"),
        avg_month_end_balance=_q(sum(balances, Decimal("0")) / len(balances)) if balances else None,
        risk_factor=_q(factor, "0.001"), affordable_instalment=_q(affordable), statement_limit=Decimal(limit),
        score=score, reasons=reasons,
    )
