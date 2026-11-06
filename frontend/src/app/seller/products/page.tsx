"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpToLine, Eye, Megaphone, MessageCircle, MousePointerClick, Package, Pencil, PlusCircle, Sparkles } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { Badge, ButtonLink, EmptyState, PageLoader, Tabs, useToast } from "@/components/ui";
import { ProductThumb } from "@/components/product-card";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { naira, titleCase } from "@/lib/format";
import type { Page, SellerProductRow } from "@/lib/types";

type AdSummary = {
  days: number; impressions: number; clicks: number; ctr: number; eligible_listings: number; live_listings: number;
  bumps: { premium: boolean; allowed: number; used: number; remaining: number };
  from_ads?: { visits: number; orders: number; attribution_days: number };
  quality_bar: { min_photos: number; min_description: number };
};

/** How Premium sponsored placements are performing, and today's bumps. */
function SponsoredCard({ s }: { s: AdSummary }) {
  if (!s.bumps.premium) {
    return (
      <div className="card mb-3 flex flex-wrap items-center gap-3 p-4">
        <Megaphone className="size-5 text-accent-600" />
        <p className="flex-1 text-sm"><b>Get more buyers:</b> Premium listings rank higher in search, get extra <b>TOP</b> spots in search, on item pages and in recommendations, and can be bumped to the top daily.</p>
        <ButtonLink href="/premium" size="sm" variant="accent">See Premium</ButtonLink>
      </div>
    );
  }
  const missing = s.live_listings - s.eligible_listings;
  return (
    <div className="card mb-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex items-center gap-2 font-semibold"><Megaphone className="size-4 text-accent-600" />TOP spot performance <span className="text-xs font-normal text-muted">· last {s.days} days</span></h2>
        <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-800">{s.bumps.remaining} of {s.bumps.allowed} bump{s.bumps.allowed === 1 ? "" : "s"} left today</span>
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-center sm:grid-cols-5">
        {[["Times shown", s.impressions.toLocaleString()], ["Clicks", s.clicks.toLocaleString()], ["Click rate", `${s.ctr}%`],
          ["Visits from Google & Facebook ads", (s.from_ads?.visits ?? 0).toLocaleString()], ["Orders from those visits", (s.from_ads?.orders ?? 0).toLocaleString()]].map(([l, v]) => (
          <div key={l} className="rounded-lg bg-canvas p-2"><dt className="text-[11px] text-muted">{l}</dt><dd className="text-lg font-bold tabular-nums">{v}</dd></div>
        ))}
      </dl>
      <p className="mt-3 text-xs text-muted">
        {s.eligible_listings} of {s.live_listings} live listings qualify for TOP spots.
        {missing > 0 && <> To qualify, a listing needs at least {s.quality_bar.min_photos} photos and a {s.quality_bar.min_description}+ character description, and your store must be ID- or business-verified.</>}
      </p>
    </div>
  );
}

const TONE = { active: "good", sold: "info", inactive: "neutral", pending_review: "warn", rejected: "bad", draft: "neutral" } as const;

function List() {
  const [status, setStatus] = useState("");
  const { data, reload } = useApi<Page<SellerProductRow>>("/seller/products", { status: status || undefined, page_size: 100 });
  const { data: ads, reload: reloadAds } = useApi<AdSummary>("/seller/ads/summary");
  const toast = useToast();
  async function act(p: SellerProductRow, action: string) {
    try {
      if (action === "delete") { if (!confirm("Delete this listing?")) return; await http.del(`/seller/products/${p.id}`); }
      else if (action === "bump") { await http.post(`/seller/products/${p.id}/bump`); toast("Bumped to the top of its category"); reloadAds(); }
      else if (action === "feature") { await http.post("/subscriptions/feature-listing", { product_id: p.id, days: 7 }); toast("Listing featured for 7 days"); }
      else await http.post(`/seller/products/${p.id}/status`, { status: action });
      reload();
    } catch (e) { toast(errorMessage(e), "bad"); }
  }
  return (
    <>
      {ads && <SponsoredCard s={ads} />}
      <Tabs value={status} onChange={setStatus} tabs={[{ value: "", label: "All" }, { value: "active", label: "Active" }, { value: "pending_review", label: "In review" }, { value: "sold", label: "Sold" }, { value: "inactive", label: "Inactive" }, { value: "rejected", label: "Rejected" }]} />
      {!data ? <PageLoader /> : !data.items.length ? (
        <div className="card mt-3"><EmptyState icon={<Package />} title="No listings here" action={<ButtonLink href="/seller/products/new">Post your first ad</ButtonLink>} /></div>
      ) : (
        <ul className="card mt-3 divide-y divide-line">
          {data.items.map((p) => (
            <li key={p.id} className="flex flex-col gap-3 p-3 sm:flex-row sm:items-center">
              <div className="flex min-w-0 flex-1 gap-3">
                <div className="size-16 shrink-0 overflow-hidden rounded-lg"><ProductThumb src={p.thumb_url} alt={p.title} categorySlug={p.category.slug} /></div>
                <div className="min-w-0">
                  <Link href={`/item/${p.slug}`} className="line-clamp-1 font-medium hover:text-brand-700">{p.title}</Link>
                  <p className="text-sm font-semibold text-brand-800">{naira(p.price)} <span className="font-normal text-muted">· {p.quantity} in stock</span></p>
                  <p className="flex flex-wrap gap-3 text-xs text-muted">
                    <span className="inline-flex items-center gap-1"><Eye className="size-3" />{p.views_count}</span>
                    <span className="inline-flex items-center gap-1"><MessageCircle className="size-3" />{p.enquiries_count}</span>
                    <span className="inline-flex items-center gap-1"><MousePointerClick className="size-3" />{p.contact_clicks}</span>
                    {p.is_featured && <span className="font-semibold text-accent-600">Featured</span>}
                  </p>
                  {p.rejection_reason && <p className="text-xs text-red-600">{p.rejection_reason}</p>}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={TONE[p.status]}>{titleCase(p.status)}</Badge>
                <Link href={`/seller/products/${p.id}/edit`} className="chip"><Pencil className="size-3.5" />Edit</Link>
                {p.status === "active" && ads?.bumps.premium && (
                  <button className="chip" disabled={!ads.bumps.remaining} title={ads.bumps.remaining ? "Move this listing back to the top of its category" : "No bumps left today"}
                    onClick={() => act(p, "bump")}><ArrowUpToLine className="size-3.5" />Bump</button>
                )}
                {p.status === "active" && <button className="chip" onClick={() => act(p, "sold")}>Mark sold</button>}
                {p.status === "active" && <button className="chip" onClick={() => act(p, "inactive")}>Pause</button>}
                {p.status === "active" && !p.is_featured && <button className="chip" onClick={() => act(p, "feature")}><Sparkles className="size-3.5" />Feature</button>}
                {["inactive", "sold"].includes(p.status) && <button className="chip" onClick={() => act(p, "active")}>Reactivate</button>}
                <button className="chip text-red-600" onClick={() => act(p, "delete")}>Delete</button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <><div className="mb-3 flex items-center justify-between"><h1 className="text-2xl font-bold">My products</h1><ButtonLink href="/seller/products/new" size="sm"><PlusCircle className="size-4" />Add</ButtonLink></div><List /></>}</RequireAuth>;
}
