"use client";

import { Activity } from "lucide-react";
import { useState } from "react";
import { AdminPageHeader, FilterChips } from "@/components/admin-ui";
import { ChartCard, ColumnChart } from "@/components/charts";
import { Alert, Skeleton, Stat } from "@/components/ui";
import { useApi, usePolling } from "@/lib/hooks";
import { date } from "@/lib/format";

type Live = {
  visitors: { daily: number; weekly: number; monthly: number; quarterly: number; yearly: number };
  active: { live_5m: number; active_15m: number; active_60m: number; active_24h: number; signed_in: number; guests: number };
  series_24h: { hour: string; visitors: number }[];
  updated_at: string;
};

type VisitorKey = "daily" | "weekly" | "monthly" | "quarterly" | "yearly";
type WindowKey = "live_5m" | "active_15m" | "active_60m" | "active_24h";

const VISITOR_CARDS: [VisitorKey, string, string][] = [
  ["daily", "Daily visitors", "Unique visitors in the last 24 hours"],
  ["weekly", "Weekly visitors", "Unique visitors in the last 7 days"],
  ["monthly", "Monthly visitors", "Unique visitors in the last 30 days"],
  ["quarterly", "Quarterly visitors", "Unique visitors in the last 90 days"],
  ["yearly", "Yearly visitors", "Unique visitors in the last 365 days"],
];

const ACTIVE_CARDS: [WindowKey, string, string][] = [
  ["live_5m", "Live now", "Active in the last 5 minutes"],
  ["active_15m", "Active · 15m", "Active in the last 15 minutes"],
  ["active_60m", "Active · 1 hour", "Active in the last hour"],
  ["active_24h", "Active · 24 hours", "Active in the last 24 hours"],
];

export default function Page() {
  const { data, error, reload } = useApi<Live>("/admin/live-stats");
  const [period, setPeriod] = useState<VisitorKey>("daily");
  const [windowKey, setWindowKey] = useState<WindowKey>("live_5m");
  usePolling(reload, 20_000);
  const periodCard = VISITOR_CARDS.find(([key]) => key === period) ?? VISITOR_CARDS[0];
  const windowCard = ACTIVE_CARDS.find(([key]) => key === windowKey) ?? ACTIVE_CARDS[0];

  return (
    <>
      <AdminPageHeader icon={Activity} title="Live traffic" description={<>Unique visitors and active users, updated every 20 seconds. Counts are first-party and anonymous — no IP addresses or cross-site tracking.</>} />
      {error && <Alert tone="bad">{error}</Alert>}
      {!data ? (
        <div className="grid gap-3 sm:grid-cols-2">{Array.from({ length: 2 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-2xl" />)}</div>
      ) : (
        <div className="space-y-6">
          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-muted">Visitors</h2>
              <FilterChips label="Period" value={period} onChange={(v) => setPeriod(v as VisitorKey)}
                options={VISITOR_CARDS.map(([key, label]) => ({ value: key, label: label.replace(" visitors", "") }))} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Stat label={periodCard[1]} value={data.visitors[period].toLocaleString()} hint={periodCard[2]} />
            </div>
          </section>

          <section className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-sm font-bold uppercase tracking-wider text-muted">Active &amp; live users</h2>
              <FilterChips label="Window" value={windowKey} onChange={(v) => setWindowKey(v as WindowKey)}
                options={ACTIVE_CARDS.map(([key, label]) => ({ value: key, label }))} />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <Stat label={windowCard[1]} value={data.active[windowKey].toLocaleString()} hint={windowCard[2]}
                icon={windowKey === "live_5m" ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700"><span className="size-2 animate-pulse rounded-full bg-brand-600" />live</span> : undefined} />
            </div>
            <p className="text-sm text-muted">
              Live now: <b>{data.active.signed_in.toLocaleString()}</b> signed in · <b>{data.active.guests.toLocaleString()}</b> guests.
              Updated {date(data.updated_at, true)}.
            </p>
          </section>

          <ChartCard title="Visitors per hour" subtitle="Unique visitors in the last 24 hours (Lagos time)"
            table={{ head: ["Hour", "Visitors"], rows: data.series_24h.map((p) => [date(p.hour, true), p.visitors]) }}>
            <ColumnChart data={data.series_24h.map((p) => ({ date: p.hour, visitors: p.visitors }))} valueKey="visitors" label="Visitors" height={220} />
          </ChartCard>
        </div>
      )}
    </>
  );
}
