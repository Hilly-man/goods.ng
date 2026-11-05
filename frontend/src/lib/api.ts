"use client";

/**
 * Browser API client. Talks to the same-origin /api/v1 rewrite.
 * - Access token lives in memory only (never localStorage).
 * - Refresh token is an httpOnly cookie; refresh requests send the CSRF header.
 * - A 401 "token_expired" triggers one silent refresh + retry.
 */

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;
  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
  /** Field errors from 422 responses, keyed by field path. */
  get fieldErrors(): Record<string, string> {
    if (!Array.isArray(this.details)) return {};
    return Object.fromEntries(
      (this.details as { field: string; message: string }[]).map((d) => [d.field, d.message.replace(/^Value error, /, "")]),
    );
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
const listeners = new Set<(token: string | null) => void>();

export function setAccessToken(token: string | null) {
  accessToken = token;
  listeners.forEach((l) => l(token));
}
export function getAccessToken() {
  return accessToken;
}
export function onTokenChange(fn: (t: string | null) => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

const BASE = "/api/v1";
const CSRF = { "X-Requested-With": "goodsng" };

let inflight: Promise<{ access_token: string; user: unknown } | null> | null = null;

/** Single-flight: concurrent callers share one refresh request (refresh tokens rotate on every use). */
export function refreshSession(): Promise<{ access_token: string; user: unknown } | null> {
  inflight ??= (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, { method: "POST", headers: CSRF, credentials: "same-origin" });
      if (!res.ok) {
        setAccessToken(null);
        return null;
      }
      const body = await res.json();
      setAccessToken(body.access_token);
      return body;
    } finally {
      setTimeout(() => (inflight = null), 0);
    }
  })();
  return inflight;
}

async function tryRefresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = refreshSession()
      .then((b) => !!b)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

type Opts = Omit<RequestInit, "body"> & { body?: unknown; query?: Record<string, unknown>; retry?: boolean };

function buildQuery(query?: Record<string, unknown>) {
  if (!query) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === "" || v === false) continue;
    if (Array.isArray(v)) v.forEach((x) => sp.append(k, String(x)));
    else sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export async function api<T = unknown>(path: string, opts: Opts = {}): Promise<T> {
  const { body, query, retry = true, headers, ...rest } = opts;
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const h: Record<string, string> = { ...(headers as Record<string, string>) };
  if (accessToken) h.Authorization = `Bearer ${accessToken}`;
  if (body !== undefined && !isForm) h["Content-Type"] = "application/json";
  const res = await fetch(`${BASE}${path}${buildQuery(query)}`, {
    ...rest,
    headers: h,
    credentials: "same-origin",
    body: body === undefined ? undefined : isForm ? (body as FormData) : JSON.stringify(body),
  });
  if (res.status === 401 && retry && path !== "/auth/refresh") {
    const ok = await tryRefresh();
    if (ok) return api<T>(path, { ...opts, retry: false });
  }
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;
  if (!res.ok) {
    const err = data?.error ?? {};
    throw new ApiError(res.status, err.code ?? "error", err.message ?? "Something went wrong", err.details);
  }
  return data as T;
}

export const http = {
  get: <T>(p: string, query?: Record<string, unknown>) => api<T>(p, { method: "GET", query }),
  post: <T>(p: string, body?: unknown, headers?: Record<string, string>) => api<T>(p, { method: "POST", body, headers }),
  patch: <T>(p: string, body?: unknown) => api<T>(p, { method: "PATCH", body }),
  put: <T>(p: string, body?: unknown) => api<T>(p, { method: "PUT", body }),
  del: <T>(p: string) => api<T>(p, { method: "DELETE" }),
};

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) {
    const fe = Object.values(e.fieldErrors);
    return fe.length ? fe[0] : e.message;
  }
  return "Network error. Check your connection and try again.";
}

export { CSRF };
