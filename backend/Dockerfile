# Goods.ng API — production image
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN useradd --system --uid 10001 app && chown -R app /app
USER app
ENV PATH="/app/.venv/bin:$PATH" PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
# Migrations run as a separate release step (see docs/DEPLOYMENT.md), never on every container start.
# No --proxy-headers: the app resolves the real client IP itself and only trusts X-Forwarded-For from
# TRUSTED_PROXY_CIDRS (your load balancer). Trusting it from '*' would let anyone spoof their IP and dodge rate limits.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-2} --no-server-header"]
