"use client";

import Link from "next/link";
import { Alert, PageLoader, Stat } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { naira } from "@/lib/format";

type O = Record<string, number | string> & { bnpl: Record<string, number | string> };

export default function Page() {
  const { data: o, error } = useApi<O>("/admin/overview");
  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!o) return <PageLoader />;
  const queue = [
    ["open_disputes", "Open disputes", "/admin/disputes"], ["pending_refunds", "Refunds awaiting approval", "/admin/refunds"],
    ["pending_verifications", "Verifications to review", "/admin/verifications"], ["pending_listings", "Listings in review", "/admin/products?status=pending_review"],
    ["open_reports", "Open reports", "/admin/reports"],
  ] as const;
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Overview</h1>
      <div className="grid gap-2 sm:grid-cols-5">
        {queue.map(([k, l, h]) => (
          <Link key={k} href={h} className={`card p-3 ${Number(o[k]) > 0 ? "ring-2 ring-amber-300" : ""}`}><p className="text-2xl font-bold">{o[k]}</p><p className="text-xs text-muted">{l}</p></Link>
        ))}
      </div>
      <section><h2 className="mb-2 font-semibold">Marketplace</h2><div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Total users" value={o.total_users} /><Stat label="Active buyers (30d)" value={o.active_buyers_30d} />
        <Stat label="Active sellers" value={o.active_sellers} hint={`${o.total_sellers} seller profiles`} /><Stat label="Verified sellers" value={o.verified_sellers} />
        <Stat label="Premium sellers" value={o.premium_sellers} /><Stat label="Active listings" value={Number(o.active_listings).toLocaleString()} />
      </div></section>
      <section><h2 className="mb-2 font-semibold">Transactions</h2><div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Paid orders" value={o.total_orders} /><Stat label="Completed protected" value={o.completed_protected} />
        <Stat label="Transaction value (completed)" value={naira(String(o.total_transaction_value))} /><Stat label="Currently in escrow" value={naira(String(o.in_escrow_value))} />
        <Stat label="Platform revenue" value={naira(String(o.platform_revenue))} hint="Commission + protection + subscriptions" />
        <Stat label="Dispute rate" value={`${o.dispute_rate}%`} /><Stat label="Refund rate" value={`${o.refund_rate}%`} />
      </div></section>
      <section><h2 className="mb-2 font-semibold">Goods Flex (BNPL)</h2><div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <Stat label="Applications" value={o.bnpl.applications} /><Stat label="Approved" value={o.bnpl.approved} /><Stat label="Active agreements" value={o.bnpl.active_agreements} />
        <Stat label="Outstanding" value={naira(String(o.bnpl.outstanding))} /><Stat label="Overdue instalments" value={o.bnpl.overdue_installments} />
      </div></section>
    </div>
  );
}
