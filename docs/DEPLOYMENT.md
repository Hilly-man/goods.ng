# Goods.ng — Deployment Runbook

## Environments

| | Development | Staging | Production |
|---|---|---|---|
| `ENVIRONMENT` | development | staging | production |
| Providers | mock | **real provider test/sandbox keys** | live keys, licensed escrow + lending partners |
| Dev routes (`/api/v1/dev/*`), OTP echo | on | off | off |
| API docs `/docs` | on | on | off |
| Boot guard | — | rejects dev secrets | rejects dev secrets, missing Redis, **any mock provider** |

## Topology

- **Frontend:** Vercel. Root `frontend/`, build `pnpm build`. Set `API_INTERNAL_URL` (backend URL) and `NEXT_PUBLIC_SITE_URL`. The `/api/v1` and `/media` rewrites proxy to the backend. Alternative: `frontend/Dockerfile`.
- **Backend:** container platform (Cloud Run, ECS/Fargate, Fly, Render, Railway…) using `backend/Dockerfile`, with at least 2 instances behind HTTPS. The worker runs the same image with `python -m app.worker` (1+ replicas; jobs take advisory locks).
- **Database:** managed PostgreSQL 15+ with PITR enabled, private networking and TLS.
- **Cache:** managed Redis (required in production).
- **Storage:** S3-compatible bucket (`STORAGE_BACKEND=s3`). Public images go behind a CDN (`MEDIA_BASE_URL`). KYC documents live under the `private/` prefix with **no public access**, server-side encryption, and access via short-lived signed URLs only.
- **Secrets:** use a secret manager (not committed `.env` files). `DATA_ENCRYPTION_KEY` must be backed up separately — losing it makes encrypted KYC identifiers unreadable.

## Provider configuration (Goods Flex)

| Variable | Development | Staging / production |
|---|---|---|
| `BANK_DATA_PROVIDER` | `mock` | `mono` |
| `MONO_SECRET_KEY` | — | `test_sk_…` in staging, `live_sk_…` in production |
| `MONO_PUBLIC_KEY` | — | Mono public key (served to the browser only for the Connect widget) |
| `BNPL_PROVIDER` | `mock` | licensed lender adapter (not bundled) |

The Mono secret key is used only by the API. Never prefix it with `NEXT_PUBLIC_` or expose it to the browser. The `bank_data_provider` boot guard refuses `mock` in production and requires `MONO_SECRET_KEY` when Mono is selected.

## Release procedure

1. CI must pass (`.github/workflows/ci.yml`): lint, tests against Postgres, migration round-trip, frontend lint/typecheck/unit/build, and the Playwright E2E suite (protected checkout, negotiation, direct-contact gate, mandatory guarantor + one-plan rule).
2. **Back up** (or confirm a recent PITR point) before migrations.
3. Run migrations as a one-off release job: `alembic upgrade head`. Migrations must be backward-compatible with the running version (expand → deploy → contract).
4. Deploy the API and worker images, wait for `/health/ready` (checks DB and reports cache backend and providers).
5. Deploy the frontend.
6. Smoke test: home, search, item page, login, a staging test payment end to end.

## Webhooks

Configure provider webhooks to `https://<api-domain>/api/v1/payments/webhooks/<provider>/webhook`. Signatures are verified (Paystack HMAC-SHA512, Flutterwave `verif-hash`), and invalid signatures get 403. Events are de-duplicated. If a webhook is missed, the unpaid-order expiry job and the buyer's return page both re-verify with the provider.

## Rollback

- Application: redeploy the previous image tag (images are immutable; tag by git SHA).
- Database: prefer forward fixes. `alembic downgrade -1` exists for every migration but **must not be run in production on financial tables without a DBA review**. Ledger, escrow-event and audit tables are append-only by design.
- Feature kill-switches: disable Protected Checkout or Goods Flex per listing via admin moderation. Set `listing_moderation_required` in Platform Settings to stop new listings going live.

## Backups and recovery

- Managed PITR (7–35 days) plus a daily logical dump (`pg_dump -Fc`) to a separate account or region, encrypted, with 30-day retention.
- **Quarterly restore drill** into staging, then run `/admin/reconciliation` and check that the ledger is balanced.
- Object storage: versioning enabled, cross-region replication for `private/`.

## Monitoring and alerting

- Logs: structured JSON on stdout, with `request_id` on every line (also returned in the `x-request-id` header). Ship them to your log platform.
- Error tracking: add the Sentry SDK (FastAPI and Next.js) with the DSN from secrets. Not wired yet — see STATUS.md.
- Alert on: 5xx rate, p95 latency, `/health/ready` failures, worker job failures (`job_failed` log), `payment_amount_mismatch`, `webhook_invalid_signature` spikes, non-empty reconciliation lists, overdue BNPL instalment growth, spikes in `guarantor_limit_reached` or `provider_error` from Mono, and a drop in successful bank connections.
- Uptime checks on `/health` and the homepage.
