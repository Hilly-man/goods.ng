"use client";

import Link from "next/link";
import { Package } from "lucide-react";
import type { Order, Page } from "@/lib/types";
import { useApi } from "@/lib/hooks";
import { date, naira } from "@/lib/format";
import { EmptyState, PageLoader } from "./ui";
import { StatusBadge } from "./order-view";

export function OrderList({ path, query, seller }: { path: string; query?: Record<string, unknown>; seller?: boolean }) {
  const { data } = useApi<Page<Order>>(path, { page_size: 50, ...query });
  if (!data) return <PageLoader />;
  if (!data.items.length) return <div className="card"><EmptyState icon={<Package />} title="No orders here" body={seller ? "Protected orders from buyers will appear here." : "Orders you place with Protected Checkout will appear here."} /></div>;
  return (
    <ul className="card divide-y divide-line">
      {data.items.map((o) => (
        <li key={o.id}>
          <Link href={seller ? `/seller/orders/${o.id}` : `/orders/${o.id}`} className="flex items-center gap-3 p-3 hover:bg-canvas">
            <span className="size-14 shrink-0 overflow-hidden rounded-lg bg-canvas">{/* eslint-disable-next-line @next/next/no-img-element */}{o.items[0]?.image_url && <img src={o.items[0].image_url} alt="" className="size-full object-cover" />}</span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">{o.items[0]?.title}</span>
              <span className="block text-xs text-muted">{o.order_number} · {date(o.created_at)} · {seller ? o.buyer.name : o.seller.store_name}</span>
              <span className="text-sm font-semibold">{naira(seller ? o.seller_earnings ?? o.total : o.total)}</span>
            </span>
            <StatusBadge status={o.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
}
