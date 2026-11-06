"use client";

import { Receipt } from "lucide-react";
import { AdminPageHeader, FilterChips } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { Badge } from "@/components/ui";
import { date, naira, titleCase } from "@/lib/format";

import type { Order } from "@/lib/types";
import { StatusBadge } from "@/components/order-view";

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <><AdminPageHeader icon={Receipt} title="Orders" description="Every protected-checkout order and where it is in escrow." />
    <AdminTable<Order> path="/admin/orders" query={{ status: status || undefined }} searchable filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All statuses" }, ...["pending_payment", "awaiting_seller", "processing", "dispatched", "awaiting_buyer_confirmation", "disputed", "refund_pending", "completed", "refunded", "cancelled"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
      { key: "n", label: "Order", render: (o) => <><Link href={`/orders/${o.id}`} className="font-mono text-brand-700">{o.order_number}</Link><p className="text-xs text-muted">{o.items[0]?.title}</p></> },
      { key: "p", label: "Parties", render: (o) => <span className="text-xs">{o.buyer.name} → {o.seller.store_name}</span> },
      { key: "t", label: "Total", render: (o) => <>{naira(o.total)}{o.payment_method === "bnpl" && <Badge tone="info" className="ml-1">Flex</Badge>}</> },
      { key: "s", label: "Status", render: (o) => <StatusBadge status={o.status} /> },
      { key: "d", label: "Created", render: (o) => date(o.created_at, true) },
    ]} /></>
  );
}
