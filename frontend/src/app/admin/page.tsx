"use client";

import Link from "next/link";
import clsx from "clsx";
import {
  ArrowRight, BadgeCheck, CalendarClock, CheckCircle2, Coins, Crown, Flag, Gavel, Landmark, Package, PiggyBank, Receipt,
  RotateCcw, ShieldCheck, Store, TrendingDown, UserCheck, Users, Wallet,
} from "lucide-react";
import { Alert, Skeleton } from "@/components/ui";
import { useAuth } from "@/components/auth-provider";
import { useApi } from "@/lib/hooks";
import { useAdminBase } from "@/lib/admin-area";
import { naira } from "@/lib/format";
import { OverviewCharts } from "./overview-charts";

type O = Record<string, number | string> & { bnpl: Record<string, number | string> };

const QUEUE = [
  { key: "open_disputes", label: "Open disputes", hint: "Buyers and sellers waiting on a decision", href: "/disputes", icon: Gavel },
  { key: "pending_refunds", label: "Refunds to approve", hint: "Needs a second administrator", href: "/refunds", icon: RotateCcw },
  { key: "pending_verifications", label: "Verifications", hint: "Seller ID / business documents", href: "/verifications", icon: BadgeCheck },
  { key: "pending_listings", label: "Listings in review", hint: "New ads waiting for approval", href: "/products?status=pending_review", icon: Package },
  { key: "open_reports", label: "Open reports", hint: "Flagged listings, users and messages", href: "/reports", icon: Flag },
] as const;

