# Goods.ng — Architecture

## System overview

```
 Browser (mobile-first)                       ┌───────────────────────────────┐
   │  same-origin /api/v1/* and /media/*      │  FastAPI (stateless, N pods)  │
   ▼                                          │  /api/v1  REST, JWT + RBAC    │
 Next.js 16 (Vercel) ── rewrite ─────────────▶│  modules/* (domain services)  │
   SSR/PPR public pages (SEO)                 └──────┬───────────┬────────────┘
   Client dashboards (buyer/seller/admin)            │           │
                                                     ▼           ▼
                                             PostgreSQL       Redis (cache, rate limits,
                                             (source of truth)   single-flight locks)
                                                     ▲
                                  Worker (python -m app.worker): outbox email/SMS, unpaid-order expiry,
                                  offer expiry, escrow auto-release, subscription expiry, BNPL reminders
 External (behind interfaces in app/integrations):
   PaymentProvider (mock | Paystack | Flutterwave) · EscrowProvider (mock) · FinancingProvider (mock)
   Object storage (local | S3-compatible) · Email/SMS senders (console in dev)
```

**Same-origin API.** The browser only talks to the Next.js origin, which rewrites `/api/v1/*` to FastAPI. The refresh-token cookie is therefore first-party, and no CORS is needed in production.

## Backend layout

```
backend/app/
  core/          config (env), db, security (argon2, JWT, Fernet, sanitising), errors, logging (JSON + request id),
                 cache (Redis with in-memory dev fallback; rate limiter; single-flight), deps (auth/RBAC dependencies)
  models/        SQLAlchemy models (46 tables) — users, sellers, catalog, messaging/negotiation, commerce, ledger, misc
  integrations/  payments/{base,mock,paystack,flutterwave}, escrow, bnpl, storage
  modules/       auth, users, sellers, categories, products, subscriptions, messaging, negotiation, payments,
                 orders (+ escrow state machine), bnpl, reviews, notifications, ledger, admin, dev (dev/test only)
  worker.py      scheduled jobs with Postgres advisory locks (safe to run multiple replicas)
  seed.py        reference data (+ demo data in development)
```

Each module owns its router and business logic. Cross-module coupling goes through service functions and the payment purpose registry (`payments.on_success(PaymentPurpose.X)`). The payments module never imports orders, subscriptions or BNPL directly.

## Roles and permissions

- Guest: browse, search, view listings, stores and reviews.
- User (buyer): every account. Becomes a **seller** by creating a seller profile.
- **Premium** is derived, never stored as a flag: an ACTIVE subscription whose period covers *now* (`subscriptions/premium.py`). The client cannot grant itself premium.
- **Per-listing promotions** are separate from Premium: `products.promoted_tier` mirrors an ACTIVE paid `Promotion` while `featured_until` is in the future, so one listing can be promoted without an account plan.
- Admins: `role=admin` with granular permissions (`users.manage`, `refunds.approve`, `disputes.resolve`, …). `super_admin` has all permissions and is the only role that can change roles. Every sensitive admin action writes an append-only `admin_audit_logs` row.

## Protected checkout and escrow

Goods.ng does **not** hold funds. A licensed escrow/payment partner holds them; Goods.ng instructs release or refund. The ledger mirrors the partner's position.

State machine (`modules/orders/escrow.py` — the only place statuses change):

```
pending_payment ─▶ payment_confirmed ─▶ funds_safeguarded ─▶ awaiting_seller ─▶ processing ─▶ dispatched
      │                                                            │                │              │
      ▼                                                            ▼                ▼              ▼
  cancelled                                              refund_pending ◀── (decline/cancel)   delivered
                                                               │                               │
                                                               ▼                               ▼
                                                           refunded       completed ◀─ awaiting_buyer_confirmation
                                                                              ▲                │
                                                       disputed ──────────────┘ (admin)        │ (auto-release after N days)
```

Guarantees:

