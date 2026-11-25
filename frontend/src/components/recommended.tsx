"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { anonHeaders, captureLanding, personalisationOff, setPersonalisation, trackSignal, type Signal } from "@/lib/interest";
import type { ProductCard } from "@/lib/types";
import { rememberViewedProduct } from "@/lib/search-history";
import { ProductCollection } from "./product-collection";
import { ProductGridSkeleton } from "./product-card";

/** Mounted once in the root layout: records where this visit came from (once per session). */
export function InterestCapture() {
  useEffect(() => { void captureLanding(); }, []);
  return null;
}

/** Records a search or listing view on Goods.ng. */
export function TrackSignal(props: Signal & { recentlyViewed?: ProductCard }) {
  const { kind, query, product_slug, category_slug } = props;
  const recentlyViewed = "recentlyViewed" in props ? props.recentlyViewed : undefined;
  useEffect(() => {
    if (!query && !product_slug && !category_slug) return;
    if (kind === "view" && recentlyViewed) rememberViewedProduct(recentlyViewed);
    void captureLanding().then(() => trackSignal({ kind, query, product_slug, category_slug }));
  }, [kind, query, product_slug, category_slug, recentlyViewed]);
  return null;
}

type ForYou = { personalised: boolean; items: ProductCard[] };

export function RecommendedForYou() {
  const { user, loading } = useAuth();
  const [data, setData] = useState<ForYou | null>(null);
  const [off, setOff] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (loading) return;
    let alive = true;
    const isOff = personalisationOff();
    // Resolve after an await so state updates never run synchronously inside the effect.
    captureLanding()
      .then(() => (isOff ? null : api<ForYou>("/recommendations/for-you", { method: "GET", headers: anonHeaders() })))
      .then((d) => { if (alive) { setOff(isOff); setData(d); } })
      .catch(() => { if (alive) setData(null); });
    return () => { alive = false; };
  }, [loading, user?.id, version]);

  if (off) {
    return (
      <section className="card flex flex-wrap items-center justify-between gap-3 p-4 text-sm">
        <span className="text-muted">Personalised recommendations are off.</span>
        <button type="button" className="font-semibold text-brand-700 hover:underline"
                onClick={() => { setPersonalisation(true); setVersion((v) => v + 1); }}>Turn on</button>
      </section>
    );
  }
  if (!data) {
    return (
      <section>
        <div className="mb-3 h-6 w-48 rounded skeleton" />
        <ProductGridSkeleton count={5} />
      </section>
    );
  }
  if (!data.items.length) return null;

  return (
    <section aria-labelledby="for-you">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div className="min-w-0">
          <h2 id="for-you" className="text-lg font-bold tracking-tight sm:text-xl">
            Recommended for you
          </h2>
          {!data.personalised && (
            <p className="text-sm text-muted">Popular right now — search or browse and we&apos;ll tailor this to you.</p>
          )}
        </div>
      </div>
      <ProductCollection items={data.items.slice(0, 10)} placement="for_you" />
    </section>
  );
}
