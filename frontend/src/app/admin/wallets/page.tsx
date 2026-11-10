"use client";

import Link from "next/link";
import { Wallet } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-ui";
import { AdminTable } from "@/components/admin-table";
import { Badge } from "@/components/ui";
import { useAdminBase } from "@/lib/admin-area";
import { naira } from "@/lib/format";

type W = {
  id: string; seller_id: string; store_name: string; slug: string; owner_email: string;
  is_suspended: boolean; payouts_frozen: boolean;
  available: string; clearing: string; in_escrow: string; on_hold: string;
  pending_payouts: string; withdrawn: string;
};

export default function Page() {
  const base = useAdminBase();
  return (
    <>
      <AdminPageHeader icon={Wallet} title="Seller wallets" description="Every seller's wallet position. Available excludes funds still clearing, held for instalments/complaints, or already requested for payout." />
      <AdminTable<W> path="/admin/wallets" searchable columns={[
        { key: "s", label: "Seller", render: (w) => <><Link href={`${base}/sellers/${w.seller_id}`} className="font-medium text-brand-700">{w.store_name}</Link><p className="text-xs text-muted">{w.owner_email}</p></> },
        { key: "a", label: "Available", render: (w) => <b>{naira(w.available)}</b> },
        { key: "c", label: "Clearing", render: (w) => naira(w.clearing) },
        { key: "e", label: "In escrow", render: (w) => naira(w.in_escrow) },
        { key: "h", label: "On hold", render: (w) => naira(w.on_hold) },
        { key: "p", label: "Pending payout", render: (w) => naira(w.pending_payouts) },
        { key: "w", label: "Withdrawn", render: (w) => naira(w.withdrawn) },
        { key: "st", label: "Status", render: (w) => w.is_suspended ? <Badge tone="bad">Suspended</Badge> : w.payouts_frozen ? <Badge tone="warn">Payouts frozen</Badge> : <Badge tone="good">Active</Badge> },
      ]} />
    </>
  );
}
