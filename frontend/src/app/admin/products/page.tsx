"use client";

import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AdminTable, askReason } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, naira, titleCase } from "@/lib/format";

type P = { id: string; title: string; slug: string; price: string; status: string; seller: { store_name: string }; category: string; thumb_url: string | null; is_featured: boolean; rejection_reason: string | null; created_at: string };

export default function Page() {
  return <Suspense><Products /></Suspense>;
}

function Products() {
  const toast = useToast();
  const [status, setStatus] = useState(useSearchParams().get("status") ?? "");
  const mod = async (p: P, action: string, reload: () => void) => {
    const body: Record<string, unknown> = { action };
    if (action === "reject" || action === "deactivate") { const r = askReason("Reason (shown to seller):"); if (!r) return; body.reason = r; }
    try { await http.post(`/admin/products/${p.id}/moderate`, body); toast("Updated"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
  };
  return (
    <><h1 className="mb-4 text-2xl font-bold">Products</h1>
    <AdminTable<P> path="/admin/products" query={{ status: status || undefined }} searchable filters={<select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="">All</option>{["active", "pending_review", "rejected", "inactive", "sold"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</select>} columns={[
      { key: "t", label: "Listing", render: (p) => <div className="flex gap-2">{/* eslint-disable-next-line @next/next/no-img-element */}{p.thumb_url ? <img src={p.thumb_url} alt="" className="size-10 rounded object-cover" /> : <span className="size-10 rounded bg-canvas" />}<div><Link href={`/item/${p.slug}`} className="font-medium text-brand-700">{p.title}</Link><p className="text-xs text-muted">{p.seller.store_name} · {p.category}</p></div></div> },
      { key: "p", label: "Price", render: (p) => naira(p.price) },
      { key: "s", label: "Status", render: (p) => <><Badge>{titleCase(p.status)}</Badge>{p.is_featured && <Badge tone="warn" className="ml-1">Featured</Badge>}{p.rejection_reason && <p className="mt-1 text-xs text-red-600">{p.rejection_reason}</p>}</> },
      { key: "d", label: "Listed", render: (p) => date(p.created_at) },
    ]} actions={(p, reload) => (<>
      {p.status !== "active" && <Button size="sm" onClick={() => mod(p, "approve", reload)}>Approve</Button>}
      {p.status === "pending_review" && <Button size="sm" variant="danger" onClick={() => mod(p, "reject", reload)}>Reject</Button>}
      {p.status === "active" && <Button size="sm" variant="outline" onClick={() => mod(p, p.is_featured ? "unfeature" : "feature", reload)}>{p.is_featured ? "Unfeature" : "Feature"}</Button>}
      {p.status === "active" && <Button size="sm" variant="danger" onClick={() => mod(p, "deactivate", reload)}>Take down</Button>}
    </>)} /></>
  );
}
