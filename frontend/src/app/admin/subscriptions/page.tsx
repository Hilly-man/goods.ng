"use client";

import { Crown } from "lucide-react";
import { AdminPageHeader, FilterChips, confirmAction, StatusBadge } from "@/components/admin-ui";
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
    <><AdminPageHeader icon={Crown} title="Premium plans" description="Seller Premium subscriptions and their billing status." />
    <AdminTable<S> path="/admin/subscriptions" query={{ status: status || undefined }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["active", "pending_payment", "expired", "cancelled"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
      { key: "s", label: "Seller", render: (s) => s.seller.store_name },
      { key: "p", label: "Plan", render: (s) => <>{s.plan}{s.granted_by_admin && <Badge tone="info" className="ml-1">Granted</Badge>}</> },
      { key: "a", label: "Paid", render: (s) => naira(s.amount) },
      { key: "st", label: "Status", render: (s) => <StatusBadge status={s.status} /> },
      { key: "e", label: "Period", render: (s) => <span className="text-xs">{date(s.current_period_start)} → {date(s.current_period_end)}</span> },
    ]} actions={(s, reload) => s.status === "active" ? <Button size="sm" variant="danger" onClick={async () => { if (!(await confirmAction({ title: "Cancel this subscription now?", message: "The seller loses Premium features immediately.", confirmLabel: "Cancel subscription", tone: "danger" }))) return; try { await http.post(`/admin/subscriptions/${s.id}/cancel`); reload(); } catch (e) { toast(errorMessage(e), "bad"); } }}>Cancel</Button> : null} /></>
  );
}
