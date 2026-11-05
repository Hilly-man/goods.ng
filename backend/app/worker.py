"""Background worker: `python -m app.worker` (or `--once` for cron-style single runs).

Each job takes a Postgres advisory lock, so running several worker replicas is safe: a job never
runs concurrently with itself.
"""

import argparse
import logging
import time
import zlib

from sqlalchemy import select, text, update

from app.core.db import SessionLocal
from app.core.logging import configure_logging
from app.core.time import utcnow
from app.main import app as _app  # noqa: F401  (registers payment handlers)
from app.models import Product, Promotion, Subscription
from app.models.enums import PromotionStatus, SubscriptionStatus
from app.modules.bnpl.service import mark_overdue_and_remind
from app.modules.negotiation.service import expire_due as expire_negotiations
from app.modules.notifications.service import drain_outbox
from app.modules.orders.service import auto_release_due, expire_unpaid

log = logging.getLogger("goodsng.worker")


def expire_subscriptions_and_features(db) -> dict:
    now = utcnow()
    subs = db.execute(update(Subscription).where(Subscription.status == SubscriptionStatus.ACTIVE,
                                                 Subscription.current_period_end <= now)
                      .values(status=SubscriptionStatus.EXPIRED)).rowcount
    promos = db.execute(update(Promotion).where(Promotion.status == PromotionStatus.ACTIVE, Promotion.ends_at <= now)
                        .values(status=PromotionStatus.EXPIRED)).rowcount
    feats = db.execute(update(Product).where(Product.is_featured.is_(True), Product.featured_until <= now)
                       .values(is_featured=False)).rowcount
    db.commit()
    _ = select
    return {"subscriptions": subs, "promotions": promos, "featured": feats}


JOBS = {
    # name: (interval seconds, fn)
    "outbox": (10, drain_outbox),
    "expire_unpaid_orders": (60, expire_unpaid),
    "expire_negotiations": (60, expire_negotiations),
    "auto_release_escrow": (300, auto_release_due),
    "expire_subscriptions": (300, expire_subscriptions_and_features),
    "bnpl_reminders": (3600, mark_overdue_and_remind),
}


def run_job(name: str) -> None:
    _, fn = JOBS[name]
    with SessionLocal() as db:
        key = zlib.crc32(f"goodsng:{name}".encode())
        if not db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar():
            return
        try:
            result = fn(db)
            if result:
                log.info("job_done", extra={"job": name, "result": result})
        except Exception:
            db.rollback()
            log.exception("job_failed", extra={"job": name})
        finally:
            db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            db.commit()


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="run every job once and exit")
    args = parser.parse_args()
    if args.once:
        for name in JOBS:
            run_job(name)
        return
    last = dict.fromkeys(JOBS, 0.0)
    log.info("worker_started", extra={"jobs": list(JOBS)})
    while True:
        now = time.monotonic()
        for name, (interval, _) in JOBS.items():
            if now - last[name] >= interval:
                run_job(name)
                last[name] = now
        time.sleep(2)


if __name__ == "__main__":
    main()
