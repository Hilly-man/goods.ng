"use client";

import Link from "next/link";
import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { Badge } from "@/components/ui";
import { date, naira, titleCase } from "@/lib/format";

type A = { id: string; status: string; provider: string; credit_decision_ref: string | null; purchase_amount: string; tenor_months: number; decline_reason: string | null; order_id: string | null; created_at: string; outstanding: string | null };

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <><h1 className="mb-1 text-2xl font-bold">BNPL monitoring</h1>
    <p className="mb-4 text-sm text-muted">Credit decisions are made by the lending partner; this view is read-only for reconciliation and monitoring.</p>
    <AdminTable<A> path="/admin/bnpl/applications" query={{ status: status || undefined }} filters={<select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="">All</option>{["approved", "declined", "accepted", "active", "completed", "cancelled", "defaulted"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</select>} columns={[
      { key: "r", label: "Decision ref", render: (a) => <><p className="font-mono text-xs">{a.credit_decision_ref}</p><p className="text-xs text-muted">{a.provider}{a.provider === "mock" && " (dev)"}</p></> },
      { key: "a", label: "Amount", render: (a) => `${naira(a.purchase_amount)} · ${a.tenor_months}m` },
      { key: "s", label: "Status", render: (a) => <><Badge>{titleCase(a.status)}</Badge>{a.decline_reason && <p className="mt-1 text-xs text-muted">{a.decline_reason}</p>}</> },
      { key: "o", label: "Outstanding", render: (a) => (a.outstanding ? naira(a.outstanding) : "—") },
      { key: "ord", label: "Order", render: (a) => (a.order_id ? <Link href={`/orders/${a.order_id}`} className="text-brand-700">View</Link> : "—") },
      { key: "t", label: "Applied", render: (a) => date(a.created_at) },
    ]} /></>
  );
}