function greeting() {
  const h = Number(new Intl.DateTimeFormat("en-GB", { hour: "numeric", hour12: false, timeZone: "Africa/Lagos" }).format(new Date()));
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

function Kpi({ icon: Icon, label, value, hint, tone = "brand" }: { icon: React.ElementType; label: string; value: React.ReactNode; hint?: string; tone?: "brand" | "amber" | "mint" | "sky" | "rose" }) {
  const tones = { brand: "bg-brand-50 text-brand-700", amber: "bg-amber-50 text-amber-700", mint: "bg-accent-500/25 text-brand-800", sky: "bg-sky-50 text-sky-700", rose: "bg-rose-50 text-rose-700" };
  return (
    <div className="card flex items-start gap-3 p-4">
      <span className={clsx("grid size-10 shrink-0 place-items-center rounded-xl", tones[tone])}><Icon className="size-5" /></span>
      <div className="min-w-0">
        <p className="text-xs font-medium text-muted">{label}</p>
        <p className="mt-0.5 truncate text-xl font-bold tabular-nums tracking-tight">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
      </div>
    </div>
  );
}

function Section({ title, children, cols = "lg:grid-cols-4" }: { title: string; children: React.ReactNode; cols?: string }) {
  return (
    <section>
      <h2 className="mb-3 text-sm font-bold uppercase tracking-wider text-muted">{title}</h2>
      <div className={clsx("grid gap-3 sm:grid-cols-2", cols)}>{children}</div>
    </section>
  );
}

export default function Page() {
  const { data: o, error } = useApi<O>("/admin/overview");
  const { user } = useAuth();
  const base = useAdminBase();
  const link = (h: string) => (base || "") + h;
  const first = user?.full_name.split(" ")[0];

  if (error) return <Alert tone="bad">{error}</Alert>;
  const waiting = o ? QUEUE.filter((q) => Number(o[q.key]) > 0) : [];
  const totalWaiting = waiting.reduce((n, q) => n + Number(o![q.key]), 0);

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted">{greeting()}{first ? `, ${first}` : ""} 👋</p>
          <h1 className="text-2xl font-bold tracking-tight">Marketplace overview</h1>
        </div>
        {o && (
          <p className={clsx("inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold",
            totalWaiting ? "bg-amber-100 text-amber-900" : "bg-brand-50 text-brand-800")}>
            {totalWaiting ? <>{totalWaiting} item{totalWaiting === 1 ? "" : "s"} need attention</> : <><CheckCircle2 className="size-4" />All caught up</>}
          </p>
        )}
      </div>

      {/* Work queue */}
      <section aria-labelledby="queue">
        <h2 id="queue" className="mb-3 text-sm font-bold uppercase tracking-wider text-muted">Needs your attention</h2>
        {!o ? <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">{QUEUE.map((q) => <Skeleton key={q.key} className="h-28 rounded-2xl" />)}</div> : (
          <div className="grid grid-cols-2 gap-3 xl:grid-cols-5">
            {QUEUE.map((q) => {
              const n = Number(o[q.key]);
              return (
                <Link key={q.key} href={link(q.href)}
                  className={clsx("group card flex flex-col p-4 transition hover:-translate-y-0.5 hover:shadow-[var(--shadow-pop)]",
                    n > 0 && "ring-2 ring-amber-300")}>
                  <span className="flex items-center justify-between">
                    <span className={clsx("grid size-9 place-items-center rounded-lg", n > 0 ? "bg-amber-100 text-amber-700" : "bg-canvas text-muted")}><q.icon className="size-[18px]" /></span>
                    <span className={clsx("text-2xl font-bold tabular-nums", n > 0 ? "text-amber-700" : "text-ink/40")}>{n}</span>
                  </span>
                  <span className="mt-3 font-semibold">{q.label}</span>
                  <span className="text-xs text-muted">{n > 0 ? q.hint : "Nothing waiting"}</span>
                  <span className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-brand-700 opacity-0 transition group-hover:opacity-100">
                    {n > 0 ? "Review now" : "Open"} <ArrowRight className="size-3.5" />
                  </span>
                </Link>
              );
            })}
          </div>
        )}
      </section>

      <OverviewCharts />

      {!o ? <Skeleton className="h-72 rounded-2xl" /> : (
        <>
          <Section title="Money">
            <Kpi icon={Coins} label="Completed sales value" value={naira(String(o.total_transaction_value))} hint={`${o.completed_protected} protected orders completed`} />
            <Kpi icon={Landmark} label="Held in escrow now" value={naira(String(o.in_escrow_value))} tone="sky" hint="Released when buyers confirm" />
            <Kpi icon={PiggyBank} label="Platform revenue" value={naira(String(o.platform_revenue))} tone="mint" hint="Commission, protection fees & Premium" />
            <Kpi icon={Receipt} label="Paid orders" value={Number(o.total_orders).toLocaleString()} tone="amber" />
          </Section>

          <Section title="Marketplace">
            <Kpi icon={Users} label="Registered users" value={Number(o.total_users).toLocaleString()} hint={`${o.active_buyers_30d} bought in the last 30 days`} />
            <Kpi icon={Store} label="Active sellers" value={o.active_sellers} tone="sky" hint={`${o.total_sellers} seller profiles`} />
            <Kpi icon={UserCheck} label="Verified sellers" value={o.verified_sellers} tone="mint" hint={`${o.premium_sellers} on Premium`} />
            <Kpi icon={Package} label="Live listings" value={Number(o.active_listings).toLocaleString()} tone="amber" hint={`${o.pending_listings} waiting for review`} />
          </Section>

          <Section title="Trust & risk" cols="lg:grid-cols-3">
            <Kpi icon={ShieldCheck} label="Dispute rate" value={`${o.dispute_rate}%`} tone={Number(o.dispute_rate) > 5 ? "rose" : "brand"} hint="Orders with a dispute ÷ paid orders" />
            <Kpi icon={TrendingDown} label="Refund rate" value={`${o.refund_rate}%`} tone={Number(o.refund_rate) > 5 ? "rose" : "brand"} hint="Refunded ÷ paid orders" />
            <Kpi icon={Crown} label="Premium sellers" value={o.premium_sellers} tone="amber" />
          </Section>

          <Section title="Goods Flex (pay in instalments)" cols="lg:grid-cols-4">
            <Kpi icon={CalendarClock} label="Applications" value={o.bnpl.applications} tone="mint" hint={`${o.bnpl.approved} approved`} />
            <Kpi icon={Wallet} label="Active plans" value={o.bnpl.active_agreements} tone="mint" />
            <Kpi icon={Coins} label="Outstanding balance" value={naira(String(o.bnpl.outstanding))} tone="sky" />
            <Kpi icon={Flag} label="Overdue instalments" value={o.bnpl.overdue_installments} tone={Number(o.bnpl.overdue_installments) > 0 ? "rose" : "brand"} />
          </Section>
        </>
      )}
    </div>
  );
}
