"use client";

import { Activity } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-ui";
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

const VISITOR_CARDS = [
  ["daily", "Daily visitors", "Unique visitors in the last 24 hours"],
  ["weekly", "Weekly visitors", "Unique visitors in the last 7 days"],
  ["monthly", "Monthly visitors", "Unique visitors in the last 30 days"],
  ["quarterly", "Quarterly visitors", "Unique visitors in the last 90 days"],
  ["yearly", "Yearly visitors", "Unique visitors in the last 365 days"],
] as const;

const ACTIVE_CARDS = [
  ["live_5m", "Live now", "Active in the last 5 minutes"],
  ["active_15m", "Active · 15m", "Active in the last 15 minutes"],
  ["active_60m", "Active · 1 hour", "Active in the last hour"],
  ["active_24h", "Active · 24 hours", "Active in the last 24 hours"],
] as const;

export default function Page() {
  const { data, error, reload } = useApi<Live>("/admin/live-stats");
  usePolling(reload, 20_000);

  return (
    <>
      <AdminPageHeader icon={Activity} title="Live traffic" description={<>Unique visitors and active users, updated every 20 seconds. Counts are first-party and anonymous — no IP addresses or cross-site tracking.</>} />
      {error && <Alert tone="bad">{error}</Alert>}
      {!data ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-24 rounded-2xl" />)}</div>
      ) : (
        <div className="space-y-6">
          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted">Visitors</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {VISITOR_CARDS.map(([key, label, hint]) => (
                <Stat key={key} label={label} value={data.visitors[key].toLocaleString()} hint={hint} />
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted">Active &amp; live users</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {ACTIVE_CARDS.map(([key, label, hint]) => (
                <Stat key={key} label={label} value={data.active[key].toLocaleString()} hint={hint}
                  icon={key === "live_5m" ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700"><span className="size-2 animate-pulse rounded-full bg-brand-600" />live</span> : undefined} />
              ))}
            </div>
            <p className="mt-2 text-sm text-muted">
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
