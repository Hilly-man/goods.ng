"use client";

import Link from "next/link";
import { useState } from "react";
import { Eye, MessageCircle, MousePointerClick, Package, Pencil, PlusCircle, Sparkles } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { Badge, ButtonLink, EmptyState, PageLoader, Tabs, useToast } from "@/components/ui";
import { ProductThumb } from "@/components/product-card";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { naira, titleCase } from "@/lib/format";
import type { Page, SellerProductRow } from "@/lib/types";

const TONE = { active: "good", sold: "info", inactive: "neutral", pending_review: "warn", rejected: "bad", draft: "neutral" } as const;

function List() {
  const [status, setStatus] = useState("");
  const { data, reload } = useApi<Page<SellerProductRow>>("/seller/products", { status: status || undefined, page_size: 100 });
  const toast = useToast();
  async function act(p: SellerProductRow, action: string) {
    try {
      if (action === "delete") { if (!confirm("Delete this listing?")) return; await http.del(`/seller/products/${p.id}`); }
      else if (action === "feature") { await http.post("/subscriptions/feature-listing", { product_id: p.id, days: 7 }); toast("Listing featured for 7 days"); }
      else await http.post(`/seller/products/${p.id}/status`, { status: action });
      reload();
    } catch (e) { toast(errorMessage(e), "bad"); }
  }
  return (
    <>
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
