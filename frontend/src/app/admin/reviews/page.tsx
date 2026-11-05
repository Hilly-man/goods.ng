"use client";

import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { titleCase } from "@/lib/format";

type R = { id: string; rating: number; title: string | null; comment: string | null; status: string; is_verified_purchase: boolean; reviewer: string; reports: number; created_at: string };

export default function Page() {
  const toast = useToast();
  const [reported, setReported] = useState(true);
  return (
    <><h1 className="mb-4 text-2xl font-bold">Reviews</h1>
    <AdminTable<R> path="/admin/reviews" query={{ reported_only: reported }} filters={<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={reported} onChange={(e) => setReported(e.target.checked)} className="accent-brand-700" />Reported only</label>} columns={[
      { key: "r", label: "Rating", render: (r) => "★".repeat(r.rating) },
      { key: "c", label: "Review", render: (r) => <><p className="font-medium">{r.title}</p><p className="max-w-md text-xs">{r.comment}</p><p className="text-xs text-muted">{r.reviewer}{r.is_verified_purchase && " · verified purchase"}</p></> },
      { key: "rep", label: "Reports", render: (r) => r.reports },
      { key: "s", label: "Status", render: (r) => <Badge tone={r.status === "published" ? "good" : "bad"}>{titleCase(r.status)}</Badge> },
    ]} actions={(r, reload) => (
      <Button size="sm" variant={r.status === "published" ? "danger" : "secondary"} onClick={async () => {
        const note = askReason(r.status === "published" ? "Reason for hiding:" : "Reason for restoring:"); if (!note) return;
        try { await http.post(`/admin/reviews/${r.id}/moderate`, { status: r.status === "published" ? "hidden" : "published", note }); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
      }}>{r.status === "published" ? "Hide" : "Restore"}</Button>
    )} /></>
  );
}
