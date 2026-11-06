"use client";

import { Flag } from "lucide-react";
import { AdminPageHeader, FilterChips } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useAdminBase } from "@/lib/admin-area";
import { date, titleCase } from "@/lib/format";

type R = { id: string; target_type: string; target_id: string; reason: string; details: string | null; status: string; created_at: string };

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("open");
  const base = useAdminBase();
  const act = async (r: R, s: string, reload: () => void) => {
    const resolution = await askReason("Resolution note:"); if (!resolution) return;
    try { await http.post(`/admin/reports/${r.id}`, { status: s, resolution }); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
  };
  return (
    <><AdminPageHeader icon={Flag} title="Reports" description="Listings, users and messages flagged by the community." />
    <AdminTable<R> path="/admin/reports" query={{ status }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "open", label: "Open" }, { value: "actioned", label: "Actioned" }, { value: "dismissed", label: "Dismissed" }]} />} columns={[
      { key: "t", label: "Target", render: (r) => <><p className="font-medium">{titleCase(r.target_type)}</p>{r.target_type === "product" && <Link href={`${base}/products`} className="font-mono text-[10px] text-brand-700">{r.target_id}</Link>}</> },
      { key: "r", label: "Reason", render: (r) => <><p>{r.reason}</p>{r.details && <p className="text-xs text-muted">{r.details}</p>}</> },
      { key: "d", label: "Reported", render: (r) => date(r.created_at, true) },
    ]} actions={(r, reload) => r.status === "open" ? (<>
      <Button size="sm" onClick={() => act(r, "actioned", reload)}>Actioned</Button>
      <Button size="sm" variant="outline" onClick={() => act(r, "dismissed", reload)}>Dismiss</Button>
    </>) : null} /></>
  );
}
