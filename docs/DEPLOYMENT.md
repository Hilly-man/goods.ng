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
- **Database:** managed PostgreSQL 15+ with PITR enabled, private networking and TLS. Each API process opens `DB_POOL_SIZE + DB_MAX_OVERFLOW` connections, so total = that × `WEB_CONCURRENCY` × replicas: size it against `max_connections` and put **PgBouncer** (transaction pooling) in front once you run more than a handful of API replicas. Add read replicas for search/browse before write throughput becomes the limit.
- **Cache:** managed Redis (required in production).
- **Storage:** S3-compatible bucket (`STORAGE_BACKEND=s3`). Public images go behind a CDN (`MEDIA_BASE_URL`). KYC documents live under the `private/` prefix with **no public access**, server-side encryption, and access via short-lived signed URLs only.
- **Upload limits:** each input is capped by `MAX_UPLOAD_MB` (8 MB), decoded with Pillow (40 MP decompression-bomb guard), and re-encoded to WebP at 1280px (thumbnail 400px). Listing photos are watermarked with the seller's business name and **Goods.ng** before encoding. `MAX_IMAGES_PER_SELLER` (default 200) caps total listing photos per seller, and the worker purges soft-deleted listings after `DELETED_LISTING_RETENTION_DAYS` (default 30).
- **Secrets:** use a secret manager (not committed `.env` files). `DATA_ENCRYPTION_KEY` must be backed up separately — losing it makes encrypted KYC identifiers unreadable.

## Deploy on Render

