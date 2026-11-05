"""Lightweight load smoke test for the public read paths (no external tools needed).

    uv run python perf/smoke.py --base http://localhost:8000 --concurrency 20 --requests 400

Reports throughput and p50/p95/p99 latency per endpoint. For full load tests use k6/Locust in staging.
"""

import argparse
import asyncio
import statistics
import time

import httpx

PATHS = [
    "/api/v1/products/feed/home",
    "/api/v1/products?q=iphone",
    "/api/v1/products?category=phones-tablets&sort=price_asc",
    "/api/v1/products?state=Lagos&min_price=100000&max_price=2000000",
    "/api/v1/categories",
]


async def run(base: str, path: str, n: int, conc: int) -> dict:
    lat, errors = [], 0
    sem = asyncio.Semaphore(conc)
    async with httpx.AsyncClient(base_url=base, timeout=30) as c:
        async def one():
            nonlocal errors
            async with sem:
                t = time.perf_counter()
                r = await c.get(path, headers={"x-forwarded-for": f"10.0.{len(lat) % 250}.{len(lat) % 200}"})
                lat.append((time.perf_counter() - t) * 1000)
                errors += r.status_code >= 400
        start = time.perf_counter()
        await asyncio.gather(*(one() for _ in range(n)))
        dur = time.perf_counter() - start
    q = statistics.quantiles(lat, n=100)
    return {"path": path, "rps": round(n / dur), "p50": round(q[49]), "p95": round(q[94]), "p99": round(q[98]), "errors": errors}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--concurrency", type=int, default=20)
    ap.add_argument("--requests", type=int, default=400)
    a = ap.parse_args()
    print(f"{'endpoint':62} {'req/s':>6} {'p50':>5} {'p95':>5} {'p99':>5} {'err':>4}")
    for p in PATHS:
        r = await run(a.base, p, a.requests, a.concurrency)
        print(f"{r['path']:62} {r['rps']:>6} {r['p50']:>4}ms {r['p95']:>4}ms {r['p99']:>4}ms {r['errors']:>4}")


if __name__ == "__main__":
    asyncio.run(main())
