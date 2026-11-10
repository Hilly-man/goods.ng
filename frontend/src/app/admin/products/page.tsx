"use client";

import { Package } from "lucide-react";
import { AdminPageHeader, FilterChips, StatusBadge } from "@/components/admin-ui";
import Link from "next/link";
import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AdminTable, askReason } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, naira, titleCase } from "@/lib/format";
import { useAdminBase } from "@/lib/admin-area";

type P = { id: string; title: string; slug: string; price: string; status: string; seller: { store_name: string }; category: string; thumb_url: string | null; is_featured: boolean; rejection_reason: string | null; created_at: string };

export default function Page() {
  return <Suspense><Products /></Suspense>;
}

function Products() {
  const toast = useToast();
  const sp = useSearchParams();
  const seller = sp.get("seller") ?? "";
  const base = useAdminBase();
  const [status, setStatus] = useState(sp.get("status") ?? "");
  const mod = async (p: P, action: string, reload: () => void) => {
    const body: Record<string, unknown> = { action };
    if (action === "reject" || action === "deactivate") { const r = await askReason(action === "reject" ? "Reject this listing?" : "Take down this listing?", 3, { message: <>Tell the seller why — they&apos;ll see this reason.<br /><b>{p.title}</b></>, confirmLabel: action === "reject" ? "Reject listing" : "Take down", tone: "danger" }); if (!r) return; body.reason = r; }
    try { await http.post(`/admin/products/${p.id}/moderate`, body); toast("Updated"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
  };
  return (
    <><AdminPageHeader icon={Package} title="Listings" description="Approve new ads, feature great ones and take down anything that breaks the rules." />
    {seller && <p className="mb-3 rounded-lg bg-canvas p-3 text-sm text-muted">Showing listings for one seller. <Link href={`${base}/products`} className="font-semibold text-brand-700 underline">Clear seller filter</Link></p>}
    <AdminTable<P> path="/admin/products" query={{ status: status || undefined, seller_id: seller || undefined }} searchable filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["active", "pending_review", "rejected", "inactive", "sold"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
      { key: "t", label: "Listing", render: (p) => <div className="flex gap-2">{p.thumb_url ? <img src={p.thumb_url} alt="" className="size-10 rounded object-cover" /> : <span className="size-10 rounded bg-canvas" />}<div><Link href={`${base}/products/${p.id}`} className="font-medium text-brand-700">{p.title}</Link><p className="text-xs text-muted">{p.seller.store_name} · {p.category}</p></div></div> },
      { key: "p", label: "Price", render: (p) => naira(p.price) },
      { key: "s", label: "Status", render: (p) => <><StatusBadge status={p.status} />{p.is_featured && <Badge tone="warn" className="ml-1">Featured</Badge>}{p.rejection_reason && <p className="mt-1 text-xs text-red-600">{p.rejection_reason}</p>}</> },
      { key: "d", label: "Listed", render: (p) => date(p.created_at) },
    ]} actions={(p, reload) => (<>
      {p.status !== "active" && <Button size="sm" onClick={() => mod(p, "approve", reload)}>Approve</Button>}
      {p.status === "pending_review" && <Button size="sm" variant="danger" onClick={() => mod(p, "reject", reload)}>Reject</Button>}
      {p.status === "active" && <Button size="sm" variant="outline" onClick={() => mod(p, p.is_featured ? "unfeature" : "feature", reload)}>{p.is_featured ? "Unfeature" : "Feature"}</Button>}
      {p.status === "active" && <Button size="sm" variant="danger" onClick={() => mod(p, "deactivate", reload)}>Take down</Button>}
    </>)} /></>
  );
}
