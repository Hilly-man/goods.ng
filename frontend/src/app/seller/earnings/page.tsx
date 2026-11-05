"use client";

import Link from "next/link";
import { RequireAuth } from "@/components/require-auth";
import { PageLoader, Stat } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { date, naira, ORDER_STATUS } from "@/lib/format";
import type { OrderStatus } from "@/lib/types";

type E = { released_balance: string; in_escrow: string; note: string; transactions: { order_id: string; order_number: string; status: OrderStatus; gross: string; fees: string; net: string; released_at: string | null; created_at: string }[] };

function View() {
  const { data } = useApi<E>("/seller/earnings");
  if (!data) return <PageLoader />;
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <Stat label="Released earnings" value={naira(data.released_balance)} hint="Paid out by our escrow partner" />
        <Stat label="Held in escrow" value={naira(data.in_escrow)} hint="Released after buyers confirm delivery" />
      </div>
      <p className="text-sm text-muted">{data.note}</p>
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead><tr className="border-b border-line text-left text-muted"><th className="p-3">Order</th><th className="p-3">Status</th><th className="p-3">Gross</th><th className="p-3">Fees</th><th className="p-3">Net</th><th className="p-3">Released</th></tr></thead>
          <tbody>
            {data.transactions.map((t) => (
              <tr key={t.order_id} className="border-b border-line/60">
                <td className="p-3"><Link href={`/seller/orders/${t.order_id}`} className="font-mono text-brand-700">{t.order_number}</Link></td>
                <td className="p-3">{ORDER_STATUS[t.status].label}</td><td className="p-3">{naira(t.gross)}</td><td className="p-3">-{naira(t.fees)}</td>
                <td className="p-3 font-semibold">{naira(t.net)}</td><td className="p-3">{date(t.released_at)}</td>
              </tr>
            ))}
            {!data.transactions.length && <tr><td colSpan={6} className="p-6 text-center text-muted">No protected sales yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Earnings</h1><View /></>}</RequireAuth>;
}
