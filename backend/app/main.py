import importlib
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.cache import cache, check_rate_limit
from app.core.config import settings
from app.core.db import engine
from app.core.deps import client_ip
from app.core.errors import AppError, register_exception_handlers
from app.core.logging import RequestContextMiddleware, configure_logging

ROUTERS = [
    "auth", "users", "sellers", "categories", "products", "subscriptions", "messaging", "negotiation",
    "payments", "orders", "bnpl", "reviews", "notifications", "admin",
]


def create_app() -> FastAPI:
    settings.validate_for_production()
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="Goods.ng — Buy. Sell. Trade with Confidence.",
        docs_url="/docs" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "Idempotency-Key", "X-Request-ID"],
    )

    @app.middleware("http")
    async def security_headers_and_throttle(request: Request, call_next):
        if request.url.path.startswith(settings.api_prefix) and not request.url.path.endswith("/webhook"):
            try:
                check_rate_limit(f"api:{client_ip(request)}", settings.rate_limit_per_minute, 60)
            except AppError as e:
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=429, content={"error": {"code": e.code, "message": e.message}})
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if settings.environment in ("production", "staging"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains")
        return response

    register_exception_handlers(app)

    for name in ROUTERS:
        mod = importlib.import_module(f"app.modules.{name}.router")
        app.include_router(mod.router, prefix=settings.api_prefix)
    if settings.environment in ("development", "test"):
        from app.modules.dev.router import router as dev_router

        app.include_router(dev_router, prefix=settings.api_prefix)
        logging.getLogger("goodsng").warning("dev_routes_enabled_mock_providers_active")

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
        return {"status": "ready", "database": "ok", "cache": cache.backend,
                "providers": {"payment": settings.payment_provider, "escrow": settings.escrow_provider,
                              "bnpl": settings.bnpl_provider}}

    return app


app = create_app()
