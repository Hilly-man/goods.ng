"use client";

import { useEffect, useRef, useState } from "react";
import { BadgeCheck, MapPin, PackageCheck, Sparkles, Store, Tag } from "lucide-react";
import { http } from "@/lib/api";
import { usePolling } from "@/lib/hooks";

export type PublicStats = {
  live_ads: number;
  new_ads_24h: number;
  sellers: number;
  verified_sellers: number;
  completed_orders: number;
  categories: number;
  states_with_ads: number;
  cities_with_ads: number;
  updated_at: string;
};

const POLL_MS = 15_000;

/** Counts toward `value` whenever it changes, so live updates are visible rather than a silent swap. */
function CountUp({ value }: { value: number }) {
  const [shown, setShown] = useState(value);
  const from = useRef(value);
  useEffect(() => {
    const start = from.current;
    if (start === value) return;
    const t0 = performance.now();
    let raf = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - t0) / 800);
      const eased = 1 - Math.pow(1 - k, 3);
      setShown(Math.round(start + (value - start) * eased));
      if (k < 1) raf = requestAnimationFrame(step);
      else from.current = value;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return <>{shown.toLocaleString("en-US")}</>;
}

export function LiveStats({ initial }: { initial: PublicStats }) {
  const [s, setS] = useState(initial);
  const [pulse, setPulse] = useState(false);
  const latest = useRef(initial);

  usePolling(() => {
    http.get<PublicStats>("/stats/public").then((next) => {
      const prev = latest.current;
      if (prev.live_ads !== next.live_ads || prev.completed_orders !== next.completed_orders || prev.sellers !== next.sellers) {
        setPulse(true);
        setTimeout(() => setPulse(false), 1200);
      }
      latest.current = next;
      setS(next);
    }).catch(() => { /* keep last good numbers */ });
  }, POLL_MS);

  const items = [
    { icon: Tag, value: s.live_ads, label: "live ads", note: `+${s.new_ads_24h.toLocaleString("en-US")} in the last 24h` },
    { icon: Store, value: s.sellers, label: "sellers", note: `${s.verified_sellers.toLocaleString("en-US")} verified` },
    { icon: PackageCheck, value: s.completed_orders, label: "protected orders completed", note: "paid safely through Goods.ng" },
    { icon: MapPin, value: s.cities_with_ads, label: "cities with ads", note: `across ${s.states_with_ads} state${s.states_with_ads === 1 ? "" : "s"}` },
  ];

  return (
    <section aria-label="Goods.ng in numbers">
      <p className="mb-3 flex items-center justify-center gap-2 text-sm font-semibold text-muted">
        <span className="relative flex size-2.5">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-brand-500 opacity-75" />
          <span className="relative inline-flex size-2.5 rounded-full bg-brand-600" />
        </span>
        Live from the marketplace
        <span className="sr-only">— figures refresh automatically</span>
      </p>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-live="polite">
        {items.map((it) => (
          <div key={it.label} className={`card p-4 text-center transition-shadow duration-700 sm:p-5 ${pulse ? "ring-2 ring-brand-400" : ""}`}>
            <it.icon className="mx-auto size-5 text-brand-600" />
            <p className="mt-1.5 text-2xl font-extrabold tabular-nums text-brand-800 sm:text-3xl"><CountUp value={it.value} /></p>
            <p className="text-sm font-medium">{it.label}</p>
            <p className="mt-0.5 text-xs text-muted">{it.note}</p>
          </div>
        ))}
      </div>
      <p className="mt-2 flex items-center justify-center gap-1.5 text-xs text-muted">
        <Sparkles className="size-3.5" />Real counts from our database, updated every few seconds · <BadgeCheck className="size-3.5" />{s.categories} categories
      </p>
    </section>
  );
}
