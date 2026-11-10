from datetime import timedelta

from app.core.time import utcnow
from app.models import SiteVisit


def _visit(db, visitor, *, minutes_ago=0, user_id=None):
    db.add(SiteVisit(visitor_id=visitor, user_id=user_id, path="/", created_at=utcnow() - timedelta(minutes=minutes_ago)))


def test_traffic_ping_and_admin_live_stats(client, db, make_admin, make_user):
    user = make_user()
    # Signed-in heartbeat.
    assert user.post("/stats/visit", {"path": "/search"}, headers={"X-Anon-Id": "signed-in-visitor"}).status_code == 204
    # Guest page view.
    assert client.post("/api/v1/stats/visit", json={"path": "/item/phone"},
                       headers={"X-Anon-Id": "guest-visitor-1"}).status_code == 204
    # No anonymous id => ignored (never fingerprint the IP).
    assert client.post("/api/v1/stats/visit", json={"path": "/"}).status_code == 204
    assert db.query(SiteVisit).count() == 2

    _visit(db, "active-10m", minutes_ago=10)
    _visit(db, "active-10d", minutes_ago=60 * 24 * 10)
    _visit(db, "active-100d", minutes_ago=60 * 24 * 100)
    _visit(db, "active-400d", minutes_ago=60 * 24 * 400)
    db.commit()

    stats = make_admin(["analytics.view"]).get("/admin/live-stats").json()
    assert stats["visitors"] == {"daily": 3, "weekly": 3, "monthly": 4, "quarterly": 4, "yearly": 5}
    assert stats["active"]["live_5m"] == 2
    assert stats["active"]["active_15m"] == 3
    assert stats["active"]["active_60m"] == 3
    assert stats["active"]["active_24h"] == 3
    assert stats["active"]["signed_in"] == 1 and stats["active"]["guests"] == 1
    assert stats["updated_at"]

    assert make_admin(["payments.view"]).get("/admin/live-stats").status_code == 403
    assert user.get("/admin/live-stats").status_code == 403
