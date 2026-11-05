"""Provider-neutral payment interface.

Business logic depends only on this interface. Each licensed provider (Paystack, Flutterwave, ...)
implements it in its own module; the active provider is chosen by configuration.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


@dataclass
class InitResult:
    authorization_url: str
    provider_reference: str
    raw: dict = field(default_factory=dict)


@dataclass
class VerifyResult:
    """Normalised result of asking the provider (server-to-server) about a transaction."""

    reference: str
    status: str  # "success" | "failed" | "abandoned" | "pending"
    amount: Decimal
    currency: str
    provider_reference: str | None = None
    channel: str | None = None
    raw: dict = field(default_factory=dict)


@dataclass
class RefundResult:
    provider_refund_ref: str
    status: str  # "processing" | "completed" | "failed"
    raw: dict = field(default_factory=dict)


@dataclass
class WebhookEventData:
    event_key: str  # unique per provider event, used for idempotency
    event_type: str
    reference: str | None
    raw: dict


class PaymentProvider(Protocol):
    name: str

    def initialize(
        self, *, reference: str, amount: Decimal, currency: str, email: str, callback_url: str, metadata: dict
    ) -> InitResult: ...

    def verify(self, reference: str) -> VerifyResult: ...

    def refund(self, *, reference: str, amount: Decimal, reason: str) -> RefundResult: ...

    def verify_webhook_signature(self, body: bytes, headers: dict[str, str]) -> bool: ...

    def parse_webhook(self, payload: dict) -> WebhookEventData: ...
