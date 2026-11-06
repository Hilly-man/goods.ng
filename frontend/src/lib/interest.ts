/**
 * First-party interest signals for "Recommended for you".
 *
 * What we capture (and only this):
 *  - searches typed into Goods.ng and listings opened on Goods.ng
 *  - when a visit *arrives* from another site: which site (from the referrer or utm_source / click-id
 *    params), the UTM/ad keyword or campaign that link carried, and the page landed on.
 * We can't — and don't try to — read anyone's history on Google, Facebook, TikTok, Instagram, etc.
 *
 * Visitors can switch personalisation off (stored locally) and clear their history. Browsers sending
 * Global Privacy Control don't get off-site (landing) capture.
 */
import { api } from "./api";

const ANON_KEY = "gng_aid";
const OFF_KEY = "gng_personalise_off";
const LANDED_KEY = "gng_landing_done";

export type Source =
  | "goods" | "google" | "bing" | "yahoo" | "duckduckgo" | "facebook" | "instagram" | "tiktok" | "x"
  | "whatsapp" | "youtube" | "other";

export type Signal = {
  kind: "search" | "view" | "landing";
  source?: Source;
  query?: string;
  campaign?: string;
  product_slug?: string;
  category_slug?: string;
};

const canStore = () => typeof window !== "undefined" && "localStorage" in window;

export function anonId(): string | null {
  if (!canStore()) return null;
  try {
    let id = localStorage.getItem(ANON_KEY);
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem(ANON_KEY, id);
    }
    return id;
  } catch {
    return null;
  }
}

export function personalisationOff(): boolean {
  if (!canStore()) return false;
  try { return localStorage.getItem(OFF_KEY) === "1"; } catch { return false; }
}

export function setPersonalisation(on: boolean) {
  try {
    if (on) localStorage.removeItem(OFF_KEY);
    else localStorage.setItem(OFF_KEY, "1");
  } catch { /* storage blocked */ }
}

export function anonHeaders(): Record<string, string> {
  const id = anonId();
  return id ? { "X-Anon-Id": id } : {};
}

export function trackSignal(sig: Signal): Promise<void> {
  if (personalisationOff()) return Promise.resolve();
  return api("/recommendations/signals", { method: "POST", body: sig, headers: anonHeaders() })
    .then(() => undefined)
    .catch(() => undefined);
}

export async function clearHistory(): Promise<void> {
  await api("/recommendations/history", { method: "DELETE", headers: anonHeaders() });
}

/* ---------- landing capture ---------- */

const HOSTS: [RegExp, Source][] = [
  [/(^|\.)google\./, "google"],
  [/(^|\.)bing\.com$/, "bing"],
  [/(^|\.)yahoo\./, "yahoo"],
  [/(^|\.)duckduckgo\.com$/, "duckduckgo"],
  [/(^|\.)(facebook\.com|fb\.com|fb\.me|m\.facebook\.com|l\.facebook\.com)$/, "facebook"],
  [/(^|\.)(instagram\.com|l\.instagram\.com)$/, "instagram"],
  [/(^|\.)tiktok\.com$/, "tiktok"],
  [/(^|\.)(x\.com|twitter\.com|t\.co)$/, "x"],
  [/(^|\.)(whatsapp\.com|wa\.me)$/, "whatsapp"],
  [/(^|\.)(youtube\.com|youtu\.be)$/, "youtube"],
];
const UTM: Record<string, Source> = {
  google: "google", adwords: "google", bing: "bing", microsoft: "bing", yahoo: "yahoo", duckduckgo: "duckduckgo",
  facebook: "facebook", fb: "facebook", meta: "facebook", instagram: "instagram", ig: "instagram",
  tiktok: "tiktok", twitter: "x", x: "x", whatsapp: "whatsapp", wa: "whatsapp", youtube: "youtube",
};

export function detectSource(referrer: string, params: URLSearchParams, ownHost: string): Source | null {
  const utm = params.get("utm_source")?.toLowerCase().trim();
  if (utm) return UTM[utm] ?? "other";
  if (params.has("gclid") || params.has("gbraid") || params.has("wbraid")) return "google";
  if (params.has("msclkid")) return "bing";
  if (params.has("ttclid")) return "tiktok";
  if (params.has("fbclid")) return "facebook";
  if (!referrer) return null;
  let host: string;
  try { host = new URL(referrer).hostname.toLowerCase(); } catch { return null; }
  if (host === ownHost || host.endsWith(`.${ownHost.replace(/^www\./, "")}`)) return null;
  return HOSTS.find(([re]) => re.test(host))?.[1] ?? "other";
}

export function landingSignal(href: string, referrer: string): Signal | null {
  const url = new URL(href);
  const params = url.searchParams;
  const source = detectSource(referrer, params, url.hostname);
  if (!source) return null;
  const query = (params.get("utm_term") || params.get("q") || "").slice(0, 120) || undefined;
  const campaign = (params.get("utm_campaign") || "").slice(0, 120) || undefined;
  const item = url.pathname.match(/^\/item\/([^/]+)/)?.[1];
  const cat = url.pathname.match(/^\/c\/([^/]+)/)?.[1];
  if (!query && !item && !cat) return null; // nothing to learn from (e.g. landed on the home page)
  return {
    kind: "landing", source, query, campaign,
    product_slug: item ? decodeURIComponent(item) : undefined,
    category_slug: cat ? decodeURIComponent(cat) : undefined,
  };
}

let landing: Promise<void> | null = null;

/** Runs once per browser session; other code can await it so the first recommendations already use it. */
export function captureLanding(): Promise<void> {
  if (landing) return landing;
  landing = (async () => {
    if (typeof window === "undefined" || personalisationOff()) return;
    const gpc = (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl;
    if (gpc) return;
    try {
      if (sessionStorage.getItem(LANDED_KEY)) return;
      sessionStorage.setItem(LANDED_KEY, "1");
    } catch { /* storage blocked: still try once */ }
    const sig = landingSignal(window.location.href, document.referrer);
    if (sig) await trackSignal(sig);
  })();
  return landing;
}
