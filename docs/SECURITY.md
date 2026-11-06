# Goods.ng — Security Controls & Review

Review date: 5 November 2026. Scope: backend API, frontend, data model. Items marked ✅ are implemented **and covered by automated tests**. Items marked ☑ are implemented but not covered by dedicated tests.

## Authentication and sessions
- ✅ Argon2id password hashing; password policy (8+ characters, letters and digits).
- ✅ Short-lived JWT access tokens (15 min) kept in memory only. A per-user `token_version` revokes all tokens on password change, role change or account disable.
- ✅ Refresh tokens are opaque, stored as SHA-256 hashes, **rotated on every use**, and **reuse detection** revokes the whole token family. They live in an httpOnly, SameSite=Lax cookie scoped to `/api/v1/auth` (Secure in staging/production).
- ✅ CSRF: cookie-authenticated endpoints (refresh, logout) require the `X-Requested-With: goodsng` header. All other endpoints use Bearer tokens, which aren't sent automatically by browsers.
- ✅ Login lockout (5 failures → 15 minutes) and IP/email rate limits.
- ✅ OTP: 6 digits, HMAC-peppered hash, 10-minute TTL, 5 attempts, 3 sends per 10 minutes and 10 per day per number.
- ✅ Password reset doesn't reveal whether an account exists.
- ☑ Open-redirect protection on `?next=` (unit tested in the frontend).

## Authorisation
- ✅ Every resource is checked server-side for ownership (orders, conversations, negotiations, listings). Non-participants get 404 rather than 403, to avoid revealing that a resource exists.
- ✅ Granular admin permissions, and only super-admins can change roles. Tests cover a non-admin, an admin missing a permission, and a role change revoking sessions.
- ✅ Premium features (WhatsApp/phone buttons, banner, analytics, featured credits) are enforced server-side. A client-sent `is_premium` field is ignored.

## Payments and financial integrity
- ✅ Webhook signature verification; forged webhooks are rejected.
- ✅ Server-to-server verification with an exact amount and currency match; underpayment never funds an order.
- ✅ Idempotent webhooks and checkout; duplicate events have no effect.
- ✅ Duplicate settlement and refund prevention (state machine, row locks, unique ledger key, partial unique index), including a five-thread concurrency test.
- ✅ Prices are computed on the server; client-supplied prices and totals are ignored.
- ✅ The ledger is append-only and balanced at commit (DB triggers), and the audit log is append-only.
- ✅ **Bot protection on sign-in:** an "I'm not a robot" check (reCAPTCHA v2 or Turnstile) for devices that haven't signed in within 24 hours and after 3 wrong passwords, verified server-side *before* the password is checked; the device marker is an HMAC-signed httpOnly cookie.
- ✅ **Admin activity log** (Admin › Activity log): every staff sign-in, sign-out, failed sign-in and failed 2FA; every admin action with actor, IP and device; a middleware safety net that records any admin write that didn't log itself — including requests refused for missing permissions; and console pages viewed. Filter by admin, period and type, see per-admin totals, and export CSV (exports are themselves logged). Entries can't be edited or deleted.
- ✅ Four-eyes refund approval for dispute refunds.
- ✅ Production refuses to boot with mock providers or dev secrets.

