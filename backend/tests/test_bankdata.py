"""Unit tests for the Mono open-banking adapter (no network; mocked HTTP transport)."""

from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.core.errors import ProviderError
from app.integrations.bankdata import MonoBankDataProvider


def provider(handler):
    return MonoBankDataProvider(secret_key="test_sk_123", base_url="https://api.withmono.test",
                                transport=httpx.MockTransport(handler))


def test_exchange_code_returns_account_details():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["mono-sec-key"] == "test_sk_123"
        if request.url.path == "/v2/accounts/auth":
            assert request.method == "POST"
            assert b'"code":"code_abc"' in request.content
            return httpx.Response(200, json={"status": "successful", "data": {"id": "acct_1"}})
        assert request.url.path == "/v2/accounts/acct_1"
        return httpx.Response(200, json={"status": "successful", "data": {
            "account": {"name": "ADA LOVELACE", "accountNumber": "0123456789",
                        "institution": {"name": "GTBank"}}}})

    acct = provider(handler).exchange_code("code_abc", account_name="ignored")
    assert acct.provider_account_ref == "acct_1"
    assert acct.account_name == "ADA LOVELACE"
    assert acct.bank_name == "GTBank"
    assert acct.account_number_last4 == "6789"


def test_transactions_are_converted_from_kobo():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/accounts/acct_1/transactions"
        assert request.url.params["paginate"] == "false"
        return httpx.Response(200, json={"status": "successful", "data": [
            {"date": "2026-01-25T10:00:00.000Z", "amount": 45_000_000, "type": "credit",
             "narration": "SALARY JAN", "balance": 50_000_000},
            {"date": "2026-01-02T10:00:00.000Z", "amount": 1_500_000, "type": "debit",
             "narration": "POS PURCHASE", "balance": None},
            {"date": "not-a-date", "amount": 100, "type": "debit", "narration": "BAD ROW"},
        ]})

    rows = provider(handler).transactions("acct_1", months=6)
    assert len(rows) == 2  # rows with an unparseable date are skipped
    assert rows[0].type == "credit" and rows[0].amount == Decimal("450000.00")
    assert rows[0].date == date(2026, 1, 25) and rows[0].balance == Decimal("500000.00")
    assert rows[1].type == "debit" and rows[1].amount == Decimal("15000.00") and rows[1].balance is None


def test_provider_errors_are_mapped():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"status": "failed", "message": "Invalid key"})

    with pytest.raises(ProviderError):
        provider(handler).exchange_code("bad", account_name="x")


def test_unreachable_provider_is_mapped():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(ProviderError):
        provider(handler).exchange_code("bad", account_name="x")