- **Verify before trust.** A payment counts only after a server-to-server `verify()` with the provider returns success with the *exact* expected amount and currency. Webhooks must pass signature verification, and they only *trigger* verification. Redirects and screenshots are never trusted.
- **Idempotency.** Webhook events are unique per `(provider, event_key)`. `confirm_payment` row-locks the payment and applies effects once. Checkout accepts an `Idempotency-Key`.
- **No double settlement.** Release and refund are guarded by the state machine, by row locks (`SELECT … FOR UPDATE` on order and escrow), and by a unique ledger key `escrow:<id>:settle`. A concurrency test fires five simultaneous confirmations and asserts exactly one settlement.
- **Server-side pricing.** Totals are computed from the listing, or from an accepted negotiation owned by the buyer. Client-sent prices are ignored. A DB check constraint enforces `total = subtotal + delivery_fee + protection_fee`.
- **Stock** is reserved atomically at checkout (`UPDATE … WHERE quantity >= n`) and restored when an unpaid order expires or a refund happens before dispatch. If payment arrives after expiry, the expiry job asks the provider first; the order is honoured if stock is still available, otherwise the payment is automatically refunded.
- **Refund controls.** Pre-dispatch cancellations and seller declines are refunded automatically. Dispute refunds need a second, different admin (four-eyes). A partial unique index allows only one active refund per order.

## Double-entry ledger

`ledger_accounts`, `ledger_transactions` (unique `idempotency_key`) and `ledger_entries`. Postings:

| Event | Debit | Credit |
|---|---|---|
| Escrow funded | asset:escrow_partner_holding | liability:escrow_obligations |
| Released to seller | liability:escrow_obligations | liability:seller_payable:<seller>, revenue:platform_commission, revenue:protection_fees |
| Refunded | liability:escrow_obligations | asset:escrow_partner_holding |
| Premium subscription | asset:provider_receipts | revenue:subscriptions |
| Listing promotion | asset:provider_receipts | revenue:promotions |

Database triggers make ledger tables, escrow events and audit logs **append-only**, and a deferred constraint trigger rejects any **unbalanced** transaction at commit. `/admin/reconciliation` cross-checks payments, escrow states and ledger postings.

## Promotions

Sellers can buy visibility for one listing without subscribing: `POST /api/v1/promotions` prices the package server-side, creates a `PaymentPurpose.PROMOTION` charge, and activates the `Promotion` only after server-side provider verification. TOP packages set the listing featured and bump it to the top; Boost Premium additionally marks it `promoted_tier=premium`, making it eligible for the sponsored pool while it meets the same photo/description/verification quality bar as Premium sellers. The worker expires promotions, clears stale badges, and refreshes Boost Premium top placement roughly daily. Package prices are defaults in `modules/promotions/packages.py`, overridable through the `promotion_packages` platform setting.

## Negotiation

`negotiations` (one live per buyer and product, enforced by a partial unique index) and `offers`. Every response locks the negotiation row and must name the pending offer ID, so stale or double clicks get `409 stale_offer`. Turn-taking, counter direction, a minimum offer (10% of list price), 48-hour offer expiry, a 24-hour checkout window after acceptance, and a 10-round cap are all enforced. The public listing price never changes. When paid, the negotiation becomes `converted`.

## Goods Flex (BNPL)

### Credit profile and limit

Before applying, a customer builds a credit profile: verified phone → BVN (encrypted, with a keyed fingerprint that blocks one BVN being reused across accounts) → read-only bank connection (mock in development; `MonoBankDataProvider` for real open banking) → guarantor who consents by SMS → optional workplace verification (work email, or CAC number plus business inflows). A guarantor is mandatory; without one the limit is zero and no application can start. The borrower must have a bank assessment before naming a guarantor, so the amount shown to the guarantor is meaningful. Guarantor BVNs carry a keyed fingerprint and each person can guarantee at most `max_active_guarantees` customers (default 3); consent, decline and cancellation are recorded and the borrower is notified. The amount shown at consent is stored and caps the borrower's limit, so a later change in circumstances cannot silently increase what the guarantor is liable for — the guarantor must consent again. Connecting a bank runs the assessment engine in `app/modules/bnpl/credit.py`, which is pure and deterministic so the rules can be tested and explained:

