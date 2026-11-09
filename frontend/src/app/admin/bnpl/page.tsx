"use client";

import { CalendarClock } from "lucide-react";
import { AdminPageHeader, FilterChips, StatusBadge } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { date, naira, titleCase } from "@/lib/format";

type A = { id: string; status: string; provider: string; credit_decision_ref: string | null; purchase_amount: string; tenor_months: number; decline_reason: string | null; order_id: string | null; created_at: string; outstanding: string | null };

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <><AdminPageHeader icon={CalendarClock} title="Goods Flex" description={<>Credit decisions are made by the lending partner; this view is read-only for reconciliation and monitoring.</>} />
    <AdminTable<A> path="/admin/bnpl/applications" query={{ status: status || undefined }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["approved", "declined", "accepted", "active", "completed", "cancelled", "defaulted"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
      { key: "r", label: "Decision ref", render: (a) => <><p className="font-mono text-xs">{a.credit_decision_ref}</p><p className="text-xs text-muted">{a.provider}{a.provider === "mock" && " (dev)"}</p></> },
      { key: "a", label: "Amount", render: (a) => `${naira(a.purchase_amount)} · ${a.tenor_months}m` },
      { key: "s", label: "Status", render: (a) => <><StatusBadge status={a.status} />{a.decline_reason && <p className="mt-1 text-xs text-muted">{a.decline_reason}</p>}</> },
      { key: "o", label: "Outstanding", render: (a) => (a.outstanding ? naira(a.outstanding) : "—") },
      { key: "ord", label: "Order", render: (a) => (a.order_id ? <Link href={`/orders/${a.order_id}`} className="text-brand-700">View</Link> : "—") },
      { key: "t", label: "Applied", render: (a) => date(a.created_at) },
    ]} /></>
  );
}
