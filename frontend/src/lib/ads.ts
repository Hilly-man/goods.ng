/**
 * Sponsored-placement measurement. Impressions (≥50% of the card visible) and clicks are batched and sent
 * every few seconds, and on page hide. The API de-duplicates impressions per viewer per hour.
 */
import { anonHeaders, anonId } from "./interest";

export type AdPlacement = "search" | "category" | "item" | "for_you" | "home";
type Ev = { kind: "impression" | "click"; placement: AdPlacement; product_id: string };

const queue: Ev[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;
const seen = new Set<string>();

function flush() {
  if (timer) { clearTimeout(timer); timer = null; }
  if (!queue.length) return;
  const events = queue.splice(0, 50);
  void fetch("/api/v1/ads/events", {
    method: "POST", keepalive: true, credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...anonHeaders() },
    body: JSON.stringify({ events, anon_id: anonId() }),
  }).catch(() => {});
  if (queue.length) flush();
}

if (typeof window !== "undefined") {
  window.addEventListener("pagehide", flush);
  document.addEventListener("visibilitychange", () => document.visibilityState === "hidden" && flush());
}

export function trackAd(ev: Ev) {
  if (ev.kind === "impression") {
    const k = `${ev.placement}:${ev.product_id}`;
    if (seen.has(k)) return; // once per page view
    seen.add(k);
  }
  queue.push(ev);
  if (ev.kind === "click") flush();
  else if (!timer) timer = setTimeout(flush, 3000);
}
