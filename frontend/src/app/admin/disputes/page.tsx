"use client";

import Link from "next/link";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, naira, titleCase } from "@/lib/format";

type D = { id: string; order_id: string; order_number: string; status: string; reason: string; opened_by: string; description: string; amount: string; created_at: string };

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("");
  const resolve = async (d: D, outcome: string, reload: () => void) => {
    const notes = askReason(outcome === "refund_buyer" ? "Resolution notes (refund needs a second admin's approval):" : "Resolution notes:", 10); if (!notes) return;
    try { await http.post(`/admin/disputes/${d.id}/resolve`, { outcome, notes }); toast("Dispute resolved"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
  };
  return (
    <><h1 className="mb-4 text-2xl font-bold">Disputes</h1>
    <AdminTable<D> path="/admin/disputes" query={{ status: status || undefined }} filters={<select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="">Open & under review</option>{["resolved_buyer", "resolved_seller", "cancelled"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</select>} columns={[
      { key: "o", label: "Order", render: (d) => <><Link href={`/orders/${d.order_id}`} className="font-mono text-brand-700">{d.order_number}</Link><p className="text-xs text-muted">{naira(d.amount)}</p></> },
      { key: "r", label: "Reason", render: (d) => <><p className="font-medium">{titleCase(d.reason)}</p><p className="text-xs text-muted">Opened by {d.opened_by}</p></> },
      { key: "d", label: "Description", render: (d) => <p className="max-w-sm text-xs">{d.description}</p> },
      { key: "s", label: "Status", render: (d) => <Badge tone="bad">{titleCase(d.status)}</Badge> },
      { key: "t", label: "Opened", render: (d) => date(d.created_at) },
    ]} actions={(d, reload) => ["open", "under_review"].includes(d.status) ? (<div className="flex flex-col gap-1">
      {d.status === "open" && <Button size="sm" variant="ghost" onClick={async () => { await http.post(`/admin/disputes/${d.id}/review`).catch(() => {}); reload(); }}>Start review</Button>}
      <Button size="sm" onClick={() => resolve(d, "release_to_seller", reload)}>Release to seller</Button>
      <Button size="sm" variant="danger" onClick={() => resolve(d, "refund_buyer", reload)}>Refund buyer</Button>
      <Button size="sm" variant="outline" onClick={() => resolve(d, "cancel", reload)}>Close, no action</Button>
    </div>) : null} /></>
  );
}
