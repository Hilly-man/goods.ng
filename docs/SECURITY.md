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
- ✅ Four-eyes refund approval for dispute refunds.
- ✅ Production refuses to boot with mock providers or dev secrets.

## Input, output and files
- ✅ Pydantic validation on every input; money is `Decimal` with at most 2 dp, serialised as strings, and never touches floats.
- ✅ HTML is stripped from user text (`nh3`). React escapes output. JSON-LD is serialised with `<` escaped.
- ✅ SQL injection: the ORM uses bound parameters everywhere, and full-text tokens are sanitised to word characters.
- ✅ Image uploads are decoded with Pillow (extension and MIME aren't trusted), limited to 8 MB and 40 MP (decompression-bomb guard), then re-encoded to WebP, which strips EXIF/GPS and any embedded payload. They're stored under random keys. KYC documents go to private storage.
- ✅ KYC identifiers are Fernet-encrypted at rest. The API only ever returns them masked; admins can reveal them, and every reveal is audit-logged.

## Platform
- ✅ Security headers (nosniff, frame DENY, referrer policy; HSTS in staging/production; Permissions-Policy on the frontend).
- ☑ Global API throttle per IP; per-action limits on messages, offers, reviews, reports and direct contacts.
- ☑ Structured logs never include passwords, tokens, OTPs or card data. Provider payloads are stored internally and never returned to clients.

## Findings and follow-ups (must be addressed before launch)
1. **Trusted proxy configuration:** `client_ip()` trusts `X-Forwarded-For`. In production, restrict this to your load balancer (uvicorn `--forwarded-allow-ips` set to its CIDR, not `*`). Otherwise an attacker can rotate IPs to evade rate limits.
2. **Content Security Policy** isn't set yet. Add a CSP with nonces in a Next.js `proxy.ts` once third-party scripts (analytics, Sentry) are decided.
3. **Malware scanning** of uploads (e.g. ClamAV or the cloud provider's scanner) for KYC documents.
4. **KYC identity checks** are manual review today. Integrate a licensed KYC provider (e.g. NIMC-backed NIN verification) before relying on the "Verified" badge at scale.
5. **Penetration test** by a third party before the first live transaction.
6. **NDPA 2023 compliance:** appoint a DPO, keep a record of processing, implement a data-subject-request workflow (export and delete) and retention schedules.
7. **2FA for admins** (TOTP or WebAuthn) is not implemented yet and is strongly recommended before staff accounts go live.

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
