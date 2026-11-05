"use client";

import Link from "next/link";
import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { Badge } from "@/components/ui";
import { date, naira, titleCase } from "@/lib/format";

type P = { id: string; reference: string; provider: string; purpose: string; status: string; amount: string; amount_refunded: string; channel: string | null; failure_reason: string | null; order_id: string | null; verified_at: string | null; created_at: string };

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <><h1 className="mb-4 text-2xl font-bold">Payments</h1>
    <AdminTable<P> path="/admin/payments" query={{ status: status || undefined }} filters={<select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="">All</option>{["initialized", "success", "failed", "abandoned", "refunded", "partially_refunded"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</select>} columns={[
      { key: "r", label: "Reference", render: (p) => <><p className="font-mono text-xs">{p.reference}</p><p className="text-xs text-muted">{p.provider}{p.provider === "mock" && " (dev)"} · {titleCase(p.purpose)}</p></> },
      { key: "a", label: "Amount", render: (p) => <>{naira(p.amount)}{Number(p.amount_refunded) > 0 && <p className="text-xs text-muted">refunded {naira(p.amount_refunded)}</p>}</> },
      { key: "s", label: "Status", render: (p) => <><Badge tone={p.status === "success" ? "good" : p.status === "failed" ? "bad" : "neutral"}>{titleCase(p.status)}</Badge>{p.failure_reason && <p className="mt-1 max-w-xs text-xs text-red-600">{p.failure_reason}</p>}</> },
      { key: "v", label: "Verified", render: (p) => date(p.verified_at, true) },
      { key: "o", label: "Order", render: (p) => (p.order_id ? <Link href={`/orders/${p.order_id}`} className="text-brand-700">View</Link> : "—") },
    ]} /></>
  );
}
