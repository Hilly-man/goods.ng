"""Unit tests for the Goods Flex credit engine (pure maths, no DB)."""

from datetime import date
from decimal import Decimal

from app.modules.bnpl.credit import Policy, Txn, assess, classify

D = Decimal


def months(n=6, year=2026):
    return [(year, m) for m in range(1, n + 1)]


def statement(salary=None, salary_narr="SALARY ACME LTD", inflows=None, debits=(), extra=()):
    """Builds n months of data: day-1 expense, day-25 salary/inflow, day-28 expense (all months fully covered)."""
    txns = []
    for i, (y, m) in enumerate(months()):
        txns.append(Txn(date(y, m, 1), D("10000"), "debit", "POS SHOPRITE"))
        if salary:
            txns.append(Txn(date(y, m, 25), D(salary), "credit", salary_narr))
        if inflows:
            txns.append(Txn(date(y, m, 15), D(inflows[i]), "credit", "TRF FROM CUSTOMER"))
        for amt, narr in debits:
            txns.append(Txn(date(y, m, 20), D(amt), "debit", narr))
        txns.append(Txn(date(y, m, 28), D("5000"), "debit", "AIRTIME MTN"))
    return txns + list(extra)


def test_classifier():
    assert classify(Txn(date(2026, 1, 1), D(1), "credit", "SALARY JAN ACME")) == "salary"
    assert classify(Txn(date(2026, 1, 1), D(1), "credit", "FAIRMONEY LOAN DISB")) == "loan_in"
    assert classify(Txn(date(2026, 1, 1), D(1), "debit", "CARBON LOAN REPAYMENT")) == "loan_out"
    assert classify(Txn(date(2026, 1, 1), D(1), "debit", "SPORTYBET WALLET")) == "gambling"
    assert classify(Txn(date(2026, 1, 1), D(1), "credit", "REVERSAL OF TRF")) == "reversal"
    assert classify(Txn(date(2026, 1, 1), D(1), "debit", "DD RETURNED - INSUFFICIENT FUNDS")) == "failed_debit"


def test_stable_salary_exact_limit():
    a = assess(statement(salary="300000"))
    assert a.months_analysed == 6 and a.salary_detected and a.income_source == "salary"
    assert a.monthly_income == D("300000.00")
    assert a.risk_factor == D("1.000")
    # affordable = 300k × 0.33 = 99,000 → P = 99,000 × 6 / (0.7 × 1.21) = 701,298 → floored to 701,000
    assert a.affordable_instalment == D("99000.00")
    assert a.statement_limit == D("838000")


def test_existing_loans_reduce_limit():
    base = assess(statement(salary="300000"))
    indebted = assess(statement(salary="300000", debits=[("40000", "CARBON LOAN REPAYMENT")]))
    assert indebted.monthly_loan_repayments == D("40000.00")
    assert indebted.affordable_instalment == D("59000.00")  # 99,000 − 40,000
    assert indebted.statement_limit < base.statement_limit


def test_loan_disbursements_and_reversals_are_not_income():
    extra = [Txn(date(2026, m, 10), D("500000"), "credit", "FAIRMONEY LOAN DISB") for m in range(1, 7)]
    extra += [Txn(date(2026, m, 11), D("200000"), "credit", "REVERSAL OF TRANSFER") for m in range(1, 7)]
    a = assess(statement(salary="300000", extra=extra))
    assert a.monthly_income == D("300000.00")
    assert all(row["eligible_inflow"] == "300000.00" for row in a.monthly_inflows)


def test_irregular_income_gets_haircut_and_stability_penalty():
    inflows = ["400000", "600000", "500000", "300000", "700000", "500000"]
    a = assess(statement(inflows=inflows))
    assert a.income_source == "business_inflows" and not a.salary_detected
    assert a.monthly_income == D("350000.00")  # 70% of the 500k median
    assert a.risk_factor < D("1")  # volatility penalty
    assert any("No regular salary" in r for r in a.reasons)


def test_regular_credit_without_keyword_counts_as_salary():
    a = assess(statement(salary="250000", salary_narr="TRF FROM ACME NIG LTD"))
    assert a.salary_detected and a.monthly_income == D("250000.00")


def test_gambling_and_failed_debits_penalised():
    clean = assess(statement(salary="300000"))
    risky = assess(statement(salary="300000", debits=[("80000", "SPORTYBET WALLET FUNDING")],
                             extra=[Txn(date(2026, 3, 28), D("0"), "debit", "DD RETURNED - INSUFFICIENT FUNDS"),
                                    Txn(date(2026, 4, 28), D("0"), "debit", "DD RETURNED - INSUFFICIENT FUNDS")]))
    assert risky.gambling_ratio > D("0.20")
    assert risky.failed_debits == 2
    assert risky.risk_factor == D("0.300")  # 1 × 0.5 (betting) × 0.6 (failed debits)
    assert risky.statement_limit < clean.statement_limit / 3


def test_too_little_history_gives_no_limit():
    txns = [Txn(date(2026, 5, 1), D("1000"), "debit", "POS"), Txn(date(2026, 5, 25), D("300000"), "credit", "SALARY"),
            Txn(date(2026, 6, 28), D("1000"), "debit", "POS")]
    a = assess(txns)
    assert a.statement_limit == 0 and any("3 full months" in r for r in a.reasons)


def test_policy_is_configurable():
    a = assess(statement(salary="300000"), Policy(max_dti=D("0.25")))
    assert a.affordable_instalment == D("75000.00")


def test_many_similar_small_credits_are_not_a_salary():
    # A trader with ten ~₦50k POS settlements a month: the biggest one is similar every month,
    # but it's never the dominant credit, so it must not be read as a salary.
    extra = [Txn(date(2026, m, d), D("50000") + d * 100, "credit", "POS SETTLEMENT MONIEPOINT")
             for m in range(1, 7) for d in range(2, 22, 2)]
    a = assess(statement(extra=extra))
    assert not a.salary_detected and a.income_source == "business_inflows"
