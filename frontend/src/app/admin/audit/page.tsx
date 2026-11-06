"use client";

import { Fragment, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import {
  Ban, BookOpen, ChevronDown, Download, Eye, KeyRound, LogIn, LogOut, MousePointerClick, Search, ShieldAlert, X,
} from "lucide-react";
import { AdminPageHeader, FilterChips } from "@/components/admin-ui";
import { Avatar } from "@/components/avatar";
import { Alert, Button, Skeleton, useToast } from "@/components/ui";
import { getAccessToken } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { timeAgo, titleCase } from "@/lib/format";

type Actor = { id: string; name: string; email: string; role: string };
type Entry = {
  id: string; actor: Actor; action: string; category: "action" | "auth" | "view" | "api"; outcome: "success" | "denied" | "failed";
  target_type: string; target_id: string | null; details: Record<string, unknown>; ip: string | null; user_agent: string | null; created_at: string;
};
type Page = { items: Entry[]; total: number; page: number; pages: number };
type AdminRow = Actor & { actions: number; sign_ins: number; issues: number; page_views: number; last_active: string | null; is_active: boolean };
type Summary = { days: number; admins: AdminRow[]; totals: { actions: number; auth_events: number; issues: number; active_admins: number } };

const RANGES = [{ value: "1", label: "Today" }, { value: "7", label: "7 days" }, { value: "30", label: "30 days" }, { value: "90", label: "90 days" }];
const TYPES = [
  { value: "", label: "All activity" },
  { value: "action", label: "Admin actions" },
  { value: "auth", label: "Sign-ins" },
  { value: "issues", label: "Blocked & failed" },
  { value: "view", label: "Pages viewed" },
];

/* ---------- plain-English descriptions ---------- */

const VERBS: Record<string, string> = {
  "user.status": "changed a customer account's access",
  "seller.suspend": "changed a seller's suspension",
  "verification.decide": "decided a seller verification",
  "kyc.reveal": "revealed a KYC document number",
  "product.approve": "approved a listing",
  "product.reject": "rejected a listing",
  "product.deactivate": "took down a listing",
  "product.feature": "featured a listing",
  "product.unfeature": "removed a listing from featured",
  "dispute.review": "started reviewing a dispute",
  "dispute.resolve": "resolved a dispute",
  "refund.approve": "approved and executed a refund",
  "refund.reject": "rejected a refund",
  "plan.upsert": "edited a Premium plan",
  "review.moderate": "moderated a review",
  "report.handle": "handled a report",
  "settings.update": "changed platform settings",
  "category.create": "created a category",
  "category.update": "updated a category",
  "category.reorder": "reordered categories",
  "subscription.grant": "granted Premium to a seller",
  "subscription.cancel": "cancelled a Premium subscription",
  "role.create": "created a role",
  "role.update": "changed a role's permissions",
  "role.delete": "deleted a role",
  "staff.create": "invited a staff member",
  "staff.update": "updated a staff member",
  "staff.resend_invite": "re-sent a staff invitation",
  "activity.export": "exported the activity log",
  "auth.sign_in": "signed in",
  "auth.sign_out": "signed out",
  "auth.sign_in_failed": "failed to sign in",
  "auth.2fa_failed": "entered a wrong 2FA code",
  "page.view": "viewed",
};

function describe(e: Entry) {
  if (e.category === "view") return <>viewed <b>{String(e.details.title ?? e.target_id ?? "a page")}</b></>;
  if (e.category === "api") {
    const verb = e.outcome === "denied" ? "was blocked from" : e.outcome === "failed" ? "tried (and failed)" : "made";
    return <>{verb} a <b>{String(e.details.method ?? "")}</b> request to <code className="rounded bg-canvas px-1 text-[12px]">{e.target_id}</code></>;
  }
  const extra = e.action === "auth.sign_in" && e.details.method ? ` with ${e.details.method}` : "";
  return <>{VERBS[e.action] ?? titleCase(e.action.replace(/\./g, " "))}{extra}</>;
}

function icon(e: Entry) {
  if (e.outcome !== "success") return { I: e.outcome === "denied" ? Ban : ShieldAlert, tone: "bg-red-50 text-red-600" };
  if (e.category === "auth") return { I: e.action === "auth.sign_out" ? LogOut : e.action.includes("2fa") ? KeyRound : LogIn, tone: "bg-sky-50 text-sky-700" };
  if (e.category === "view") return { I: Eye, tone: "bg-canvas text-muted" };
  return { I: MousePointerClick, tone: "bg-brand-50 text-brand-700" };
}

const lagosDay = (iso: string) => new Intl.DateTimeFormat("en-GB", { timeZone: "Africa/Lagos", weekday: "long", day: "numeric", month: "long", year: "numeric" }).format(new Date(iso));
const lagosTime = (iso: string) => new Intl.DateTimeFormat("en-GB", { timeZone: "Africa/Lagos", hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date(iso));

function browser(ua: string | null) {
  if (!ua) return null;
  const b = /Edg\//.test(ua) ? "Edge" : /Chrome\//.test(ua) ? "Chrome" : /Firefox\//.test(ua) ? "Firefox" : /Safari\//.test(ua) ? "Safari" : ua.split(/[/ ]/)[0].slice(0, 24) || "Unknown client";
  const os = /Windows/.test(ua) ? "Windows" : /Android/.test(ua) ? "Android" : /iPhone|iPad/.test(ua) ? "iOS" : /Mac OS X/.test(ua) ? "macOS" : /Linux/.test(ua) ? "Linux" : "";
  return os ? `${b} on ${os}` : b;
}

/* ---------- page ---------- */

export default function Page() {
  const toast = useToast();
  const [days, setDays] = useState("7");
  const [type, setType] = useState("");
  const [actor, setActor] = useState("");
  const [q, setQ] = useState("");
  const [applied, setApplied] = useState("");
  const [page, setPage] = useState(1);
  const [items, setItems] = useState<Entry[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => { const t = setTimeout(() => setApplied(q.trim()), 350); return () => clearTimeout(t); }, [q]);

  const filters = useMemo(() => ({
    days: Number(days),
    actor_id: actor || undefined,
    category: type === "" ? undefined : type === "issues" ? "all" : type,
    outcome: undefined as string | undefined,
    q: applied || undefined,
  }), [days, actor, type, applied]);
  const query = { ...filters, outcome: type === "issues" ? undefined : filters.outcome };
  const issuesOnly = type === "issues";

  const { data: summary } = useApi<Summary>("/admin/audit-logs/summary", { days: Number(days) });
  // "Blocked & failed" = denied + failed; the API filters one outcome at a time, so fetch both via two pages.
  const { data: denied } = useApi<Page>(issuesOnly ? "/admin/audit-logs" : null, { ...query, outcome: "denied", page_size: 100 });
  const { data: failed } = useApi<Page>(issuesOnly ? "/admin/audit-logs" : null, { ...query, outcome: "failed", page_size: 100 });
  const { data, error, loading } = useApi<Page>(issuesOnly ? null : "/admin/audit-logs", { ...query, page, page_size: 50 });

  // Reset paging when filters change; accumulate pages for "Load more".
  const key = JSON.stringify(filters);
  useEffect(() => { void Promise.resolve().then(() => { setPage(1); setItems([]); }); }, [key]);
  useEffect(() => {
    if (!data) return;
    void Promise.resolve().then(() => setItems((prev) => (data.page === 1 ? data.items : [...prev, ...data.items.filter((x) => !prev.some((p) => p.id === x.id))])));
  }, [data]);

  const list = issuesOnly
    ? [...(denied?.items ?? []), ...(failed?.items ?? [])].sort((a, b) => b.created_at.localeCompare(a.created_at))
    : items;
  const total = issuesOnly ? (denied?.total ?? 0) + (failed?.total ?? 0) : data?.total ?? 0;
  const groups = useMemo(() => {
    const g: { day: string; entries: Entry[] }[] = [];
    for (const e of list) {
      const d = lagosDay(e.created_at);
      if (g.at(-1)?.day !== d) g.push({ day: d, entries: [] });
      g.at(-1)!.entries.push(e);
    }
    return g;
  }, [list]);

  async function exportCsv() {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      Object.entries({ ...filters, category: issuesOnly ? "all" : filters.category }).forEach(([k, v]) => { if (v !== undefined && v !== "") params.set(k, String(v)); });
      const res = await fetch(`/api/v1/admin/audit-logs/export?${params}`, { headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` }, credentials: "same-origin" });
      if (!res.ok) throw new Error("Export failed");
      const url = URL.createObjectURL(await res.blob());
      const a = Object.assign(document.createElement("a"), { href: url, download: `goodsng-admin-activity-${days}d.csv` });
      a.click(); URL.revokeObjectURL(url);
      toast("Activity exported");
    } catch (e) { toast(e instanceof Error ? e.message : "Export failed", "bad"); }
    finally { setExporting(false); }
  }

  const selected = summary?.admins.find((a) => a.id === actor);

  return (
    <div className="space-y-6">
      <AdminPageHeader icon={BookOpen} title="Activity log"
        description="Everything every admin does — sign-ins, actions, blocked attempts and pages viewed. Entries are permanent and can't be edited or deleted."
        actions={<Button variant="outline" loading={exporting} onClick={exportCsv}><Download className="size-4" />Export CSV</Button>} />

      {/* Filters: one row, scoping everything below */}
      <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
        <FilterChips label="Period" value={days} onChange={setDays} options={RANGES} />
        <div className="flex flex-1 flex-col gap-2 sm:flex-row lg:justify-end">
          <select className="input sm:w-56" value={actor} onChange={(e) => setActor(e.target.value)} aria-label="Admin">
            <option value="">All admins</option>
            {summary?.admins.map((a) => <option key={a.id} value={a.id}>{a.name}{a.is_active ? "" : " (deactivated)"}</option>)}
          </select>
          <div className="relative sm:w-64">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            <input className="input pl-9 pr-9" placeholder="Search action, ID or IP…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search activity" />
            {q && <button type="button" aria-label="Clear search" onClick={() => setQ("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted hover:bg-canvas"><X className="size-4" /></button>}
          </div>
        </div>
      </div>

      {/* Totals */}
      {!summary ? <Skeleton className="h-24 rounded-2xl" /> : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[
            { label: "Admin actions", value: summary.totals.actions },
            { label: "Sign-in events", value: summary.totals.auth_events },
            { label: "Blocked or failed", value: summary.totals.issues, warn: summary.totals.issues > 0 },
            { label: "Active admins", value: `${summary.totals.active_admins} of ${summary.admins.length}` },
          ].map((t) => (
            <div key={t.label} className={clsx("card p-4", t.warn && "ring-2 ring-red-200")}>
              <p className="text-xs font-medium text-muted">{t.label}</p>
              <p className={clsx("mt-0.5 text-2xl font-bold tabular-nums", t.warn && "text-red-600")}>{t.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Per-admin breakdown */}
      {summary && (
        <section className="card overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <h2 className="font-semibold">By admin</h2>
            {actor && <button type="button" className="text-sm font-semibold text-brand-700 hover:underline" onClick={() => setActor("")}>Show everyone</button>}
          </div>
          <ul className="divide-y divide-line/70">
            {summary.admins.map((a) => (
              <li key={a.id}>
                <button type="button" onClick={() => setActor(actor === a.id ? "" : a.id)} aria-pressed={actor === a.id}
                  className={clsx("grid w-full grid-cols-[auto_1fr_auto] items-center gap-3 px-4 py-3 text-left transition hover:bg-canvas sm:grid-cols-[auto_1fr_repeat(4,5.5rem)]", actor === a.id && "bg-brand-50/60")}>
                  <Avatar name={a.name} className="size-9 text-xs" />
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-semibold">{a.name}{!a.is_active && <span className="ml-1.5 text-xs font-normal text-muted">(deactivated)</span>}</span>
                    <span className="block truncate text-xs text-muted">{a.role} · {a.last_active ? `active ${timeAgo(a.last_active)}` : "never active"}</span>
                  </span>
                  <span className="text-right text-sm sm:hidden"><b className="tabular-nums">{a.actions}</b> <span className="text-xs text-muted">actions</span></span>
                  {[["Actions", a.actions], ["Sign-ins", a.sign_ins], ["Blocked/failed", a.issues], ["Pages viewed", a.page_views]].map(([l, v]) => (
                    <span key={l as string} className="hidden text-right sm:block">
                      <span className={clsx("block text-sm font-semibold tabular-nums", l === "Blocked/failed" && Number(v) > 0 && "text-red-600")}>{v}</span>
                      <span className="block text-[11px] text-muted">{l}</span>
                    </span>
                  ))}
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Timeline */}
      <section className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <FilterChips label="Activity type" value={type} onChange={setType} options={TYPES} />
          <p className="text-xs text-muted">{total.toLocaleString()} entr{total === 1 ? "y" : "ies"}{selected ? ` by ${selected.name}` : ""}</p>
        </div>
        {error && <Alert tone="bad">{error}</Alert>}
        {!data && !issuesOnly && loading ? <Skeleton className="h-64 rounded-2xl" /> : !list.length ? (
          <div className="card px-6 py-14 text-center">
            <p className="font-semibold">No activity matches these filters</p>
            <p className="text-sm text-muted">Try a longer period or a different admin.</p>
          </div>
        ) : (
          <div className="card overflow-hidden">
            {groups.map((g) => (
              <Fragment key={g.day}>
                <p className="border-b border-line bg-canvas px-4 py-2 text-xs font-bold uppercase tracking-wider text-muted">{g.day}</p>
                <ul className="divide-y divide-line/60">
                  {g.entries.map((e) => {
                    const { I, tone } = icon(e);
                    const expanded = open === e.id;
                    return (
                      <li key={e.id}>
                        <button type="button" onClick={() => setOpen(expanded ? null : e.id)} aria-expanded={expanded}
                          className="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-canvas/60">
                          <span className={clsx("mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg", tone)}><I className="size-4" /></span>
                          <span className="min-w-0 flex-1">
                            <span className="block text-sm leading-snug">
                              <b>{e.actor.name}</b> {describe(e)}
                              {e.target_id && e.category === "action" && <span className="text-muted"> · {e.target_type} <code className="text-[11px]">{e.target_id.slice(0, 8)}</code></span>}
                            </span>
                            <span className="mt-0.5 flex flex-wrap items-center gap-x-2 text-xs text-muted">
                              <span>{lagosTime(e.created_at)}</span>
                              {e.ip && <span>· IP {e.ip}</span>}
                              {browser(e.user_agent) && <span className="hidden sm:inline">· {browser(e.user_agent)}</span>}
                              {e.outcome !== "success" && <span className="rounded-full bg-red-50 px-1.5 font-semibold text-red-700">{e.outcome === "denied" ? "Blocked" : "Failed"}</span>}
                            </span>
                          </span>
                          <ChevronDown className={clsx("mt-1 size-4 shrink-0 text-muted transition", expanded && "rotate-180")} />
                        </button>
                        {expanded && (
                          <div className="mx-4 mb-3 ml-[3.75rem] space-y-2 rounded-lg bg-canvas p-3 text-xs">
                            <dl className="grid gap-x-4 gap-y-1 sm:grid-cols-[8rem_1fr]">
                              <dt className="text-muted">Admin</dt><dd>{e.actor.name} · {e.actor.email} · {e.actor.role}</dd>
                              <dt className="text-muted">Event</dt><dd className="font-mono">{e.action} ({e.category}, {e.outcome})</dd>
                              <dt className="text-muted">Target</dt><dd className="font-mono break-all">{e.target_type}{e.target_id ? `: ${e.target_id}` : ""}</dd>
                              <dt className="text-muted">When</dt><dd>{lagosDay(e.created_at)}, {lagosTime(e.created_at)} (Lagos)</dd>
                              {e.user_agent && <><dt className="text-muted">Device</dt><dd className="break-all">{e.user_agent}</dd></>}
                            </dl>
                            {Object.keys(e.details ?? {}).length > 0 && (
                              <pre className="max-h-60 overflow-auto rounded-md bg-white p-2 font-mono text-[11px] ring-1 ring-line">{JSON.stringify(e.details, null, 2)}</pre>
                            )}
                          </div>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </Fragment>
            ))}
          </div>
        )}
        {!issuesOnly && data && data.page < data.pages && (
          <div className="text-center"><Button variant="outline" loading={loading} onClick={() => setPage((p) => p + 1)}>Load more</Button></div>
        )}
      </section>
    </div>
  );
}
