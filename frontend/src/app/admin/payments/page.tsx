"use client";

import { BarChart3 } from "lucide-react";
import { AdminPageHeader, FilterChips, StatusBadge } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { date, naira, titleCase } from "@/lib/format";

type P = { id: string; reference: string; provider: string; purpose: string; status: string; amount: string; amount_refunded: string; channel: string | null; failure_reason: string | null; order_id: string | null; verified_at: string | null; created_at: string };

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <><AdminPageHeader icon={BarChart3} title="Payments" description="Every payment attempt, verified server-side with the provider." />
    <AdminTable<P> path="/admin/payments" query={{ status: status || undefined }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["initialized", "success", "failed", "abandoned", "refunded", "partially_refunded"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
      { key: "r", label: "Reference", render: (p) => <><p className="font-mono text-xs">{p.reference}</p><p className="text-xs text-muted">{p.provider}{p.provider === "mock" && " (dev)"} · {titleCase(p.purpose)}</p></> },
      { key: "a", label: "Amount", render: (p) => <>{naira(p.amount)}{Number(p.amount_refunded) > 0 && <p className="text-xs text-muted">refunded {naira(p.amount_refunded)}</p>}</> },
      { key: "s", label: "Status", render: (p) => <><StatusBadge status={p.status} />{p.failure_reason && <p className="mt-1 max-w-xs text-xs text-red-600">{p.failure_reason}</p>}</> },
      { key: "v", label: "Verified", render: (p) => date(p.verified_at, true) },
      { key: "o", label: "Order", render: (p) => (p.order_id ? <Link href={`/orders/${p.order_id}`} className="text-brand-700">View</Link> : "—") },
    ]} /></>
  );
}
