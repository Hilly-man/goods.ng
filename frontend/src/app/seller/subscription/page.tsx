"use client";

import { RequireAuth } from "@/components/require-auth";
import { Badge, ButtonLink, PageLoader } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { date, naira, titleCase } from "@/lib/format";
import type { Plan } from "@/lib/types";

type S = { active: { plan: Plan; current_period_end: string; featured_used: number; featured_remaining: number } | null; history: { id: string; plan: string; status: string; amount: string; current_period_end: string | null; created_at: string }[] };

function View() {
  const { data } = useApi<S>("/subscriptions/me");
  if (!data) return <PageLoader />;
  return (
    <div className="space-y-4">
      {data.active ? (
        <div className="card bg-gradient-to-r from-amber-50 to-yellow-50 p-5">
          <p className="text-sm text-muted">Current plan</p>
          <p className="text-xl font-bold">{data.active.plan.name}</p>
          <p className="text-sm">Active until <strong>{date(data.active.current_period_end)}</strong> · {data.active.featured_remaining} featured listing credits left</p>
          <ButtonLink href="/premium" variant="outline" size="sm" className="mt-3">Renew or change plan</ButtonLink>
        </div>
      ) : (
        <div className="card p-5"><p className="font-semibold">You&apos;re on the free Standard plan.</p><ButtonLink href="/premium" className="mt-3">See Premium plans</ButtonLink></div>
      )}
      <ul className="card divide-y divide-line">
        {data.history.map((h) => (
          <li key={h.id} className="flex items-center justify-between p-3 text-sm"><span>{h.plan} · {naira(h.amount)}<span className="block text-xs text-muted">{date(h.created_at)}{h.current_period_end && ` → ${date(h.current_period_end)}`}</span></span><Badge>{titleCase(h.status)}</Badge></li>
        ))}
        {!data.history.length && <li className="p-4 text-sm text-muted">No subscription history.</li>}
      </ul>
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Subscription</h1><View /></>}</RequireAuth>;
}
