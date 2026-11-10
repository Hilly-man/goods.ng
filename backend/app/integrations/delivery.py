"""Delivery/carrier partner interface.

Carrier integrations confirm dispatch and delivery independently of the seller. A provider
implements this protocol; manual couriers fall back to the buyer-only delivery PIN. Only a MOCK
provider exists today; a real adapter (Shipbubble, GIG, Fez, ...) can be added without changing
order logic.
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings


@dataclass
class ShipmentResult:
    reference: str
    status: str  # created | in_transit | delivered | failed
    tracking_url: str | None = None
    raw: dict | None = None


@dataclass
class DeliveryEvent:
    event_key: str
    order_reference: str
    status: str  # in_transit | delivered | failed
    raw: dict | None = None


class DeliveryProvider:
    name: str

    def create_shipment(self, *, order_reference: str, carrier: str | None,
                        tracking_reference: str | None) -> ShipmentResult: ...
    def parse_webhook(self, payload: dict) -> DeliveryEvent: ...


class MockDeliveryProvider(DeliveryProvider):
    """DEVELOPMENT/TEST ONLY. No carrier is called."""

    name = "mock"

    def create_shipment(self, *, order_reference, carrier, tracking_reference):
        ref = f"MOCKSHIP-{uuid.uuid4().hex[:10].upper()}"
        return ShipmentResult(reference=ref, status="created",
                              tracking_url=f"https://mock-delivery.local/track/{ref}",
                              raw={"order": order_reference, "carrier": carrier})

    def parse_webhook(self, payload):
        return DeliveryEvent(
            event_key=str(payload.get("event_key") or uuid.uuid4()),
            order_reference=str(payload["order_reference"]),
            status=str(payload.get("status", "delivered")),
            raw=payload,
        )


@lru_cache
def get_delivery_provider() -> DeliveryProvider:
    if settings.delivery_provider == "mock":
        return MockDeliveryProvider()
    raise RuntimeError("No delivery partner configured")
