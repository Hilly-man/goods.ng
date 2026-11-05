"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CalendarClock } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { FlexLimitCard, FlexSteps, type FlexStatus } from "@/components/flex-setup";
import { Badge, Button, EmptyState, PageLoader, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { date, naira } from "@/lib/format";

type Inst = { id: string; sequence: number; due_date: string; amount: string; amount_paid: string; status: string; paid_at: string | null };
type Ag = { id: string; order_id: string | null; status: string; total_payable: string; outstanding_balance: string; down_payment: string; tenor_months: number; installments: Inst[] };

function Agreements() {
  const { data, reload } = useApi<{ total_outstanding: string; agreements: Ag[] }>("/bnpl/agreements");
  const [busy, setBusy] = useState<string | null>(null);
  const toast = useToast();
  useEffect(() => {
    // Returning from an instalment payment: trigger server-side verification, then refresh.
    const ref = new URLSearchParams(location.search).get("reference");
    if (ref) http.post(`/payments/${ref}/verify`).then(reload).catch(() => {});
  }, [reload]);
  if (!data) return <PageLoader />;
  if (!data.agreements.length) return <div className="card"><EmptyState icon={<CalendarClock />} title="No Goods Flex plans yet" body="Look for the Goods Flex option on eligible listings." /></div>;
  return (
    <div className="space-y-4">
      <div className="card p-5"><p className="text-sm text-muted">Total outstanding</p><p className="text-3xl font-extrabold">{naira(data.total_outstanding)}</p></div>
      {data.agreements.map((a) => (
        <section key={a.id} className="card p-5">
          <div className="flex items-center justify-between">
            <div><p className="font-semibold">{a.tenor_months}-month plan · {naira(a.total_payable)}</p>{a.order_id && <Link href={`/orders/${a.order_id}`} className="text-sm text-brand-700">View order</Link>}</div>
            <Badge tone={a.status === "active" ? "info" : a.status === "completed" ? "good" : "neutral"} className="capitalize">{a.status}</Badge>
          </div>
          <p className="mt-1 text-sm text-muted">Outstanding {naira(a.outstanding_balance)}</p>
          <ul className="mt-3 divide-y divide-line">
            {a.installments.map((i) => (
              <li key={i.id} className="flex items-center justify-between gap-3 py-2.5 text-sm">
                <span>#{i.sequence} · due {date(i.due_date)}</span>
                <span className="flex items-center gap-2">
                  <span className="font-semibold">{naira(i.amount)}</span>
                  {i.status === "paid" ? <Badge tone="good">Paid</Badge> : i.status === "cancelled" ? <Badge>Cancelled</Badge> : a.status === "active" ? (
                    <Button size="sm" variant={i.status === "overdue" ? "danger" : "secondary"} loading={busy === i.id} onClick={async () => {
                      setBusy(i.id);
                      try { const r = await http.post<{ authorization_url: string }>(`/bnpl/installments/${i.id}/pay`); window.location.href = r.authorization_url; }
                      catch (e) { toast(errorMessage(e), "bad"); setBusy(null); }
                    }}>{i.status === "overdue" ? "Pay overdue" : "Pay now"}</Button>
                  ) : <Badge className="capitalize">{i.status}</Badge>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function FlexHome() {
  const { data, setData } = useApi<FlexStatus>("/bnpl/profile");
  if (!data) return <PageLoader />;
  return (
    <div className="space-y-5">
      <FlexLimitCard s={data} />
      <div>
        <h2 className="mb-3 text-lg font-bold">Set up & raise your limit</h2>
        <FlexSteps s={data} onChange={setData} />
      </div>
      <div>
        <h2 className="mb-3 text-lg font-bold">Your plans</h2>
        <Agreements />
      </div>
      <p className="text-xs text-muted">Goods Flex financing is provided by a licensed lending partner, subject to approval. Only one Goods Flex plan can run at a time. <Link href="/flex/about" className="underline">How Goods Flex works</Link></p>
    </div>
  );
}

export default function Page() {
  return <RequireAuth>{() => <div className="container-page max-w-3xl py-6"><h1 className="mb-4 text-2xl font-bold">Goods Flex</h1><FlexHome /></div>}</RequireAuth>;
}
