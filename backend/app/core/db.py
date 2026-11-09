import logging
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

log = logging.getLogger("goodsng.notify")

# Server-side guardrails: a runaway or abusive query is cancelled instead of tying up the database,
# and a transaction left open (e.g. a crashed worker) can't hold row locks forever.
engine = create_engine(
    settings.database_url, pool_pre_ping=True, pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow, pool_timeout=settings.db_pool_timeout,
    connect_args={"options": f"-c statement_timeout={settings.db_statement_timeout_ms}"
                             " -c idle_in_transaction_session_timeout=60000"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        # Serverless platforms (Vercel) have no long-running worker, so send queued email/SMS
        # as the request finishes. Close this session first: the pool is intentionally small.
        dirty = db.info.pop("outbox_dirty", False)
        db.close()
        if dirty:
            try:
                from app.modules.notifications.service import drain_outbox

                with SessionLocal() as outbox:
                    drain_outbox(outbox)
            except Exception:  # never fail a committed request because a provider is down
                log.exception("outbox_flush_failed")
