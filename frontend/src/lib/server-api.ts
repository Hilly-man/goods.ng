import "server-only";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

export class NotFoundError extends Error {}

/** Server-side fetch for public data used in SSR pages. */
export async function serverGet<T>(path: string, query?: Record<string, string | string[] | undefined>): Promise<T> {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v === undefined || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, x));
    else sp.set(k, v);
  }
  const qs = sp.toString();
  const res = await fetch(`${API}/api/v1${path}${qs ? `?${qs}` : ""}`, {
    headers: { Accept: "application/json" },
  });
  if (res.status === 404) throw new NotFoundError(path);
  if (!res.ok) throw new Error(`API ${res.status} for ${path}`);
  return res.json() as Promise<T>;
}

export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
