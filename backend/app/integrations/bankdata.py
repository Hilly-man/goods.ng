"""Open-banking provider interface: link a bank account and fetch its transaction history.

Real adapters (e.g. Mono Connect) return a one-time code from their widget, which the backend exchanges
for an account id and then pulls transactions server-to-server. Only a MOCK exists today; it generates a
realistic, deterministic 6-month statement for a chosen test persona.
"""

import hashlib
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import settings
from app.core.errors import AppError, ProviderError
from app.modules.bnpl.credit import Txn


@dataclass
class LinkedAccount:
    provider_account_ref: str
    bank_name: str
    account_name: str
    account_number_last4: str


class BankDataProvider(Protocol):
    name: str

    def exchange_code(self, code: str, *, account_name: str) -> LinkedAccount: ...

    def transactions(self, account_ref: str, *, months: int = 6) -> list[Txn]: ...


PERSONAS = {
    "salary_earner": "Salaried worker — ₦450k salary, small existing loan",
    "high_earner": "High earner — ₦1.2M salary, no other loans",
    "trader": "Market trader — irregular business inflows",
    "low_income": "Low income — ₦70k salary",
    "risky": "Risky — ₦300k salary, heavy betting, failed debits, several loans",
}
BANKS = ["GTBank", "Access Bank", "Zenith Bank", "First Bank", "UBA", "Kuda", "Opay", "Moniepoint"]


def _month_starts(today: date, months: int) -> list[date]:
    first = today.replace(day=1)
    out = []
    for i in range(months, -1, -1):
        y, m = divmod(first.month - 1 - i, 12)
        out.append(date(first.year + y, m + 1, 1))
    return out


def generate_statement(persona: str, seed: str, today: date | None = None, months: int = 6) -> list[Txn]:
    """Deterministic synthetic statement covering `months` full months plus the current partial month."""
    rnd = random.Random(int(hashlib.sha256(f"{persona}:{seed}".encode()).hexdigest(), 16) % 2**32)
    today = today or date.today()
    txns: list[Txn] = []
    D = Decimal

    def add(d, amt, typ, narr):
        txns.append(Txn(date=d, amount=D(str(round(amt, -2))), type=typ, narration=narr))

    for start in _month_starts(today, months):
        last_day = ((start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)).day
        day = lambda d, s=start, ld=last_day: s.replace(day=min(d, ld))  # noqa: E731
        if start > today:
            continue
        if persona in ("salary_earner", "high_earner", "low_income", "risky"):
            salary = {"salary_earner": 450_000, "high_earner": 1_200_000, "low_income": 70_000, "risky": 300_000}[persona]
            add(day(25), salary, "credit", f"SALARY {start:%b %Y} ACME NIGERIA LTD")
            add(day(rnd.randint(5, 20)), rnd.choice([5_000, 10_000, 15_000]), "credit", "TRF FROM CHIOMA OKAFOR")
        if persona == "trader":
            for _ in range(rnd.randint(8, 14)):
                add(day(rnd.randint(1, 28)), rnd.randint(15_000, 90_000), "credit", "POS SETTLEMENT MONIEPOINT")
        spend = {"salary_earner": 0.55, "high_earner": 0.45, "low_income": 0.8, "risky": 0.5, "trader": 0.6}[persona]
        base = {"salary_earner": 450_000, "high_earner": 1_200_000, "low_income": 70_000, "risky": 300_000, "trader": 520_000}[persona]
        for narr in ("POS PURCHASE SHOPRITE", "AIRTIME MTN", "IKEDC PREPAID", "TRF TO LANDLORD", "UBER TRIP", "DSTV SUBSCRIPTION"):
            add(day(rnd.randint(1, 28)), base * spend / 6 * rnd.uniform(0.7, 1.3), "debit", narr)
        if persona == "salary_earner":
            add(day(27), 20_000, "debit", "CARBON LOAN REPAYMENT")
        if persona == "risky":
            for _ in range(4):
                add(day(rnd.randint(1, 28)), rnd.randint(20_000, 45_000), "debit", "SPORTYBET WALLET FUNDING")
            add(day(3), 40_000, "debit", "FAIRMONEY LOAN REPAYMENT")
            add(day(10), 40_000, "debit", "PALMCREDIT LOAN REPAY")
            add(day(12), 50_000, "credit", "FAIRMONEY LOAN DISB")
            if rnd.random() < 0.6:
                add(day(28), 1, "debit", "DD RETURNED - INSUFFICIENT FUNDS")
    balance = Decimal(rnd.randint(20_000, 200_000))
    txns.sort(key=lambda t: t.date)
    for t in txns:
        balance += t.amount if t.type == "credit" else -t.amount
        t.balance = balance
    return [t for t in txns if t.date <= today]