## Input, output and files
- ✅ Pydantic validation on every input; money is `Decimal` with at most 2 dp, serialised as strings, and never touches floats.
- ✅ HTML is stripped from user text (`nh3`). React escapes output. JSON-LD is serialised with `<` escaped.
- ✅ SQL injection: the ORM uses bound parameters everywhere, and full-text tokens are sanitised to word characters.
- ✅ Image uploads are decoded with Pillow (extension and MIME aren't trusted), limited to 8 MB and 40 MP (decompression-bomb guard), then re-encoded to WebP, which strips EXIF/GPS and any embedded payload. They're stored under random keys. KYC documents go to private storage.
- ✅ KYC identifiers are Fernet-encrypted at rest. The API only ever returns them masked; admins can reveal them, and every reveal is audit-logged.

## Platform
- ✅ Security headers (nosniff, frame DENY, referrer policy; HSTS in staging/production; Permissions-Policy and a Content-Security-Policy on the frontend).
- ☑ Global API throttle per IP; per-action limits on messages, offers, reviews, reports and direct contacts.
- ☑ Structured logs never include passwords, tokens, OTPs or card data. Provider payloads are stored internally and never returned to clients.

## Findings and follow-ups (must be addressed before launch)
1. **Trusted proxy configuration:** ✅ `client_ip()` now ignores `X-Forwarded-For` unless the direct peer is in `TRUSTED_PROXY_CIDRS`, then walks the chain right-to-left. Set it to your load balancer CIDRs. Don't also enable uvicorn's `--proxy-headers`/`--forwarded-allow-ips` — the app does this itself. Production refuses to boot without it.
2. **Content Security Policy:** ✅ a strict header policy is set in `frontend/next.config.ts` (default-src, object-src, base-uri, form-action, frame-ancestors, connect/img/script allowlists). Next.js inline bootstrap requires `'unsafe-inline'`; a nonce-based CSP would force dynamic rendering and is incompatible with PPR/Cache Components. Revisit lengths/nonces or SRI when analytics/Sentry are added.
3. **Malware scanning** of uploads (e.g. ClamAV or the cloud provider's scanner) for KYC documents — still open.
4. **KYC identity checks** are manual review today. Integrate a licensed KYC provider (e.g. NIMC-backed NIN verification) before relying on the "Verified" badge at scale.
5. **Penetration test** by a third party before the first live transaction.
6. **NDPA 2023 compliance:** privacy copy now covers bank data and guarantors, but still appoint a DPO, keep a record of processing, implement a data-subject-request workflow (export and delete) and retention schedules.
7. **2FA for admins:** ✅ TOTP 2FA with single-use recovery codes, replay protection and a login challenge. Set `ADMIN_2FA_REQUIRED=true` in production (the boot guard enforces it); admins must enable 2FA from `/account` before using the admin API.

## Goods Flex and guarantor compliance checklist (pre-launch)

Implemented in code:

- ✅ **Mandatory guarantor:** no Goods Flex limit exists until a guarantor consents; one guarantor can cover at most `max_active_guarantees` customers (default 3).
- ✅ **Informed consent:** the guarantor sees the borrower's name, relationship, the amount being guaranteed and the expiry, and must tick an explicit consent box. We record the consent time, IP and BVN reference. The agreed amount is stored and caps the borrower's limit; a higher limit requires a fresh consent.
- ✅ **Withdrawal:** cancelling or revoking a guarantor immediately drops the borrower's limit to zero; the borrower is notified when a guarantor consents or declines.
- ✅ **Affordability:** limits come from six months of bank transactions, existing loan repayments, income stability and verification tiers; the statement snapshot is stored immutably for audit.
- ✅ **Transparency:** the exact down payment, financing charge, total payable and instalment schedule are shown before acceptance, with the lending partner's decision reference stored verbatim.
- ✅ **Open-banking consent:** bank access is read-only; the privacy policy explains the purpose, the provider, withdrawal and retention. The Mono adapter is server-side only (secret key never reaches the browser).
- ✅ **One plan at a time:** enforced in the service layer and by a partial unique index, which also limits over-indebtedness.

Still required before launch (owner: compliance/legal):

1. **FCCPC digital-lending review** of the lending partner's terms, charge disclosure, affordability rules, collections practices and complaint handling.
2. **NDPA 2023 review** of the bank-data and guarantor consent wording, lawful basis, retention periods and data-subject-request workflow.
3. **Guarantor legal review:** confirm the enforceability and required disclosures for guarantees under Nigerian law, including cooling-off and withdrawal rights.
4. **Partner contracts:** signed lender and open-banking agreements, including data-processing agreements and incident notification.
5. **Open-banking sandbox test** with Mono (`test_sk_` key) and a licensed lender sandbox before enabling either provider in production.


## Security audit — 6 Nov 2026

Automated guards added so these stay true (tests fail if they regress):

| Area | Status |
|---|---|
| Secrets | No keys in code or git history; only `NEXT_PUBLIC_SITE_URL`/`NEXT_PUBLIC_ADMIN_URL` reach the browser. Dev defaults are refused outside development. `.env*` ignored by git and Docker (frontend `.dockerignore` added). |
| Production config | Refuses to boot with: dev secrets, JWT secret < 32 chars, `*`/http CORS origins, http site/admin URLs, DB without `sslmode=require`, local file storage, mock payment/escrow/BNPL/bank/captcha providers, missing trusted-proxy CIDRs, admin 2FA off. |
| Admin routes | Every `/admin` route has a permission dependency (`test_every_admin_route_requires_a_permission`); all admin activity is logged. |
| Access control | Outsiders and the wrong party (buyer vs seller) get 403/404 on orders, chats, offers, payments, Flex applications, instalments, notifications and listings (`tests/test_access_control.py`). |
| Authentication | Argon2id hashing (auto re-hash on login), strong-password rule on register/reset/change/staff invite, timing-safe login for unknown emails, captcha for new devices / after failures, 2FA, rotating refresh tokens, JWT algorithm pinned to HS*. |
| Input & XSS | HTML stripped at the schema boundary (`CleanStr`) for names, addresses, notes; React escapes output; JSON-LD escaped; user URLs restricted to http(s). |
| Rate limiting | Global per-IP limit plus per-action limits on login, OTP, reset, 2FA, register, refresh, checkout, Flex apply, uploads, disputes, listings, KYC, messages, offers, reviews. |
| Headers | CSP, HSTS (prod), X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy, COOP; API responses `default-src 'none'`; auth/admin responses `no-store`; no `Server` header in production. |
| Debug | API docs/OpenAPI only in development/test; no debug mode; generic 500 errors; validation errors never echo input. |
| Client IP | The app trusts `X-Forwarded-For` only from `TRUSTED_PROXY_CIDRS`; uvicorn no longer runs with `--forwarded-allow-ips='*'` (which allowed IP spoofing to dodge rate limits). |
| Database | Parameterised queries only; 15 s statement timeout and 60 s idle-in-transaction timeout; append-only ledger/escrow events/audit log. Use a least-privilege app role (no superuser, no DDL) and run migrations with a separate role. |
| Dependencies | `pip-audit` and `pnpm audit`: no known vulnerabilities. Patch/minor updates applied; unused packages removed (zod, jsdom, testing-library, vite plugin). Major upgrades (ESLint 10, TypeScript 7) left for a separate change. |
| Escrow | Transitions only under row lock (enforced), money invariants checked before release/refund, idempotent settlement. |
| Goods Flex | Single lifecycle module with transition tables; duplicate/excess payments auto-refunded; one open payment per instalment; defaulted plans can still be paid off; overdue job uses row locks with skip-locked. |
