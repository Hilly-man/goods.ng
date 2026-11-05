from decimal import Decimal
from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (or a local .env in development)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "Goods.ng API"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    public_api_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: str = "postgresql+psycopg://localhost/goodsng_dev"
    redis_url: str | None = None

    # Auth
    jwt_secret: str = "dev-only-change-me-please-0123456789abcdef"
    jwt_algorithm: str = "HS256"
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
    mono_public_key: str | None = None
    mono_base_url: str = "https://api.withmono.com"

    # Notifications
    email_provider: Literal["console"] = "console"
    sms_provider: Literal["console"] = "console"

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    local_media_dir: str = "media"
    media_base_url: str = "/media"  # relative: served via the frontend rewrite; set to a CDN URL in production
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    max_upload_mb: int = 8

    # Marketplace economics (defaults; overridable through platform settings)
    platform_commission_rate: Decimal = Decimal("0.05")
    protection_fee_rate: Decimal = Decimal("0.015")
    protection_fee_cap: Decimal = Decimal("5000.00")
    offer_ttl_hours: int = 48
    accepted_offer_checkout_hours: int = 24
    unpaid_order_ttl_minutes: int = 60
    auto_release_days: int = 3

    rate_limit_per_minute: int = 240

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_for_production(self) -> None:
        """Refuse to boot production with development secrets or mock financial providers."""
        if self.environment not in ("production", "staging"):
            return
        problems = []
        if self.jwt_secret.startswith("dev-only"):
            problems.append("JWT_SECRET must be set")
        if self.otp_secret.startswith("dev-only"):
            problems.append("OTP_SECRET must be set")
        if self.data_encryption_key.startswith("dev-only"):
            problems.append("DATA_ENCRYPTION_KEY must be set")
        if self.environment == "production":
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
        if problems:
            raise RuntimeError("Unsafe configuration: " + "; ".join(problems))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
