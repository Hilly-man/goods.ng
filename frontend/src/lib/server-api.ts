import "server-only";

const rawApi = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
// Accept both a full URL and a Render private-network "host:port" value.
const API = (/^https?:\/\//i.test(rawApi) ? rawApi : `http://${rawApi}`).replace(/\/+$/, "");

export class NotFoundError extends Error {}

const ATTEMPTS = 3;
const TIMEOUT_MS = 12000;

/**
 * Server-side fetch for public data used in SSR pages.
 *
 * Render (and other free/hobby hosts) can cold-start slowly. A single failed fetch would otherwise
 * surface the root error page, so time out, retry network/5xx errors, and only give up after three
 * attempts. 4xx responses are not retried.
 */
export async function serverGet<T>(path: string, query?: Record<string, string | string[] | undefined>): Promise<T> {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v === undefined || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x));
    else sp.set(k, v);
  }
  const qs = sp.toString();
  const url = `${API}/api/v1${path}${qs ? `?${qs}` : ""}`;
  let last: Error | null = null;
  for (let attempt = 0; attempt < ATTEMPTS; attempt++) {
    try {
      const res = await fetch(url, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (res.status === 404) throw new NotFoundError(path);
      if (res.ok) return res.json() as Promise<T>;
      if (res.status < 500) throw new Error(`API ${res.status} for ${path}`);
      last = new Error(`API ${res.status} for ${path}`);
    } catch (e) {
      if (e instanceof NotFoundError) throw e;
      last = e instanceof Error ? e : new Error(String(e));
    }
    if (attempt < ATTEMPTS - 1) {
      await new Promise((resolve) => setTimeout(resolve, 400 * (attempt + 1)));
    }
  }
  throw last ?? new Error(`API request failed for ${path}`);
}

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
