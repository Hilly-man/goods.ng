"use client";

import { Store } from "lucide-react";
import { AdminPageHeader, askValue } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { titleCase } from "@/lib/format";

type S = { id: string; store_name: string; slug: string; verification_level: string; is_suspended: boolean; rating_avg: string; rating_count: number; completed_sales: number; owner_email: string; created_at: string };

export default function Page() {
  const toast = useToast();
  const [plan, setPlan] = useState("premium_monthly");
  return (
    <><AdminPageHeader icon={Store} title="Sellers" description="Search stores, grant Premium or suspend sellers." />
    <AdminTable<S> path="/admin/sellers" searchable filters={<select className="input w-auto" value={plan} onChange={(e) => setPlan(e.target.value)} aria-label="Plan for grants"><option value="premium_monthly">Grant: Premium Monthly</option><option value="premium_quarterly">Grant: Premium Quarterly</option><option value="business_annual">Grant: Business Annual</option></select>} columns={[
      { key: "n", label: "Store", render: (s) => <><Link href={`/store/${s.slug}`} className="font-medium text-brand-700">{s.store_name}</Link><p className="text-xs text-muted">{s.owner_email}</p></> },
      { key: "v", label: "Verification", render: (s) => titleCase(s.verification_level) },
      { key: "r", label: "Rating", render: (s) => `${Number(s.rating_avg).toFixed(1)} (${s.rating_count})` },
      { key: "c", label: "Sales", render: (s) => s.completed_sales },
      { key: "st", label: "Status", render: (s) => <Badge tone={s.is_suspended ? "bad" : "good"}>{s.is_suspended ? "Suspended" : "Active"}</Badge> },
    ]} actions={(s, reload) => (<>
      <Button size="sm" variant="outline" onClick={async () => {
        const reason = await askReason("Reason for granting premium (e.g. promotion, compensation):", 5); if (!reason) return;
        const days = Number(await askValue("How many days of Premium?", { label: "Days", type: "number", initial: "30" }, { confirmLabel: "Grant Premium" })); if (!days) return;
        try { await http.post("/admin/subscriptions/grant", { seller_id: s.id, plan_code: plan, days, reason }); toast("Premium granted"); } catch (e) { toast(errorMessage(e), "bad"); }
      }}>Grant premium</Button>
      <Button size="sm" variant={s.is_suspended ? "secondary" : "danger"} onClick={async () => {
        const reason = await askReason(s.is_suspended ? `Reinstate ${s.store_name}?` : `Suspend ${s.store_name}?`, 3, { message: s.is_suspended ? "Their listings become visible again." : "Their listings are hidden and they can’t sell until reinstated.", confirmLabel: s.is_suspended ? "Reinstate" : "Suspend seller", tone: s.is_suspended ? "default" : "danger" }); if (!reason) return;
        try { await http.post(`/admin/sellers/${s.id}/suspend`, { suspended: !s.is_suspended, reason }); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
      }}>{s.is_suspended ? "Reinstate" : "Suspend"}</Button>
    </>)} /></>
  );
}
