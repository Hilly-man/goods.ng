"use client";

import { useState } from "react";
import clsx from "clsx";
import { Alert, Skeleton } from "@/components/ui";
import { FilterChips } from "@/components/admin-ui";
import { BarList, ChartCard, ColumnChart, Legend, LineChart, SERIES, SegmentBar, nairaCompact, nairaFull, shortDate } from "@/components/charts";
import { useApi } from "@/lib/hooks";
import { titleCase } from "@/lib/format";

type Point = { date: string; sales: string; orders: number; new_users: number; new_listings: number };
type Trends = {
  days: number;
  series: Point[];
  orders_by_status: { status: string; count: number }[];
  payment_mix: { full: number; bnpl: number };
  top_categories: { name: string; count: number }[];
};

const RANGES = [{ value: "7", label: "Last 7 days" }, { value: "30", label: "Last 30 days" }, { value: "90", label: "Last 90 days" }];
const FLEX = "#6250d6"; // validated against brand green (CVD ΔE 25)

export function OverviewCharts() {
  const [days, setDays] = useState("30");
  const { data, error, loading } = useApi<Trends>("/admin/overview/trends", { days: Number(days) });

  const rows = (data?.series ?? []).map((p) => ({ date: p.date, sales: Number(p.sales), orders: p.orders, new_users: p.new_users, new_listings: p.new_listings }));
  const sum = (k: keyof (typeof rows)[number]) => rows.reduce((n, r) => n + Number(r[k]), 0);

  return (
    <section aria-labelledby="trends" className="space-y-3">
      {/* Filters: one row, above everything they scope */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="trends" className="text-sm font-bold uppercase tracking-wider text-muted">Trends</h2>
        <FilterChips label="Date range" value={days} onChange={setDays} options={RANGES} />
      </div>
      {error && <Alert tone="bad">{error}</Alert>}
      {!data ? (
        <div className="grid gap-3 lg:grid-cols-3">
          <Skeleton className="h-80 rounded-2xl lg:col-span-2" /><Skeleton className="h-80 rounded-2xl" />
        </div>
      ) : (
        <div className={clsx("grid gap-3 lg:grid-cols-3 transition-opacity", loading && "opacity-60")}>
          <ChartCard className="lg:col-span-2" title="Paid order value" subtitle={`Per day · last ${days} days`}
            headline={<p><span className="text-2xl font-bold tabular-nums tracking-tight">{nairaFull(sum("sales"))}</span> <span className="text-sm text-muted">from {sum("orders").toLocaleString()} paid orders</span></p>}
            table={{ head: ["Date", "Value", "Orders"], rows: rows.map((r) => [shortDate(r.date), nairaFull(r.sales), r.orders]) }}>
            <LineChart data={rows} series={[{ key: "sales", label: "Paid order value", color: SERIES.brand }]} area height={240} format={nairaCompact} tooltipFormat={nairaFull} />
          </ChartCard>

          <ChartCard title="Orders" subtitle={`Paid orders per day · last ${days} days`}
            headline={<p className="text-2xl font-bold tabular-nums tracking-tight">{sum("orders").toLocaleString()}</p>}
            table={{ head: ["Date", "Orders"], rows: rows.map((r) => [shortDate(r.date), r.orders]) }}>
            <ColumnChart data={rows} valueKey="orders" label="Orders" height={240} />
          </ChartCard>

          <ChartCard className="lg:col-span-2" title="Growth" subtitle="New customer sign-ups and new listings per day"
            legend={<Legend items={[{ label: `New users (${sum("new_users")})`, color: SERIES.blue }, { label: `New listings (${sum("new_listings")})`, color: SERIES.brand }]} />}
            table={{ head: ["Date", "New users", "New listings"], rows: rows.map((r) => [shortDate(r.date), r.new_users, r.new_listings]) }}>
            <LineChart data={rows} height={220} series={[
              { key: "new_users", label: "New users", color: SERIES.blue },
              { key: "new_listings", label: "New listings", color: SERIES.brand },
            ]} />
          </ChartCard>

          <ChartCard title="How buyers pay" subtitle={`Paid orders · last ${days} days`}
            table={{ head: ["Method", "Orders"], rows: [["Protected Checkout (pay in full)", data.payment_mix.full], ["Goods Flex (instalments)", data.payment_mix.bnpl]] }}>
            <SegmentBar parts={[
              { label: "Pay in full", value: data.payment_mix.full, color: SERIES.brand },
              { label: "Goods Flex", value: data.payment_mix.bnpl, color: FLEX },
            ]} />
          </ChartCard>

          <ChartCard title="Orders by status" subtitle={`Orders paid in the last ${days} days`}
            table={{ head: ["Status", "Orders"], rows: data.orders_by_status.map((s) => [titleCase(s.status), s.count]) }}>
            <BarList items={data.orders_by_status.map((s) => ({ label: titleCase(s.status), value: s.count }))} />
          </ChartCard>

          <ChartCard className="lg:col-span-2" title="Live listings by category" subtitle="Top 6 categories right now"
            table={{ head: ["Category", "Listings"], rows: data.top_categories.map((c) => [c.name, c.count]) }}>
            <BarList items={data.top_categories.map((c) => ({ label: c.name, value: c.count }))} color={SERIES.blue} />
          </ChartCard>
        </div>
      )}
    </section>
  );
}
