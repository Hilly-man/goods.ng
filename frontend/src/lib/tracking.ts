/**
 * Ad-platform events (Meta Pixel + Google tag), sent ONLY after marketing consent.
 *   view_item · contact · begin_checkout · purchase
 * Purchases carry event_id "purchase-<orderId>" so Meta de-duplicates them with the server-side event.
 */
import { readConsent } from "./consent";

type Item = { id: string; price?: number | string; name?: string };
type EventName = "view_item" | "contact" | "begin_checkout" | "purchase";
type W = Window & { fbq?: (...a: unknown[]) => void; gtag?: (...a: unknown[]) => void; __gngTrack?: { googleAdsSend?: string } };

const META: Record<EventName, string> = { view_item: "ViewContent", contact: "Contact", begin_checkout: "InitiateCheckout", purchase: "Purchase" };
const GOOGLE: Record<EventName, string> = { view_item: "view_item", contact: "generate_lead", begin_checkout: "begin_checkout", purchase: "purchase" };
const pending: [EventName, { items: Item[]; value?: number; orderId?: string }][] = [];

export function track(name: EventName, data: { items: Item[]; value?: number; orderId?: string }) {
  if (typeof window === "undefined" || !readConsent().marketing) return;
  const w = window as W;
  if (!w.fbq && !w.gtag) { pending.push([name, data]); return; } // scripts still loading
  const ids = data.items.map((i) => i.id);
  const value = data.value ?? data.items.reduce((n, i) => n + Number(i.price ?? 0), 0);
  const eventID = data.orderId ? `purchase-${data.orderId}` : undefined;
  w.fbq?.("track", META[name], { content_ids: ids, content_type: "product", value, currency: "NGN" }, eventID ? { eventID } : undefined);
  w.gtag?.("event", GOOGLE[name], {
    currency: "NGN", value, transaction_id: data.orderId,
    items: data.items.map((i) => ({ item_id: i.id, item_name: i.name, price: Number(i.price ?? 0) })),
  });
  if (name === "purchase" && w.__gngTrack?.googleAdsSend) {
    w.gtag?.("event", "conversion", { send_to: w.__gngTrack.googleAdsSend, value, currency: "NGN", transaction_id: data.orderId });
  }
}

/** Called by TrackingScripts once the platform scripts are ready. */
export function flushPending() {
  const queued = pending.splice(0);
  for (const [n, d] of queued) track(n, d);
}
