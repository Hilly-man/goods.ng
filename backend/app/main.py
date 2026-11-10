import hmac
import importlib
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.cache import cache, check_rate_limit
from app.core.config import settings
from app.core.db import engine
from app.core.deps import client_ip, rate_limit_identity
from app.core.errors import AppError, register_exception_handlers
from app.core.logging import RequestContextMiddleware, configure_logging

ROUTERS = [
    "auth", "users", "sellers", "categories", "products", "subscriptions", "messaging", "negotiation",
    "payments", "orders", "promotions", "bnpl", "reviews", "notifications", "admin", "staff", "stats", "recommendations", "ads",
    "marketing", "wallet",
]


def create_app() -> FastAPI:
    settings.validate_for_production()
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Goods.ng — Buy. Sell. Trade with Confidence.",
        # Interactive docs only in development/test — never in staging or production.
        docs_url="/docs" if settings.environment in ("development", "test") else None,
        redoc_url="/redoc" if settings.environment in ("development", "test") else None,
        openapi_url="/openapi.json" if settings.environment in ("development", "test") else None,
        debug=False,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Idempotency-Key", "X-Request-ID", "X-Anon-Id"],
    )

    @app.middleware("http")
    async def security_headers_and_throttle(request: Request, call_next):
        if request.url.path.startswith(settings.api_prefix) and not request.url.path.endswith("/webhook"):
            try:
                identity = rate_limit_identity(request)
                check_rate_limit(f"api:{identity}", settings.rate_limit_per_minute, 60)
                if not identity.startswith("ip:"):
                    # Coarse shared-IP ceiling: rotating X-Anon-Id must not bypass throttling,
                    # but a busy carrier NAT may legitimately host many users.
                    check_rate_limit(f"api-ip:{client_ip(request)}",
                                     settings.rate_limit_per_minute * settings.rate_limit_ip_multiplier, 60)
            except AppError as e:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=429, content={"error": {"code": e.code, "message": e.message}})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        path = request.url.path
        if (path.startswith(settings.api_prefix) or path.startswith("/media")) \
                and not response.headers.get("content-type", "").startswith("text/html"):
            # JSON and images never need to run scripts or be framed.
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        if path.startswith(f"{settings.api_prefix}/auth") or path.startswith(f"{settings.api_prefix}/admin"):
            response.headers.setdefault("Cache-Control", "no-store")
        if settings.environment in ("production", "staging"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response

    @app.middleware("http")
    async def admin_activity_log(request: Request, call_next):
        """Attach request context for audit entries, and record any admin write that didn't log itself."""
        from starlette.concurrency import run_in_threadpool

        from app.modules.audit import request_audit

        ctx = {"audited": False, "ip": client_ip(request), "ua": request.headers.get("user-agent")}
        token = request_audit.set(ctx)
        try:
            response = await call_next(request)
        finally:
            request_audit.reset(token)
        path = request.url.path
        if (request.method in ("POST", "PUT", "PATCH", "DELETE") and path.startswith(settings.api_prefix)
                and "/admin" in path and (not ctx["audited"] or response.status_code >= 400)):
            await run_in_threadpool(_record_unlogged_admin_request, request, response.status_code, ctx)
        return response

    register_exception_handlers(app)

    for name in ROUTERS:
        mod = importlib.import_module(f"app.modules.{name}.router")
        app.include_router(mod.router, prefix=settings.api_prefix)
    if settings.environment in ("development", "test"):
        from app.modules.dev.router import router as dev_router

        app.include_router(dev_router, prefix=settings.api_prefix)
        logging.getLogger("goodsng").warning("dev_routes_enabled_mock_providers_active")

    @app.api_route("/internal/cron", methods=["GET", "POST"])
    def internal_cron(request: Request, scope: str = "frequent"):
        """Run background jobs on hosts without a long-running worker (Vercel Cron / external scheduler)."""
        if settings.cron_secret:
            auth = request.headers.get("authorization", "")
            if not hmac.compare_digest(auth, f"Bearer {settings.cron_secret}"):
                raise HTTPException(status_code=401, detail="Invalid cron secret")
        elif settings.environment not in ("development", "test"):
            raise HTTPException(status_code=404, detail="Not found")

        from app.worker import run_job

        names = {
            "frequent": ["process_payouts", "auto_release_escrow", "expire_unpaid_orders", "expire_negotiations"],
            "daily": ["expire_subscriptions", "refresh_promotion_bumps", "bnpl_reminders", "purge_interest_signals",
                      "purge_deleted_listings", "purge_site_visits", "meta_capi_purchases"],
        }.get(scope)
        if not names:
            raise HTTPException(status_code=400, detail="Unknown scope")
        for name in names:
            run_job(name)
        return {"scope": scope, "ran": names}

    if settings.storage_backend == "local":
        Path(settings.local_media_dir).mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=settings.local_media_dir), name="media")

    @app.get("/health", tags=["ops"])
    def health():
        return {"status": "ok"}

    @app.get("/health/ready", tags=["ops"])
    def ready():
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        if settings.is_production:
            return {"status": "ready"}  # don't advertise internals publicly
        return {"status": "ready", "database": "ok", "cache": cache.backend,
                "providers": {"payment": settings.payment_provider, "escrow": settings.escrow_provider,
                              "bnpl": settings.bnpl_provider}}

    return app


def _record_unlogged_admin_request(request: Request, status: int, ctx: dict) -> None:
    """Safety net: an admin write with no explicit audit entry (or one that failed and was rolled back)."""
    from app.core.db import SessionLocal
    from app.core.security import decode_access_token
    from app.models import User
    from app.modules.audit import audit

    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        return
    try:
        claims = decode_access_token(auth[7:])
    except AppError:
        return
    if claims.get("role") == "user":
        return
    path = request.url.path
    try:
        with SessionLocal() as db:
            user = db.get(User, claims.get("sub"))
            if not user or not user.is_staff:
                return
            outcome = "success" if status < 400 else "denied" if status in (401, 403) else "failed"
            audit(db, user, f"request.{request.method.lower()}", "endpoint", path[len(settings.api_prefix):][:80],
                  {"status": status, "method": request.method, "path": path}, ctx.get("ip"),
                  category="api", outcome=outcome)
            db.commit()
    except Exception:  # never let logging break the response
        logging.getLogger("goodsng").exception("admin_activity_log_failed")


app = create_app()
