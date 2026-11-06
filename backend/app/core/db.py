from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Server-side guardrails: a runaway or abusive query is cancelled instead of tying up the database,
# and a transaction left open (e.g. a crashed worker) can't hold row locks forever.
engine = create_engine(
    settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20,
    connect_args={"options": f"-c statement_timeout={settings.db_statement_timeout_ms}"
                             " -c idle_in_transaction_session_timeout=60000"},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