1. Classify six months of transactions; loan disbursements, reversals, self-transfers and failed debits are not income.
2. Salary is detected by keywords or a dominant regular credit across at least three months; otherwise income is 70% of the median eligible monthly inflow (a haircut for irregular traders).
3. Deduct existing loan repayments, then apply a risk factor from income volatility, missing months, betting share and failed debits.
4. The affordable monthly instalment is converted to a purchase-price limit using the financed share (60%), the 3% flat monthly charge on the financed balance, and the longest tenor.
5. The final limit is `min(statement limit, verification-tier cap, repayment-history cap, lender maximum)`, and is zero unless the customer has a verified phone, BVN, connected bank and a consented guarantor. The assessment is stored immutably as a snapshot with an expiry; tier caps, DTI and the first-plan cap are admin-editable (`flex_rules`).

### Application and the one-plan rule

Apply → partner decision (stored as `credit_decision_ref`, with the partner's offer terms stored verbatim) → buyer explicitly accepts → 40% down payment → partner funds the order through the same escrow path. The remaining 60% is spread over 3 or 6 months with a 3% flat monthly charge on the financed balance. Instalments are paid through the payment layer. The worker marks overdue instalments and sends reminders. Refunding a Flex order cancels the agreement with the partner.

Goods Flex is **opt-in per listing**, and the listing stores the accepted seller-terms version and timestamp. When a Flex order is released, the seller's earnings are credited in the ledger but the financed principal share (60% of the seller amount) is placed in `wallet_holds`, one hold per instalment. The seller can withdraw the 40% down-payment share after the 24-hour clearing window; each paid instalment releases its hold and credits the seller's 70% share of that month's financing charge (ledger account `expense:flex_seller_share`). Unpaid or defaulted instalments stay on hold and are not released. If a released Flex order is refunded or cancelled, a `bnpl_refund_recovery` hold locks the down-payment share, paid instalments and credited interest share; admin reconciliation reports open holds, hold-to-instalment mismatches and the seller-share ledger balance.

A customer may have **only one plan running** (`approved`, `accepted`, `active` or `defaulted`). The check is enforced in the service layer under a row lock and again by a partial unique index (`uq_bnpl_one_running_plan`), so concurrent requests cannot create two. Unpaid offers expire after 24 hours; withdrawing an unpaid application, seller decline and refund release the slot. A new plan is allowed only after every instalment is paid (or the plan is cancelled).

## Search

PostgreSQL full-text search: a generated, weighted `tsvector` column (title A, brand/model B, description C) with a GIN index and prefix matching (`iph` matches iPhone), plus filters and sorts. Relevance ranking puts featured listings first, then premium sellers, then text rank, then recency. `products.service.search()` is the single seam for moving to a dedicated search engine later.

## Frontend

- Public pages (home, search, category, item, store, info pages) are **server-rendered with streaming**. The static shell is prerendered and data streams in (Cache Components / PPR). Product pages include `Product` JSON-LD, canonical URLs, OG metadata, `sitemap.xml` and `robots.txt`.
- Dashboards (account, orders, messages, seller, admin) are client components on a central API client: in-memory access token, silent refresh through the httpOnly cookie with a CSRF header, and one retry on 401.
- Performance for Nigerian networks: system fonts (no font download), backend-generated WebP thumbnails (400px) and full images (1280px), lazy loading, skeleton states, Redis-cached feeds, and a bottom navigation bar on phones.
- Messaging is near-real-time: 5-second polling while visible, with read receipts. Polling pauses when the tab is hidden. WebSockets can replace it later without API changes.
