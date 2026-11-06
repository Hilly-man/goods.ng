"use client";

import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { anonHeaders, captureLanding, clearHistory, personalisationOff, setPersonalisation, trackSignal, type Signal } from "@/lib/interest";
import type { ProductCard } from "@/lib/types";
import { ProductCollection } from "./product-collection";
import { ProductGridSkeleton } from "./product-card";

/** Mounted once in the root layout: records where this visit came from (once per session). */
export function InterestCapture() {
  useEffect(() => { void captureLanding(); }, []);
  return null;
}

/** Records a search or listing view on Goods.ng. */
export function TrackSignal(props: Signal) {
  const { kind, query, product_slug, category_slug } = props;
  useEffect(() => {
    if (!query && !product_slug && !category_slug) return;
    void captureLanding().then(() => trackSignal({ kind, query, product_slug, category_slug }));
  }, [kind, query, product_slug, category_slug]);
  return null;
}

type ForYou = { personalised: boolean; reasons: { text: string; source: string }[]; items: ProductCard[] };

const SOURCE_DOT: Record<string, string> = {
  google: "bg-[#4285f4]", bing: "bg-[#00809d]", facebook: "bg-[#1877f2]", instagram: "bg-[#e1306c]",
  tiktok: "bg-black", x: "bg-black", whatsapp: "bg-[#25d366]", youtube: "bg-[#ff0000]",
};

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
          <h2 id="for-you" className="flex items-center gap-2 text-lg font-bold tracking-tight sm:text-xl">
            <Sparkles className="size-5 text-accent-500" />Recommended for you
          </h2>
          {data.personalised ? (
            <div className="mt-1.5 flex flex-wrap gap-1.5">
              {data.reasons.map((r) => (
                <span key={r.text} className="inline-flex items-center gap-1.5 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-medium text-brand-800 ring-1 ring-brand-100">
                  <span className={`size-1.5 rounded-full ${SOURCE_DOT[r.source] ?? "bg-brand-600"}`} />{r.text}
                </span>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted">Popular right now — search or browse and we&apos;ll tailor this to you.</p>
          )}
        </div>
        {data.personalised && (
          <div className="flex shrink-0 items-center gap-3 text-xs font-semibold">
            <button type="button" className="text-muted hover:text-ink hover:underline"
                    onClick={() => { void clearHistory().finally(() => setVersion((v) => v + 1)); }}>
              Clear history
            </button>
            <button type="button" className="inline-flex items-center gap-1 text-muted hover:text-ink hover:underline"
                    onClick={() => { void clearHistory().finally(() => { setPersonalisation(false); setVersion((v) => v + 1); }); }}>
              <X className="size-3.5" />Turn off
            </button>
          </div>
        )}
      </div>
      <ProductCollection items={data.items.slice(0, 10)} placement="for_you" />
    </section>
  );
}
