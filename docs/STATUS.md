# Goods.ng — Build Status

Last updated: 10 November 2026.

## Verification at this checkpoint

| Check | Result |
|---|---|
| Backend tests (pytest, real PostgreSQL) | **217 passed** |
| Frontend unit tests (vitest) | **5 passed** |
| E2E (Playwright, mobile viewport, production build) | **6 passed**: redesigned product page; full protected purchase lifecycle; negotiation → checkout at agreed price; direct-contact warning gate; mandatory-guarantor and one-running-plan rules; TOTP 2FA login challenge |
| Security controls | TOTP 2FA with recovery codes and replay protection · trusted-proxy IP resolution · CSP and HSTS headers |
| Lint / types | ruff clean · eslint 0 errors · tsc clean |
| Production build | `next build` succeeds (static and partially prerendered routes) |
| Migrations | upgrade and downgrade round-trip clean |
| Auto-title suggestions | Deterministic titles from brand, model, condition and category, with storage/colour/year/size detected from the description; feeds the weight-A search field |
| Load smoke test (single dev worker, 20 concurrent) | home feed ~300 req/s, p95 ~220 ms; search ~240 req/s, p95 ~125 ms; 0 errors |
| k6 realistic mix (`backend/perf/load.js`, single dev worker) | 120 VUs: 0 errors, p95 41 ms · 400 VUs: 182 req/s, p95 553 ms, 0 errors · 800 VUs: plateau ~182 req/s, p95 ~1.9 s (one worker saturates) |

## Stages

| # | Stage | Status |
|---|---|---|
| 1–3 | Requirements, architecture, project setup | Done |
| 4 | Database (46 tables, constraints, partial unique indexes, integrity triggers) | Done |
| 5 | Authentication (JWT + rotating refresh, email verification, phone OTP, lockout, reset) | Done |
| 6 | Marketplace (categories, listings, watermarked WebP images — 5 per listing free / 10 Premium, 200-photo seller cap; full-text search, filters, favourites, keyword-rich auto-title suggestions) | Done |
| 7 | Seller management (profiles, dashboard, analytics, verification) | Done |
| 8 | Premium subscriptions (plans, paid activation, featured credits, admin grants) and per-listing paid promotions (TOP / Boost Premium) | Done |
| 9 | Messaging (product-linked chats, read receipts, unread counts, reports) | Done — polling, not WebSockets |
| 10 | Negotiation (offers, counters, expiry, concurrency, agreed-price checkout) | Done |
| 11 | Payments abstraction (mock, Paystack, Flutterwave adapters) and checkout choice: Protected Checkout or pay the seller directly outside the app | Done — **Paystack/Flutterwave not yet exercised against sandbox** |
| 12 | Protected checkout & escrow (state machine, ledger, disputes, refunds) | Done against **mock escrow partner** |
| 13 | Orders & delivery (manual tracking, evidence, auto-release, buyer-only delivery PIN, carrier provider abstraction — mock, arrange-outside-app delivery option) | Done |
| 14 | BNPL (Goods Flex): 40% down + 60% over 3/6 months at 3%/month, bank-statement credit limit, **mandatory guarantor**, verification tiers, **one running plan at a time**, per-listing seller opt-in with 70/30 financing-charge share | Done against **mock lending partner and mock open-banking provider** |
| 15 | Reviews & ratings | Done |
| 16 | Notifications (in-app, outbox for email/SMS, preferences) | Done — **email/SMS senders are console stubs** |
| 17 | Administration (19 sections, granular RBAC, audit logs, live traffic stats, full seller dashboard with listings and moderation, orders, verification and wallet; all-seller wallet balances; listing filter by seller; admin listing editor with photos) | Done |
| 18 | Testing | Done (see above) |
| 19 | Security review | Done — see SECURITY.md findings |
| 20 | Deployment | Dockerfiles, Compose, CI and runbook written. **Not yet deployed anywhere.** |

## What is mocked (and must not be described as live)

- **Escrow partner:** `MockEscrowProvider`. Goods.ng needs a contract with a CBN-licensed escrow or payment partner and an adapter implementing `EscrowProvider` (`backend/app/integrations/escrow.py`).
- **Lending partner (Goods Flex):** `MockFinancingProvider`, whose pricing (40% down payment, then 3% flat per month on the financed balance for 3 or 6 months) and affordability rule are illustrative. A licensed lender adapter must implement `FinancingProvider`, and real terms must be reviewed against FCCPC digital lending regulations.
- **Open banking (Goods Flex credit limit):** `MockBankDataProvider` generates deterministic six-month statements for test personas, and a `MonoBankDataProvider` adapter is implemented against Mono's v2 API. The Mono adapter is **not yet tested against a Mono sandbox account**; set `BANK_DATA_PROVIDER=mono` with `test_sk_…` keys in staging. The credit engine's thresholds are configurable but illustrative and need review against the lender's credit policy and FCCPC digital lending rules.
- **Payments:** development uses the mock provider. The Paystack and Flutterwave adapters follow the providers' public documentation but **have not been tested against a sandbox account**.
- **Email/SMS:** messages are queued in an outbox. Development uses a console logger; production adapters for **Termii SMS**, **Postmark** and **SMTP** are implemented but have **not been sandbox-tested** yet. Set `SMS_PROVIDER=termii` and `EMAIL_PROVIDER=postmark|smtp` with credentials in staging.
- **Seller payouts:** a ledger-backed wallet, bank accounts, withdrawal requests, 24h clearing and a staff review/approval step (`payouts.approve`) are implemented against a **mock payout provider**. Live disbursement needs a licensed payout partner adapter (`backend/app/integrations/payouts.py`).
- **Buyer verification:** a verified email and phone are required for checkout and Goods Flex. Emails are sent at registration; phone verification uses SMS OTP.
- **Carrier delivery:** order delivery uses a buyer-only 6-digit PIN. A `DeliveryProvider` interface and mock adapter exist (`backend/app/integrations/delivery.py`); real carrier webhooks (Shipbubble/GIG/Fez) are not integrated yet.

## Outstanding before launch (prioritised)

1. Sign the licensed escrow/payment and lending partners; implement and sandbox-test their adapters; verify Paystack/Flutterwave and the Mono open-banking adapter in staging.
2. Sandbox-test the Termii SMS and Postmark/SMTP email adapters; add push notifications for future mobile apps.
3. Deploy staging (managed Postgres, Redis, S3 with CDN, Vercel); set up Sentry error tracking and alerting.
4. Security follow-ups in SECURITY.md (upload malware scanning, licensed KYC provider, external penetration test, DPO/data-subject workflow).
5. **Legal review** of the Terms, Privacy, Refund & Dispute, Goods Flex and guarantor consent copy. The current text is a draft written for product purposes, not legal advice. See the Goods Flex compliance checklist in SECURITY.md.
6. Partial refunds (the model supports amounts, but the UI and dispute flow only offer full refunds today).
7. Connect a licensed payout partner (bank transfer/PSSP) and replace `MockPayoutProvider`; sandbox-test failed-transfer retries and reconciliation.
8. Integrate live carriers (Shipbubble first, then GIG/Fez) behind the new `DeliveryProvider` interface; **coming soon** — until then courier deliveries are seller-arranged and tracked manually.
9. WebSocket or SSE messaging if polling load becomes significant.
10. Paid promotions: per-listing TOP (7 or 30 days) and Boost Premium (28 days) packages are live with one-off checkout and automatic expiry — no subscription required. Prices can be overridden via the `promotion_packages` platform setting.
