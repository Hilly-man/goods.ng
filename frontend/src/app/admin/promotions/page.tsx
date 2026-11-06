"use client";

import { Megaphone } from "lucide-react";
import { AdminPageHeader, StatusBadge } from "@/components/admin-ui";
import { AdminTable } from "@/components/admin-table";
import { Badge } from "@/components/ui";
import { date, titleCase } from "@/lib/format";

type P = { id: string; product_id: string; kind: string; source: string; status: string; starts_at: string; ends_at: string };

export default function Page() {
  return (
    <><AdminPageHeader icon={Megaphone} title="Promotions" description="Featured listings and boosts currently running." />
    <AdminTable<P> path="/admin/promotions" columns={[
      { key: "k", label: "Type", render: (p) => titleCase(p.kind) },
      { key: "s", label: "Source", render: (p) => titleCase(p.source) },
      { key: "st", label: "Status", render: (p) => <StatusBadge status={p.status} /> },
      { key: "d", label: "Runs", render: (p) => `${date(p.starts_at)} → ${date(p.ends_at)}` },
    ]} />
    <p className="mt-3 text-xs text-muted">Feature a listing from Admin → Products. Sellers feature listings using their Premium plan credits.</p></>
  );
}
