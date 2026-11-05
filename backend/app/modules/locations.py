"""State → city reference data (from the `cities` table), cached, plus server-side validation."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.errors import AppError
from app.models import City

CACHE_KEY = "locations:all"


def cities_by_state(db: Session) -> dict[str, list[str]]:
    def build():
        out: dict[str, list[str]] = {}
        rows = db.scalars(select(City).where(City.is_active.is_(True)).order_by(City.state, City.sort_order, City.name))
        for c in rows:
            out.setdefault(c.state, []).append(c.name)
        return out

    return cache.get_or_compute(CACHE_KEY, 3600, build)


def canonical_city(db: Session, state: str | None, city: str | None, *, field: str = "city") -> str | None:
    """Return the canonical city name for the state, or raise a 422-style error if it doesn't belong."""
    if not city:
        return city
    cities = cities_by_state(db).get(state or "", [])
    match = next((c for c in cities if c.lower() == city.strip().lower()), None)
    if not match:
        raise AppError(
            f"Select a city in {state}" if state else "Select a state first",
            code="validation_error",
            status_code=422,
            details=[{"field": field, "message": f"Choose a city from the list for {state}" if state else "Select a state first"}],
        )
    return match