class MockBankDataProvider:
    """DEVELOPMENT/TEST ONLY. Codes look like "mock:<persona>:<bank>"."""

    name = "mock"

    def exchange_code(self, code, *, account_name):
        parts = code.split(":")
        if len(parts) < 2 or parts[0] != "mock" or parts[1] not in PERSONAS:
            raise AppError("Bank connection failed. Please try again.", code="bank_link_failed")
        bank = parts[2] if len(parts) > 2 and parts[2] in BANKS else "GTBank"
        digest = hashlib.sha256(code.encode()).hexdigest()
        return LinkedAccount(provider_account_ref=f"mockacct_{parts[1]}_{digest[:10]}", bank_name=bank,
                             account_name=account_name, account_number_last4=str(int(digest[:6], 16))[-4:].rjust(4, "0"))

    def transactions(self, account_ref, *, months=6):
        persona = "_".join(account_ref.split("_")[1:-1]) if account_ref.startswith("mockacct_") else "salary_earner"
        return generate_statement(persona, account_ref, months=months)


class MonoBankDataProvider:
    """Mono Connect open-banking adapter.

    STATUS: implemented against Mono's public v2 API documentation; NOT yet verified against a Mono
    test account. Run it in staging with a `test_sk_` key before enabling it in production.
    Transactions are returned in kobo and converted to naira.
    """

    name = "mono"

    def __init__(self, secret_key: str | None = None, base_url: str | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.secret = secret_key or settings.mono_secret_key
        if not self.secret:
            raise RuntimeError("MONO_SECRET_KEY is not configured")
        self.base_url = base_url or settings.mono_base_url
        self.transport = transport

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=20, transport=self.transport,
                            headers={"mono-sec-key": self.secret, "accept": "application/json"})

    def _call(self, method: str, path: str, **kw) -> dict | list:
        try:
            with self._client() as c:
                r = c.request(method, path, **kw)
        except httpx.HTTPError as e:
            raise ProviderError("Bank data provider unreachable") from e
        body = r.json() if r.content else {}
        if r.status_code >= 400 or (isinstance(body, dict) and body.get("status") not in (None, "successful")):
            message = body.get("message") if isinstance(body, dict) else None
            raise ProviderError(message or "Bank data provider error", details={"provider": "mono"})
        return body.get("data", body) if isinstance(body, dict) else body

    def exchange_code(self, code, *, account_name):
        auth = self._call("POST", "/v2/accounts/auth", json={"code": code})
        account_id = auth["id"] if isinstance(auth, dict) else auth
        details = self._call("GET", f"/v2/accounts/{account_id}")
        account = details.get("account", details) if isinstance(details, dict) else {}
        institution = account.get("institution")
        bank = institution.get("name") if isinstance(institution, dict) else (institution or "Unknown bank")
        number = str(account.get("accountNumber") or "")
        return LinkedAccount(provider_account_ref=str(account_id), bank_name=str(bank),
                             account_name=account.get("name") or account_name,
                             account_number_last4=number[-4:].rjust(4, "0"))

    def transactions(self, account_ref, *, months=6):
        end = date.today()
        start = end - timedelta(days=months * 31)
        data = self._call("GET", f"/v2/accounts/{account_ref}/transactions",
                          params={"start": start.isoformat(), "end": end.isoformat(), "paginate": "false"})
        rows = data if isinstance(data, list) else data.get("transactions", data.get("data", []))
        out: list[Txn] = []
        for row in rows:
            raw_date = str(row.get("date") or "")[:10]
            try:
                on = date.fromisoformat(raw_date)
            except ValueError:
                continue
            amount = Decimal(str(row.get("amount") or 0)) / 100
            balance = row.get("balance")
            out.append(Txn(on, abs(amount), "credit" if str(row.get("type", "")).lower() == "credit" else "debit",
                           str(row.get("narration") or ""),
                           Decimal(str(balance)) / 100 if balance is not None else None))
        return out


@lru_cache
def get_bank_data_provider() -> BankDataProvider:
    if settings.bank_data_provider == "mono":
        return MonoBankDataProvider()
    if settings.bank_data_provider == "mock" and settings.environment in ("development", "test"):
        return MockBankDataProvider()
    if settings.environment in ("development", "test") or settings.payment_provider == "mock":
        return MockBankDataProvider()
    raise RuntimeError("No open-banking provider configured")
