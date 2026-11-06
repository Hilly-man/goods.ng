"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, useSyncExternalStore } from "react";
import { Cookie } from "lucide-react";
import { http } from "@/lib/api";
import { readConsent, reopenConsent, saveConsent, SERVER_CONSENT, subscribeConsent } from "@/lib/consent";
import { flushPending } from "@/lib/tracking";

function useConsent() {
  return useSyncExternalStore(subscribeConsent, readConsent, () => SERVER_CONSENT);
}

/** Bottom banner shown until the visitor chooses. Tracking scripts stay off until they accept marketing. */
export function ConsentBanner() {
  const consent = useConsent();
  const pathname = usePathname();
  const [hydrated, setHydrated] = useState(false);
  const [choosing, setChoosing] = useState(false);
  const [marketing, setMarketing] = useState(true);
  useEffect(() => { void Promise.resolve().then(() => setHydrated(true)); }, []);
  if (!hydrated || consent.decided || pathname.startsWith("/admin")) return null;

  return (
    <div role="dialog" aria-label="Cookie preferences"
      className="fixed inset-x-2 bottom-20 z-50 mx-auto max-w-2xl rounded-2xl bg-white p-4 shadow-2xl ring-1 ring-line sm:bottom-4 sm:p-5">
      <div className="flex gap-3">
        <Cookie className="mt-0.5 size-5 shrink-0 text-accent-600" />
        <div className="min-w-0 flex-1 text-sm">
          <p className="font-semibold">We use cookies</p>
          <p className="mt-1 text-ink/80">
            Necessary cookies keep you signed in and secure. With your permission we also use marketing cookies (Meta and Google)
            to measure our ads and show you relevant listings. <Link href="/privacy#cookies" className="font-semibold text-brand-700 underline">Learn more</Link>
          </p>
          {choosing && (
            <div className="mt-3 space-y-2 rounded-xl bg-canvas p-3">
              <label className="flex items-start gap-2"><input type="checkbox" checked disabled className="mt-0.5" /><span><b>Necessary</b> — sign-in, security, your basket. Always on.</span></label>
              <label className="flex items-start gap-2"><input type="checkbox" checked={marketing} onChange={(e) => setMarketing(e.target.checked)} className="mt-0.5" /><span><b>Marketing</b> — Meta Pixel and Google tags for ad measurement.</span></label>
            </div>
          )}
          <div className="mt-3 flex flex-wrap gap-2">
            {choosing ? (
              <button type="button" onClick={() => saveConsent(marketing)} className="h-10 rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white hover:bg-brand-800">Save choices</button>
            ) : (
              <>
                <button type="button" onClick={() => saveConsent(true)} className="h-10 rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white hover:bg-brand-800">Accept all</button>
                <button type="button" onClick={() => saveConsent(false)} className="h-10 rounded-lg px-4 text-sm font-semibold ring-1 ring-line hover:bg-canvas">Only necessary</button>
                <button type="button" onClick={() => setChoosing(true)} className="h-10 rounded-lg px-3 text-sm font-semibold text-brand-700 hover:underline">Choose</button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Footer link to change the choice later. */
export function CookieSettingsLink({ className = "" }: { className?: string }) {
  return <button type="button" onClick={reopenConsent} className={className}>Cookie settings</button>;
}

type Cfg = { meta_pixel_id: string | null; ga4_id: string | null; google_ads_id: string | null; google_ads_purchase_label: string | null };
type W = Window & { fbq?: (...a: unknown[]) => void; _fbq?: unknown; dataLayer?: unknown[]; gtag?: (...a: unknown[]) => void;
  __gngTrack?: { googleAdsSend?: string } };

function inject(src: string) {
  if (document.querySelector(`script[src="${src}"]`)) return;
  const s = document.createElement("script");
  s.async = true;
  s.src = src;
  document.head.appendChild(s);
}

/** Loads Meta Pixel / Google tag only with marketing consent and only if IDs are configured in admin. */
export function TrackingScripts() {
  const consent = useConsent();
  const pathname = usePathname();
  const [cfg, setCfg] = useState<Cfg | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!consent.marketing || cfg) return;
    let alive = true;
    http.get<Cfg>("/tracking/config").then((c) => { if (alive) setCfg(c); }).catch(() => {});
    return () => { alive = false; };
  }, [consent.marketing, cfg]);

  useEffect(() => {
    if (!consent.marketing || !cfg || ready) return;
    const w = window as W;
    if (cfg.meta_pixel_id && !w.fbq) {
      // Meta's official Pixel bootstrap: queue calls until fbevents.js has loaded.
      type Fbq = ((...a: unknown[]) => void) & { callMethod?: (...a: unknown[]) => void; queue: unknown[]; push: unknown; loaded: boolean; version: string };
      const fbq = ((...args: unknown[]) => { if (fbq.callMethod) fbq.callMethod(...args); else fbq.queue.push(args); }) as Fbq;
      Object.assign(fbq, { push: fbq, loaded: true, version: "2.0", queue: [] });
      w.fbq = fbq;
      w._fbq = fbq;
      inject("https://connect.facebook.net/en_US/fbevents.js");
      w.fbq!("init", cfg.meta_pixel_id);
    }
    const gIds = [cfg.ga4_id, cfg.google_ads_id].filter(Boolean) as string[];
    if (gIds.length && !w.gtag) {
      w.dataLayer = w.dataLayer || [];
      w.gtag = function (...args: unknown[]) { w.dataLayer!.push(args); };
      w.gtag("js", new Date());
      for (const id of gIds) w.gtag("config", id, { send_page_view: false });
      inject(`https://www.googletagmanager.com/gtag/js?id=${gIds[0]}`);
      if (cfg.google_ads_id && cfg.google_ads_purchase_label) w.__gngTrack = { googleAdsSend: `${cfg.google_ads_id}/${cfg.google_ads_purchase_label}` };
    }
    void Promise.resolve().then(() => setReady(true));
    flushPending();
  }, [consent.marketing, cfg, ready]);

  // Page views on every client-side navigation.
  useEffect(() => {
    if (!ready || !consent.marketing) return;
    const w = window as W;
    w.fbq?.("track", "PageView");
    w.gtag?.("event", "page_view", { page_path: pathname });
  }, [ready, consent.marketing, pathname]);

  return null;
}

/** Fire one ad event when a page mounts (e.g. view_item on an item page). */
export function TrackEvent({ name, items, value, orderId }: { name: "view_item" | "begin_checkout" | "purchase"; items: { id: string; price?: string | number; name?: string }[]; value?: number; orderId?: string }) {
  const key = `${name}:${orderId ?? items.map((i) => i.id).join(",")}`;
  useEffect(() => {
    if (name === "purchase") {
      try { if (sessionStorage.getItem(`gng_ev:${key}`)) return; sessionStorage.setItem(`gng_ev:${key}`, "1"); } catch { /* ignore */ }
    }
    void import("@/lib/tracking").then(({ track }) => track(name, { items, value, orderId }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return null;
}
