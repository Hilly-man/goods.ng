"""Public product feeds for Google Merchant Center / Meta Commerce Manager, and public tracking IDs."""

import hmac

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.core.cache import cache
from app.core.config import settings
from app.core.deps import DB
from app.core.errors import NotFound
from app.modules.marketing import service

router = APIRouter(tags=["marketing"])
FEED_TTL = 900  # 15 min — the platforms fetch feeds a few times a day at most


def _guard(db, token: str | None) -> None:
    if not service.config(db)["feed_enabled"]:
        raise NotFound("Feed not enabled")
    if settings.feed_token and not hmac.compare_digest(token or "", settings.feed_token):
        raise NotFound("Feed not found")


@router.get("/feeds/google.xml", include_in_schema=False)
def google_feed(db: DB, token: str | None = Query(None)):
    _guard(db, token)
    body = cache.get_or_compute("feed:google", FEED_TTL, lambda: service.google_xml(db))
    return Response(body, media_type="application/xml", headers={"Cache-Control": "public, max-age=900"})


@router.get("/feeds/meta.csv", include_in_schema=False)
def meta_feed(db: DB, token: str | None = Query(None)):
    _guard(db, token)
    body = cache.get_or_compute("feed:meta", FEED_TTL, lambda: service.meta_csv(db))
    return Response(body, media_type="text/csv", headers={"Cache-Control": "public, max-age=900"})


@router.get("/tracking/config")
def tracking_config(db: DB):
    return cache.get_or_compute("tracking:config", 60, lambda: service.public_tracking(db))
