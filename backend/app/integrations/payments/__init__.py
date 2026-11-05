from functools import lru_cache

from app.core.config import settings
from app.integrations.payments.base import PaymentProvider


@lru_cache
def _build(name: str) -> PaymentProvider:
    if name == "mock":
        from app.integrations.payments.mock import MockPaymentProvider

        return MockPaymentProvider()
    if name == "paystack":
        from app.integrations.payments.paystack import PaystackProvider

        return PaystackProvider()
    if name == "flutterwave":
        from app.integrations.payments.flutterwave import FlutterwaveProvider

        return FlutterwaveProvider()
    raise RuntimeError(f"Unknown payment provider {name}")


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    """Active provider for new payments, or a named provider (for webhooks / verifying old payments)."""
    return _build(name or settings.payment_provider)
