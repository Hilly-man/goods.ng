import json
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env in development)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Goods.ng API"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    admin_url: str | None = None  # admin console origin, e.g. https://admin.goods.ng (used in staff invites)
    public_api_url: str = "http://localhost:8000"
    # NoDecode: accept both comma-separated values and a JSON array (platform env vars vary).
    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://localhost/goodsng_dev"
    # Per-process pool. Total connections = (pool_size + max_overflow) x workers x replicas,
    # so tune these against the database's max_connections (or PgBouncer's pool size).
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_statement_timeout_ms: int = 15000
    # Production must use an encrypted DB connection (sslmode=require/verify-full in DATABASE_URL).
    # Only set false for a private network where TLS is terminated elsewhere.
    database_require_ssl: bool = True
    redis_url: str | None = None

    # Auth
    jwt_secret: str = "dev-only-change-me-please-0123456789abcdef"
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"  # never "none"/asymmetric confusion
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    otp_ttl_minutes: int = 10
    otp_max_attempts: int = 5
    otp_secret: str = "dev-only-otp-pepper"
    # Fernet key for encrypting sensitive KYC data at rest. Generate with Fernet.generate_key().
    data_encryption_key: str = "dev-only:TZ_CTlCrVYuqeNWlywx7e9lU2Q4kOeByWp3nQ-2L25U="

    # Providers. "mock" providers are for development and automated testing only.
    payment_provider: Literal["mock", "paystack", "flutterwave"] = "mock"
    escrow_provider: Literal["mock"] = "mock"
    bnpl_provider: Literal["mock"] = "mock"
    bank_data_provider: Literal["mock", "mono"] = "mock"
    paystack_secret_key: str | None = None
    flutterwave_secret_key: str | None = None
    flutterwave_webhook_hash: str | None = None
    mock_provider_secret: str = "mock-webhook-signing-secret"
    # Mono Connect (open banking). Both keys come from the Mono dashboard.
    mono_secret_key: str | None = None
    # Google sign-in (OIDC). Without credentials, development/test use a clearly-labelled mock consent page
    # and staging/production hide the button.
    google_client_id: str | None = None
    google_client_secret: str | None = None
    # "I'm not a robot" check on sign-in for devices that haven't signed in within 24h (or after failed attempts).
    # recaptcha = Google reCAPTCHA v2 checkbox · turnstile = Cloudflare Turnstile · mock = dev-only · off = disabled
    captcha_provider: Literal["off", "mock", "recaptcha", "turnstile"] = "mock"
    captcha_site_key: str | None = None
    captcha_secret_key: str | None = None
    mono_public_key: str | None = None
    # Ads: Meta Conversions API token (secret — env only) and optional token protecting the product feeds.
    meta_capi_access_token: str | None = None
    meta_graph_version: str = "v21.0"
    feed_token: str | None = None
    mono_base_url: str = "https://api.withmono.com"

    # Notifications
    email_provider: Literal["console", "smtp", "postmark"] = "console"
    sms_provider: Literal["console", "termii"] = "console"
    termii_api_key: str | None = None
    termii_sender_id: str = "GoodsNG"
    termii_base_url: str = "https://api.ng.termii.com"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    postmark_server_token: str | None = None
    postmark_from: str | None = None

    # Storage
    storage_backend: Literal["local", "s3", "vercel-blob"] = "local"
    local_media_dir: str = "media"
    media_base_url: str = "/media"  # relative: served via the frontend rewrite; set to a CDN URL in production
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    max_upload_mb: int = 8
    # Storage cap per seller. Each photo is re-encoded to a bounded WebP, so a count cap also
    # bounds bytes. Includes photos on soft-deleted listings until they are hard-deleted.
    max_images_per_seller: int = 200
    # Soft-deleted listings (and their photo files) are purged by the worker after this many days.
    deleted_listing_retention_days: int = 30

    # Marketplace economics (defaults; overridable through platform settings)
    platform_commission_rate: Decimal = Decimal("0.05")
    protection_fee_rate: Decimal = Decimal("0.015")
    protection_fee_cap: Decimal = Decimal("5000.00")
    offer_ttl_hours: int = 48
    accepted_offer_checkout_hours: int = 24
    unpaid_order_ttl_minutes: int = 60
    auto_release_days: int = 3

    rate_limit_per_minute: int = 240
    # Coarse ceiling per public IP, as a multiple of the per-user/device limit. Keeps a client
    # from dodging limits by rotating its anonymous id, while still allowing shared carrier NAT.
    rate_limit_ip_multiplier: int = 20
    rate_limit_multiplier: int = 1  # dev/test only (e.g. 50 for E2E runs); must be 1 in staging/production

    # Only trust X-Forwarded-For when the direct peer is one of these CIDRs (your load balancer).
    # Empty means ignore the header entirely, which is the safe default.
    trusted_proxy_cidrs: Annotated[list[str], NoDecode] = []

    # Refuse to let admins use the admin API until TOTP 2FA is enabled. Required in production.
    admin_2fa_required: bool = False

    @field_validator("cors_origins", "trusted_proxy_cidrs", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                return json.loads(v)
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v):
        """Accept the URL shapes used by managed platforms (Render, Heroku, Railway).

        SQLAlchemy defaults a bare ``postgresql://`` URL to psycopg2, which this project does
        not install. Normalise it to the psycopg (v3) driver so a platform-provided
        connection string works without a manual edit.
        """
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return "postgresql+psycopg://" + v[len("postgres://"):]
            if v.startswith("postgresql://"):
                return "postgresql+psycopg://" + v[len("postgresql://"):]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_for_production(self) -> None:
        """Refuse to boot production with development secrets or mock financial providers."""
        if self.environment not in ("production", "staging"):
            return
        problems = []
        if self.rate_limit_multiplier != 1:
            problems.append("RATE_LIMIT_MULTIPLIER must be 1 outside development/test")
        if self.jwt_secret.startswith("dev-only"):
            problems.append("JWT_SECRET must be set")
        elif len(self.jwt_secret) < 32:
            problems.append("JWT_SECRET must be at least 32 random characters")
        if any(o.strip() == "*" or not o.startswith("https://") for o in self.cors_origins):
            problems.append("CORS_ORIGINS must list explicit https:// origins (no '*')")
        if not self.frontend_url.startswith("https://"):
            problems.append("FRONTEND_URL must be https://")
        if self.admin_url and not self.admin_url.startswith("https://"):
            problems.append("ADMIN_URL must be https://")
        if self.otp_secret.startswith("dev-only"):
            problems.append("OTP_SECRET must be set")
        if self.data_encryption_key.startswith("dev-only"):
            problems.append("DATA_ENCRYPTION_KEY must be set")
        if self.environment == "production":
            if self.database_require_ssl and not any(m in self.database_url for m in ("sslmode=require", "sslmode=verify-full", "sslmode=verify-ca")):
                problems.append("DATABASE_URL must use sslmode=require (or verify-full) in production")
            if self.storage_backend != "s3" or not self.s3_bucket:
                problems.append("STORAGE_BACKEND=s3 with S3_BUCKET is required in production (durable, private KYC storage)")
            if not self.redis_url:
                problems.append("REDIS_URL is required in production (shared rate limiting and cache)")
            if self.payment_provider == "mock":
                problems.append("PAYMENT_PROVIDER cannot be 'mock' in production")
            if self.escrow_provider == "mock":
                problems.append("A licensed escrow partner integration is required in production")
            if self.bnpl_provider == "mock":
                problems.append("A licensed financing partner integration is required in production")
            if self.bank_data_provider == "mock":
                problems.append("A real open-banking provider is required in production")
            if self.bank_data_provider == "mono" and not self.mono_secret_key:
                problems.append("MONO_SECRET_KEY is required when BANK_DATA_PROVIDER=mono")
            if self.captcha_provider in ("mock", "off"):
                problems.append("CAPTCHA_PROVIDER must be 'recaptcha' or 'turnstile' in production")
            elif not (self.captcha_site_key and self.captcha_secret_key):
                problems.append("CAPTCHA_SITE_KEY and CAPTCHA_SECRET_KEY are required for the captcha provider")
            if not self.trusted_proxy_cidrs:
                problems.append("TRUSTED_PROXY_CIDRS must list your load balancer CIDRs in production")
            if not self.admin_2fa_required:
                problems.append("ADMIN_2FA_REQUIRED must be true in production")
            if self.sms_provider == "console":
                problems.append("SMS_PROVIDER must be 'termii' in production")
            elif self.sms_provider == "termii" and not self.termii_api_key:
                problems.append("TERMII_API_KEY is required when SMS_PROVIDER=termii")
            if self.email_provider == "console":
                problems.append("EMAIL_PROVIDER must be 'smtp' or 'postmark' in production")
            elif self.email_provider == "smtp" and not (self.smtp_host and self.smtp_from):
                problems.append("SMTP_HOST and SMTP_FROM are required when EMAIL_PROVIDER=smtp")
            elif self.email_provider == "postmark" and not self.postmark_server_token:
                problems.append("POSTMARK_SERVER_TOKEN is required when EMAIL_PROVIDER=postmark")
        if problems:
            raise RuntimeError("Unsafe configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
