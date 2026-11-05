"use client";

import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { Badge } from "@/components/ui";
import { date } from "@/lib/format";

type A = { id: string; actor_id: string; action: string; target_type: string; target_id: string | null; details: Record<string, unknown>; ip: string | null; created_at: string };

export default function Page() {
  const [action, setAction] = useState("");
  return (
    <><h1 className="mb-1 text-2xl font-bold">Audit logs</h1>
    <p className="mb-4 text-sm text-muted">Append-only. Entries cannot be edited or deleted (enforced in the database).</p>
    <AdminTable<A> path="/admin/audit-logs" query={{ action: action || undefined }} filters={<input className="input w-56" placeholder="Filter action prefix, e.g. refund" value={action} onChange={(e) => setAction(e.target.value)} aria-label="Action filter" />} columns={[
      { key: "t", label: "When", render: (a) => date(a.created_at, true) },
      { key: "a", label: "Action", render: (a) => <Badge tone="dark">{a.action}</Badge> },
      { key: "g", label: "Target", render: (a) => <span className="font-mono text-xs">{a.target_type}:{a.target_id ?? "—"}</span> },
      { key: "d", label: "Details", render: (a) => <code className="block max-w-md truncate text-[11px]">{JSON.stringify(a.details)}</code> },
      { key: "w", label: "Actor / IP", render: (a) => <span className="font-mono text-[10px]">{a.actor_id.slice(0, 8)} · {a.ip}</span> },
    ]} /></>
  );
}
