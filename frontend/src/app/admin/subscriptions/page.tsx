"use client";

import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, naira, titleCase } from "@/lib/format";

type S = { id: string; seller: { id: string; store_name: string }; plan: string; status: string; amount: string; current_period_start: string | null; current_period_end: string | null; granted_by_admin: boolean; created_at: string };

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("active");
  return (
    <><h1 className="mb-4 text-2xl font-bold">Premium subscriptions</h1>
    <AdminTable<S> path="/admin/subscriptions" query={{ status: status || undefined }} filters={<select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="">All</option>{["active", "pending_payment", "expired", "cancelled"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</select>} columns={[
      { key: "s", label: "Seller", render: (s) => s.seller.store_name },
      { key: "p", label: "Plan", render: (s) => <>{s.plan}{s.granted_by_admin && <Badge tone="info" className="ml-1">Granted</Badge>}</> },
      { key: "a", label: "Paid", render: (s) => naira(s.amount) },
      { key: "st", label: "Status", render: (s) => <Badge tone={s.status === "active" ? "good" : "neutral"}>{titleCase(s.status)}</Badge> },
      { key: "e", label: "Period", render: (s) => <span className="text-xs">{date(s.current_period_start)} → {date(s.current_period_end)}</span> },
    ]} actions={(s, reload) => s.status === "active" ? <Button size="sm" variant="danger" onClick={async () => { if (!confirm("Cancel this subscription immediately?")) return; try { await http.post(`/admin/subscriptions/${s.id}/cancel`); reload(); } catch (e) { toast(errorMessage(e), "bad"); } }}>Cancel</Button> : null} /></>
  );
}
