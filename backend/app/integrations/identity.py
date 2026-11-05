"""Identity verification (BVN) provider interface.

Real adapters (e.g. Dojah, Prembly/IdentityPass, Smile ID, Youverify) look up the BVN record held by
NIBSS and return the registered name, phone and date of birth. Only a MOCK exists today.
"""

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Protocol

from app.core.config import settings


@dataclass
class BvnRecord:
    found: bool
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    phone: str | None = None
    date_of_birth: date | None = None
    reference: str = ""

    @property
    def full_name(self) -> str:
        return " ".join(x for x in (self.first_name, self.middle_name, self.last_name) if x)


class IdentityProvider(Protocol):
    name: str

    def lookup_bvn(self, bvn: str, *, hint_name: str, hint_phone: str | None, hint_dob: date | None) -> BvnRecord: ...


class MockIdentityProvider:
    """DEVELOPMENT/TEST ONLY.

    Test BVNs: starting with "000" → not found; ending with "9999" → registered to a different name;
    anything else (11 digits) → registered to the name/phone/DOB supplied, i.e. a match.
    """

    name = "mock"

    def lookup_bvn(self, bvn, *, hint_name, hint_phone, hint_dob):
        ref = f"MOCKBVN-{bvn[-4:]}"
        if bvn.startswith("000"):
            return BvnRecord(found=False, reference=ref)
        if bvn.endswith("9999"):
            return BvnRecord(found=True, first_name="Musa", last_name="Abdullahi", phone="+2348000000000",
                             date_of_birth=date(1990, 1, 1), reference=ref)
        parts = hint_name.split()
        return BvnRecord(found=True, first_name=parts[0], last_name=parts[-1] if len(parts) > 1 else "",
                         middle_name=" ".join(parts[1:-1]), phone=hint_phone, date_of_birth=hint_dob, reference=ref)


@lru_cache
def get_identity_provider() -> IdentityProvider:
    if settings.environment in ("development", "test") or settings.payment_provider == "mock":
        return MockIdentityProvider()
    raise RuntimeError("No identity verification provider configured")


def names_match(a: str, b: str) -> bool:
    """Lenient match: at least two name tokens in common (or one, if either side has a single name)."""
    ta = {t for t in a.lower().replace("-", " ").split() if len(t) > 1}
    tb = {t for t in b.lower().replace("-", " ").split() if len(t) > 1}
    need = 1 if min(len(ta), len(tb)) <= 1 else 2
    return len(ta & tb) >= need
