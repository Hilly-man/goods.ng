"use client";

import { Star } from "lucide-react";
import { AdminPageHeader, StatusBadge } from "@/components/admin-ui";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";

type R = { id: string; rating: number; title: string | null; comment: string | null; status: string; is_verified_purchase: boolean; reviewer: string; reports: number; created_at: string };

export default function Page() {
  const toast = useToast();
  const [reported, setReported] = useState(true);
  return (
    <><AdminPageHeader icon={Star} title="Reviews" description="Hide abusive or fake reviews, or restore them." />
    <AdminTable<R> path="/admin/reviews" query={{ reported_only: reported }} filters={<label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={reported} onChange={(e) => setReported(e.target.checked)} className="accent-brand-700" />Reported only</label>} columns={[
      { key: "r", label: "Rating", render: (r) => "★".repeat(r.rating) },
      { key: "c", label: "Review", render: (r) => <><p className="font-medium">{r.title}</p><p className="max-w-md text-xs">{r.comment}</p><p className="text-xs text-muted">{r.reviewer}{r.is_verified_purchase && " · verified purchase"}</p></> },
      { key: "rep", label: "Reports", render: (r) => r.reports },
      { key: "s", label: "Status", render: (r) => <StatusBadge status={r.status} /> },
    ]} actions={(r, reload) => (
      <Button size="sm" variant={r.status === "published" ? "danger" : "secondary"} onClick={async () => {
        const note = await askReason(r.status === "published" ? "Reason for hiding:" : "Reason for restoring:"); if (!note) return;
        try { await http.post(`/admin/reviews/${r.id}/moderate`, { status: r.status === "published" ? "hidden" : "published", note }); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
      }}>{r.status === "published" ? "Hide" : "Restore"}</Button>
    )} /></>
  );
}
