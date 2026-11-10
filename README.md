# Goods.ng

**Buy. Sell. Trade with Confidence.** A multi-vendor marketplace for Nigeria: classifieds-style discovery, in-app chat and price negotiation, premium direct contact (WhatsApp and phone), escrow-protected checkout, Goods Flex (buy now, pay later), seller verification and reviews.

| Layer | Stack |
|---|---|
| Frontend | Next.js 16 (App Router, Cache Components / PPR), React 19, TypeScript, Tailwind CSS 4 |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, PostgreSQL 15+, Redis |
| Integrations | Provider interfaces for payments (Paystack and Flutterwave adapters), escrow and BNPL. **Mock providers only for escrow and BNPL** — see [docs/STATUS.md](docs/STATUS.md) |

## Live

- Marketplace: https://goods-ng.vercel.app
- Admin console: https://admin-goods-ng.vercel.app

## Quick start (local development)

Prerequisites: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 24 with pnpm, PostgreSQL. Redis is optional in development.

```bash
# 0. Infrastructure (or use your own Postgres): docker compose up -d db redis
createdb goodsng_dev && createdb goodsng_test

# 1. Backend
cd backend
cp .env.example .env            # defaults work for local Postgres
uv sync
uv run alembic upgrade head
uv run python -m app.seed --demo   # categories, plans, demo users and listings
uv run python -m app.seed_images   # optional: generate watermarked demo photos
uv run uvicorn app.main:app --reload --port 8000
uv run python -m app.worker        # in another terminal: background jobs

# 2. Frontend
cd ../frontend
cp .env.example .env.local
pnpm install
pnpm dev                           # http://localhost:3000
```

Demo accounts (password `GoodsNG2026!`): `admin@goods.ng` (super admin), `buyer@demo.goods.ng` (buyer), `chinedu@demo.goods.ng` (premium, business-verified seller).

In development, payments go to a **mock provider page** (`/dev/mock-checkout`) where you can simulate success or failure. The resulting webhook is HMAC-signed and goes through the same server-side verification path as real providers. OTP codes are echoed in API responses (as `dev_code`) and shown in the UI, because SMS isn't connected in development.

API docs: http://localhost:8000/docs

## Tests

```bash
cd backend && uv run pytest                 # 187 API/integration tests against real PostgreSQL
cd frontend && pnpm test                    # unit tests (money formatting, redirects)
cd frontend && pnpm build && pnpm start -p 3001 && pnpm test:e2e   # Playwright E2E (needs backend + demo seed)
cd backend && uv run python perf/smoke.py   # load smoke test of public read paths
```

## Documentation

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, domains, escrow state machine, ledger
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — environments, deploy, migrations, backups, rollback
- [docs/SECURITY.md](docs/SECURITY.md) — security controls and review findings
- [docs/STATUS.md](docs/STATUS.md) — what is built, what is mocked, outstanding work before launch