`render.yaml` at the repo root is a [Render Blueprint](https://render.com/docs/blueprints) that
creates the API, worker and web app (all from the existing Dockerfiles), plus managed PostgreSQL
and Key Value (Redis).

1. Push the repo to GitHub, then in Render choose **New → Blueprint**, select the repo and click
   **Apply**. The services and datastores are created together. The first build takes a few
   minutes; the API later runs `alembic upgrade head` as its pre-deploy command.
2. Open `goodsng-web`'s `onrender.com` URL. If the first API deploy raced database provisioning,
   redeploy `goodsng-api`.
3. Seed demo data once from **goodsng-api → Shell**: `python -m app.seed --demo`
   (optionally `python -m app.seed_images`). Changes made in the shell are not preserved.
4. To use a custom domain, add it to `goodsng-web`, then update `NEXT_PUBLIC_SITE_URL` (build-time)
   and the API's `FRONTEND_URL`/`CORS_ORIGINS` to `https://your-domain` and redeploy. These values
   default to the `onrender.com` URL via `RENDER_EXTERNAL_URL`.
5. The Blueprint uses `ENVIRONMENT=staging`, mock providers, console SMS/email and local media
   storage on a disk attached to the API, so it works without third-party credentials. It is **not
   production-ready**: before switching to `ENVIRONMENT=production`, configure real providers, S3
   storage, a captcha, SMS/email and `TRUSTED_PROXY_CIDRS` as described above.

Notes specific to the current Blueprint:

- The media disk is attached only to the API. The worker cannot purge deleted listing photos from
  it; with `STORAGE_BACKEND=local` uploads also do not survive without the disk. Use S3
  (`STORAGE_BACKEND=s3`) for production.
- Plans and region (`frankfurt`) are chosen for a small production-like deployment; adjust
  `plan` values in `render.yaml` to change cost/capacity.
- Secrets marked `generateValue: true` are created on first sync. Back up
  `DATA_ENCRYPTION_KEY` separately — losing it makes encrypted KYC identifiers unreadable.

## Provider configuration (Goods Flex)

| Variable | Development | Staging / production |
|---|---|---|
| `BANK_DATA_PROVIDER` | `mock` | `mono` |
| `MONO_SECRET_KEY` | — | `test_sk_…` in staging, `live_sk_…` in production |
| `MONO_PUBLIC_KEY` | — | Mono public key (served to the browser only for the Connect widget) |
| `BNPL_PROVIDER` | `mock` | licensed lender adapter (not bundled) |
| `SMS_PROVIDER` | `console` | `termii` (`TERMII_API_KEY`, `TERMII_SENDER_ID`) |
| `EMAIL_PROVIDER` | `console` | `postmark` (`POSTMARK_SERVER_TOKEN`) or `smtp` (`SMTP_HOST`, `SMTP_FROM`, credentials) |

The Mono secret key is used only by the API. Never prefix it with `NEXT_PUBLIC_` or expose it to the browser. The `bank_data_provider` boot guard refuses `mock` in production and requires `MONO_SECRET_KEY` when Mono is selected.

## Sign in with Google

1. In Google Cloud Console → APIs & Services → Credentials, create an **OAuth client ID** of type *Web application*.
2. Authorised redirect URI: `${FRONTEND_URL}/api/v1/auth/google/callback` (e.g. `https://goods.ng/api/v1/auth/google/callback`; add the staging URL to a separate client).
3. Configure the OAuth consent screen (app name Goods.ng, support email, privacy policy and terms URLs; scopes `openid email profile`) and publish it.
4. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` on the API only — never as `NEXT_PUBLIC_*`.

Without these, development/test use a clearly-labelled mock consent screen and staging/production hide the button. Staff accounts cannot use Google sign-in; accounts with 2FA still have to enter their code.

## "I'm not a robot" check on sign-in

The sign-in form asks for a captcha when the browser hasn't signed in successfully in the last 24 hours, or after 3 wrong passwords on the account. It's enforced by the API before the password is checked.

- **Google reCAPTCHA v2 (checkbox):** create a v2 "I'm not a robot" key at google.com/recaptcha/admin for your domains, then set `CAPTCHA_PROVIDER=recaptcha`, `CAPTCHA_SITE_KEY` and `CAPTCHA_SECRET_KEY`.
- **Cloudflare Turnstile** (privacy-friendly alternative): create a widget in the Cloudflare dashboard, then set `CAPTCHA_PROVIDER=turnstile` with its site key and secret.

Production refuses to start with `mock` or `off`. The site's Content-Security-Policy already allows both providers' scripts and frames.

## Advertising on Google & Facebook

Goods.ng advertises quality-checked Premium listings from its own ad accounts.

1. **Google Merchant Center** — create an account, verify and claim `goods.ng`, set Nigeria / NGN as the target, add a *scheduled fetch* feed with the Google feed URL shown in **Admin › Platform settings › Ads** (`/api/v1/feeds/google.xml`). Then link Merchant Center to **Google Ads** and create a Performance Max (or Shopping) campaign — a feed alone doesn't run ads. Nigeria is marked *beta* by Google, so some placements may not be available yet.
2. **Meta** — in Business Manager create a Pixel and a catalog (Commerce Manager → data source → scheduled feed with `/api/v1/feeds/meta.csv`), verify the domain, then run Advantage+ catalog ads.
3. Enter the **Meta Pixel ID**, **GA4 ID**, **Google Ads tag ID** and **purchase conversion label** in Admin › Platform settings, and tick *Publish product feeds*.
4. Server-side purchases (Meta Conversions API): set `META_CAPI_ACCESS_TOKEN` (and optionally `META_GRAPH_VERSION`) on the API and run the worker. Only orders whose buyer accepted marketing cookies are reported; emails/phones are SHA-256 hashed.
5. Optional: set `FEED_TOKEN` and append `?token=…` to the feed URLs to stop casual scraping.

Tracking scripts never load until a visitor accepts marketing cookies (banner + "Cookie settings" in the footer; NDPA). Feeds contain only Premium listings with a verified seller, 3+ photos and a real description; property, vehicles, jobs and services are excluded by default.

## Security configuration

| Variable | Development | Staging / production |
|---|---|---|
| `TRUSTED_PROXY_CIDRS` | empty | load balancer CIDRs, e.g. `10.0.0.0/8` |
| `ADMIN_2FA_REQUIRED` | `false` | `true` (boot guard requires it) |
| uvicorn proxy flags | — | leave `--proxy-headers` off; the app reads `X-Forwarded-For` only from `TRUSTED_PROXY_CIDRS` |

`X-Forwarded-For` is ignored unless the peer is in `TRUSTED_PROXY_CIDRS`; the app then walks the chain right-to-left. Admins must enable TOTP 2FA at `/account` before the admin API accepts their session. The frontend sends a CSP and HSTS header; if you add analytics or error tracking, extend `script-src`/`connect-src` in `frontend/next.config.ts` rather than disabling the policy.

## Admin console subdomain

The admin console is served from its own subdomain (e.g. `https://admin.goods.ng`) by `frontend/src/proxy.ts`.

1. **DNS:** add `admin.goods.ng` pointing at the frontend (on Vercel: add the domain to the same project; it issues the certificate).
2. **Frontend env (build + runtime):** `ADMIN_URL=https://admin.goods.ng` and `NEXT_PUBLIC_ADMIN_URL=https://admin.goods.ng`. `NEXT_PUBLIC_*` values are baked in at build time, so redeploy after changing them.
3. **Behaviour:**
   - `admin.goods.ng/` → console overview; `admin.goods.ng/<section>` → that section (`/users`, `/disputes`, …).
   - `goods.ng/admin/...` → 308 redirect to the subdomain; `admin.goods.ng/admin/...` → 308 to the clean URL.
   - Other paths on the admin host (`/login`, `/orders/<id>`, `/item/...`) are served normally, so admin links to order detail pages keep working.
   - Every admin-host response carries `X-Robots-Tag: noindex, nofollow`.
   - Sessions are per host (the refresh cookie is host-only), so admin sign-in is separate from the shop.
4. **Optional hardening:** restrict `admin.goods.ng` at the edge (Vercel Firewall / Cloudflare Access / office VPN IP allow-list) and set `ADMIN_2FA_REQUIRED=true`.

Leaving `ADMIN_URL` unset keeps the console at `/admin` on the main domain (useful for local development without subdomains). For local testing with the subdomain, use `http://admin.localhost:3000`; browsers resolve `*.localhost` automatically, and `next.config.ts` allows it as a dev origin.

## Staff accounts & the first super admin

Staff (admin) accounts are separate from customer accounts. Nobody can sign up as staff, and customers can never be promoted. After the first deploy to an environment, create the first super admin from a trusted shell:

```bash
python -m app.create_super_admin --email ceo@goods.ng --name "Ada Founder"
```

It prints a one-time link (valid 72 hours) for setting the password. Set `ADMIN_URL` on the API so invitation links point at the admin subdomain. From then on, the super admin invites staff from **Admin team** and assigns them roles (Operations Manager, Finance, Customer Support, Trust & Safety, KYC Officer, Marketing, Auditor or a custom role). The command refuses to run if an active super admin already exists, unless you pass `--force` (for access recovery).

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
