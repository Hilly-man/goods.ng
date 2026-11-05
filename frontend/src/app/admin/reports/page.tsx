"use client";

import Link from "next/link";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, titleCase } from "@/lib/format";

type R = { id: string; target_type: string; target_id: string; reason: string; details: string | null; status: string; created_at: string };

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("open");
  const act = async (r: R, s: string, reload: () => void) => {
    const resolution = askReason("Resolution note:"); if (!resolution) return;
    try { await http.post(`/admin/reports/${r.id}`, { status: s, resolution }); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
  };
  return (
    <><h1 className="mb-4 text-2xl font-bold">Reports</h1>
    <AdminTable<R> path="/admin/reports" query={{ status }} filters={<select className="input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status"><option value="open">Open</option><option value="actioned">Actioned</option><option value="dismissed">Dismissed</option></select>} columns={[
      { key: "t", label: "Target", render: (r) => <><p className="font-medium">{titleCase(r.target_type)}</p>{r.target_type === "product" && <Link href="/admin/products" className="font-mono text-[10px] text-brand-700">{r.target_id}</Link>}</> },
      { key: "r", label: "Reason", render: (r) => <><p>{r.reason}</p>{r.details && <p className="text-xs text-muted">{r.details}</p>}</> },
      { key: "d", label: "Reported", render: (r) => date(r.created_at, true) },
    ]} actions={(r, reload) => r.status === "open" ? (<>
      <Button size="sm" onClick={() => act(r, "actioned", reload)}>Actioned</Button>
      <Button size="sm" variant="outline" onClick={() => act(r, "dismissed", reload)}>Dismiss</Button>
    </>) : null} /></>
  );
}
