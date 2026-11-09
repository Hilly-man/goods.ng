"use client";

import { RotateCcw } from "lucide-react";
import { AdminPageHeader, FilterChips, confirmAction, StatusBadge } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, naira, titleCase } from "@/lib/format";

type F = { id: string; order_id: string; amount: string; status: string; reason: string; requested_by_id: string; approved_by_id: string | null; dispute_id: string | null; created_at: string; completed_at: string | null };

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("pending_approval");
  return (
    <><AdminPageHeader icon={RotateCcw} title="Refunds" description={<>Dispute refunds require approval by a different administrator from the one who resolved the dispute (four-eyes control).</>} />
    <AdminTable<F> path="/admin/refunds" query={{ status: status || undefined }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["pending_approval", "processing", "completed", "rejected", "failed"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
      { key: "o", label: "Order", render: (r) => <Link href={`/orders/${r.order_id}`} className="text-brand-700">View order</Link> },
      { key: "a", label: "Amount", render: (r) => <b>{naira(r.amount)}</b> },
      { key: "r", label: "Reason", render: (r) => <p className="max-w-sm text-xs">{r.reason}</p> },
      { key: "s", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
      { key: "t", label: "Requested", render: (r) => date(r.created_at, true) },
    ]} actions={(r, reload) => r.status === "pending_approval" ? (<>
      <Button size="sm" onClick={async () => { if (!(await confirmAction({ title: `Refund ${naira(r.amount)}?`, message: "The money goes back to the buyer through the original payment method. This can’t be undone.", confirmLabel: "Approve refund", tone: "danger" }))) return; try { await http.post(`/admin/refunds/${r.id}/approve`); toast("Refund executed"); reload(); } catch (e) { toast(errorMessage(e), "bad"); } }}>Approve</Button>
      <Button size="sm" variant="danger" onClick={async () => { const reason = await askReason("Reason for rejecting (returns the order to dispute):", 5); if (!reason) return; try { await http.post(`/admin/refunds/${r.id}/reject`, { reason }); reload(); } catch (e) { toast(errorMessage(e), "bad"); } }}>Reject</Button>
    </>) : null} /></>
  );
}
