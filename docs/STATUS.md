# Goods.ng — Build Status

Last updated: 5 November 2026.

## Verification at this checkpoint

| Check | Result |
|---|---|
| Backend tests (pytest, real PostgreSQL) | **97 passed** |
| Frontend unit tests (vitest) | **5 passed** |
| E2E (Playwright, mobile viewport, production build) | **4 passed**: full protected purchase lifecycle; negotiation → checkout at agreed price; direct-contact warning gate; mandatory-guarantor and one-running-plan rules |
| Lint / types | ruff clean · eslint 0 errors · tsc clean |
| Production build | `next build` succeeds (static and partially prerendered routes) |
| Migrations | upgrade and downgrade round-trip clean |
| Load smoke test (single dev worker, 20 concurrent) | home feed ~300 req/s, p95 ~220 ms; search ~240 req/s, p95 ~125 ms; 0 errors |

## Stages

| # | Stage | Status |
|---|---|---|
| 1–3 | Requirements, architecture, project setup | Done |
| 4 | Database (46 tables, constraints, partial unique indexes, integrity triggers) | Done |
| 5 | Authentication (JWT + rotating refresh, OTP, lockout, reset) | Done |
| 6 | Marketplace (categories, listings, images, full-text search, filters, favourites) | Done |
| 7 | Seller management (profiles, dashboard, analytics, verification) | Done |
| 8 | Premium subscriptions (plans, paid activation, featured credits, admin grants) | Done |
| 9 | Messaging (product-linked chats, read receipts, unread counts, reports) | Done — polling, not WebSockets |
| 10 | Negotiation (offers, counters, expiry, concurrency, agreed-price checkout) | Done |
| 11 | Payments abstraction (mock, Paystack, Flutterwave adapters) | Done — **Paystack/Flutterwave not yet exercised against sandbox** |
| 12 | Protected checkout & escrow (state machine, ledger, disputes, refunds) | Done against **mock escrow partner** |
| 13 | Orders & delivery (manual tracking, evidence, auto-release) | Done |
| 14 | BNPL (Goods Flex): bank-statement credit limit, **mandatory guarantor**, verification tiers, **one running plan at a time** | Done against **mock lending partner and mock open-banking provider** |
| 15 | Reviews & ratings | Done |
| 16 | Notifications (in-app, outbox for email/SMS, preferences) | Done — **email/SMS senders are console stubs** |
| 17 | Administration (18 sections, granular RBAC, audit logs) | Done |
| 18 | Testing | Done (see above) |
| 19 | Security review | Done — see SECURITY.md findings |
| 20 | Deployment | Dockerfiles, Compose, CI and runbook written. **Not yet deployed anywhere.** |

## What is mocked (and must not be described as live)

- **Escrow partner:** `MockEscrowProvider`. Goods.ng needs a contract with a CBN-licensed escrow or payment partner and an adapter implementing `EscrowProvider` (`backend/app/integrations/escrow.py`).
- **Lending partner (Goods Flex):** `MockFinancingProvider`, whose pricing (30% down payment, 3.5% flat per month) and affordability rule are illustrative. A licensed lender adapter must implement `FinancingProvider`, and real terms must be reviewed against FCCPC digital lending regulations.
- **Open banking (Goods Flex credit limit):** `MockBankDataProvider` generates deterministic six-month statements for test personas, and a `MonoBankDataProvider` adapter is implemented against Mono's v2 API. The Mono adapter is **not yet tested against a Mono sandbox account**; set `BANK_DATA_PROVIDER=mono` with `test_sk_…` keys in staging. The credit engine's thresholds are configurable but illustrative and need review against the lender's credit policy and FCCPC digital lending rules.
- **Payments:** development uses the mock provider. The Paystack and Flutterwave adapters follow the providers' public documentation but **have not been tested against a sandbox account**.
- **Email/SMS:** messages are queued in an outbox and "sent" by a console logger. Add adapters (e.g. Termii or another Nigerian SMS gateway; SES, Postmark or SendGrid for email).
- **Payouts to sellers:** recorded as `seller_payable` in the ledger. Actual disbursement is the escrow partner's job and isn't integrated yet.

## Outstanding before launch (prioritised)

1. Sign the licensed escrow/payment and lending partners; implement and sandbox-test their adapters; verify Paystack/Flutterwave and the Mono open-banking adapter in staging.
2. Real SMS and email providers; push notifications for future mobile apps.
3. Deploy staging (managed Postgres, Redis, S3 with CDN, Vercel); set up Sentry error tracking and alerting.
4. Security follow-ups in SECURITY.md (trusted proxies, CSP, admin 2FA, upload malware scanning, KYC provider, pen test).
5. **Legal review** of the Terms, Privacy, Refund & Dispute, Goods Flex and guarantor consent copy. The current text is a draft written for product purposes, not legal advice. See the Goods Flex compliance checklist in SECURITY.md.
6. Partial refunds (the model supports amounts, but the UI and dispute flow only offer full refunds today).
7. Seller payout and bank-account management UI, once the escrow partner's payout API is known.
8. Logistics provider integrations (the delivery model already has carrier, tracking URL and updates).
9. WebSocket or SSE messaging if polling load becomes significant.
10. Paid promotions: the `Promotion` model and admin feature exist, and sellers use plan credits today; a pay-per-boost checkout is not built.
