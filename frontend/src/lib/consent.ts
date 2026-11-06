/**
 * Cookie / tracking consent (Nigeria Data Protection Act). Nothing that tracks people across sites —
 * Meta Pixel, Google Ads, GA4 — loads until the visitor says yes to "marketing".
 */
export type Consent = { marketing: boolean; decided: boolean; at?: string };

const KEY = "gng_consent";
const EVENT = "gng-consent-change";
const UNDECIDED: Consent = { marketing: false, decided: false };
let cached: Consent | null = null;

export function readConsent(): Consent {
  if (typeof window === "undefined") return UNDECIDED;
  if (cached) return cached;
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || "null");
    cached = raw && typeof raw.marketing === "boolean" ? { marketing: raw.marketing, decided: true, at: raw.at } : UNDECIDED;
  } catch {
    cached = UNDECIDED;
  }
  return cached;
}

export function saveConsent(marketing: boolean) {
  cached = { marketing, decided: true, at: new Date().toISOString() };
  try { localStorage.setItem(KEY, JSON.stringify(cached)); } catch { /* private mode */ }
  window.dispatchEvent(new Event(EVENT));
  if (!marketing) {
    // Turning consent off takes effect immediately on the next page load (scripts aren't injected).
    try { document.cookie.split(";").forEach((c) => { const n = c.split("=")[0].trim(); if (/^(_fbp|_fbc|_ga|_gid|_gcl_)/.test(n)) document.cookie = `${n}=; Max-Age=0; path=/`; }); } catch { /* ignore */ }
  }
}

export function reopenConsent() {
  cached = { ...(cached ?? UNDECIDED), decided: false };
  window.dispatchEvent(new Event(EVENT));
}

export function subscribeConsent(cb: () => void) {
  const onStorage = (e: StorageEvent) => { if (e.key === KEY) { cached = null; cb(); } };
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", onStorage);
  return () => { window.removeEventListener(EVENT, cb); window.removeEventListener("storage", onStorage); };
}

export const SERVER_CONSENT = UNDECIDED;
