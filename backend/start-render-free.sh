#!/bin/sh
set -e

# Free Render web services have no pre-deploy command, Shell or one-off jobs, so the API
# migrates and seeds itself on boot. Migrations are idempotent; demo data is only inserted
# when SEED_DEMO=1 and the demo admin does not exist yet.
attempt=0
until alembic upgrade head; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 30 ]; then
    echo "alembic upgrade failed after $attempt attempts" >&2
    exit 1
  fi
  sleep 2
done

python -m app.seed

if [ "${SEED_DEMO:-0}" = "1" ]; then
  python - <<'PY'
from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import User
from app.seed import seed_demo

with SessionLocal() as db:
    if db.scalar(select(User).where(User.email == "admin@goods.ng")) is None:
        seed_demo(db)
PY
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}" --workers "${WEB_CONCURRENCY:-1}" --no-server-header
