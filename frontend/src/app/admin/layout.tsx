"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import clsx from "clsx";
import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, BadgeCheck, Banknote, BarChart3, BookOpen, CalendarClock, ChevronDown, Crown, ExternalLink, FileWarning, Flag,
  FolderTree, Gavel,
  KeyRound, Landmark, LayoutDashboard, LogOut, Megaphone, Menu, Package, Receipt, RotateCcw, Search, Settings, ShieldCheck,
  Star, Store, UserCog, UserRound, Users, X,
} from "lucide-react";
import { PageLoader } from "@/components/ui";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/components/auth-provider";
import { Avatar } from "@/components/avatar";
import { AdminDialogHost } from "@/components/admin-ui";
import { AfricaSkyline } from "@/components/africa-skyline";
import { useApi, usePolling } from "@/lib/hooks";
import { http } from "@/lib/api";
import { useAdminBase } from "@/lib/admin-area";

type Item = { href: string; label: string; icon: React.ElementType; perm: string; exact?: boolean; count?: string; keywords?: string };
const GROUPS: { title: string | null; items: Item[] }[] = [
  { title: null, items: [
    { href: "/admin", label: "Overview", icon: LayoutDashboard, perm: "analytics.view", exact: true, keywords: "dashboard home stats" },
    { href: "/admin/live", label: "Live traffic", icon: Activity, perm: "analytics.view", keywords: "visitors active online traffic" },
  ] },
  { title: "Marketplace", items: [
    { href: "/admin/users", label: "Users", icon: Users, perm: "users.manage", keywords: "customers accounts buyers" },
    { href: "/admin/sellers", label: "Sellers", icon: Store, perm: "sellers.verify", keywords: "stores suspend premium grant" },
    { href: "/admin/verifications", label: "Seller verification", icon: BadgeCheck, perm: "sellers.verify", count: "verifications", keywords: "kyc nin cac identity" },
    { href: "/admin/products", label: "Listings", icon: Package, perm: "listings.moderate", count: "products", keywords: "products ads moderate approve feature" },
    { href: "/admin/categories", label: "Categories", icon: FolderTree, perm: "categories.manage" },
  ] },
  { title: "Orders & money", items: [
    { href: "/admin/orders", label: "Orders", icon: Receipt, perm: "orders.view" },
    { href: "/admin/disputes", label: "Disputes", icon: Gavel, perm: "disputes.resolve", count: "disputes", keywords: "complaints resolve" },
    { href: "/admin/refunds", label: "Refunds", icon: RotateCcw, perm: "refunds.approve", count: "refunds", keywords: "approve second approver" },
    { href: "/admin/payouts", label: "Seller payouts", icon: Banknote, perm: "payouts.approve", keywords: "withdrawals approve seller bank" },
    { href: "/admin/payments", label: "Payments", icon: BarChart3, perm: "payments.view", keywords: "transactions paystack" },
    { href: "/admin/escrow", label: "Escrow & ledger", icon: Landmark, perm: "payments.view", keywords: "reconciliation balance" },
    { href: "/admin/bnpl", label: "Goods Flex", icon: CalendarClock, perm: "bnpl.view", keywords: "bnpl instalments credit loans" },
    { href: "/admin/subscriptions", label: "Premium plans", icon: Crown, perm: "subscriptions.manage", keywords: "subscriptions premium" },
    { href: "/admin/promotions", label: "Promotions", icon: Megaphone, perm: "promotions.manage", keywords: "featured boosts" },
  ] },
  { title: "Trust & safety", items: [
    { href: "/admin/reports", label: "Reports", icon: Flag, perm: "reports.manage", count: "reports", keywords: "flags abuse scam" },
    { href: "/admin/reviews", label: "Reviews", icon: Star, perm: "reviews.moderate", count: "reviews", keywords: "ratings" },
  ] },
  { title: "Administration", items: [
    { href: "/admin/staff", label: "Admin team", icon: UserCog, perm: "super_admin", keywords: "staff invite" },
    { href: "/admin/roles", label: "Roles & permissions", icon: KeyRound, perm: "super_admin" },
    { href: "/admin/settings", label: "Platform settings", icon: Settings, perm: "settings.manage", keywords: "fees commission flex rules" },
    { href: "/admin/audit", label: "Activity log", icon: BookOpen, perm: "audit.view", keywords: "audit history logs who did what sign-ins" },
  ] },
];

type Me = { role: string; role_name: string; is_super_admin: boolean; permissions: string[] };

function useNav() {
  const base = useAdminBase();
  const pathname = usePathname();
  const { data: me } = useApi<Me>("/admin/me");
  const { data: counts, reload } = useApi<Record<string, number>>("/admin/nav-counts");
  usePolling(reload, 60_000);
  const groups = useMemo(() => {
    const perms = new Set([...(me?.permissions ?? []), ...(me?.is_super_admin ? ["super_admin"] : [])]);
    return GROUPS.map((g) => ({
      ...g,
      items: g.items.filter((i) => perms.has(i.perm)).map((i) => {
        const href = base + i.href.slice("/admin".length) || "/";
        return { ...i, href, active: i.exact ? pathname === href : pathname === href || pathname.startsWith(href + "/"), badge: i.count ? counts?.[i.count] ?? 0 : 0 };
      }),
    })).filter((g) => g.items.length);
  }, [me, counts, base, pathname]);
  return { me, groups };
}

type NavGroups = ReturnType<typeof useNav>["groups"];

function Sidebar({ groups, me, onNavigate }: { groups: NavGroups; me?: Me; onNavigate?: () => void }) {
  return (
    <nav aria-label="Admin" className="flex flex-col gap-5 p-3">
      {groups.map((g) => (
        <div key={g.title ?? "top"}>
          {g.title && <p className="px-3 pb-1.5 text-[11px] font-bold uppercase tracking-wider text-muted">{g.title}</p>}
          <ul className="space-y-0.5">
            {g.items.map((n) => (
              <li key={n.href}>
                <Link href={n.href} onClick={onNavigate} aria-current={n.active ? "page" : undefined}
                  className={clsx("group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                    n.active ? "bg-brand-50 font-semibold text-brand-800" : "text-ink/80 hover:bg-canvas hover:text-ink")}>
                  <n.icon className={clsx("size-[18px] shrink-0", n.active ? "text-brand-700" : "text-muted group-hover:text-ink")} />
                  <span className="flex-1 truncate">{n.label}</span>
                  {n.badge > 0 && <span className="min-w-5 rounded-full bg-amber-500 px-1.5 text-center text-[11px] font-bold leading-5 text-white" aria-label={`${n.badge} waiting`}>{n.badge > 99 ? "99+" : n.badge}</span>}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {me && !groups.length && <p className="flex items-center gap-2 p-3 text-sm text-muted"><FileWarning className="size-4" />No admin permissions assigned yet.</p>}
    </nav>
  );
}

function CommandPalette({ groups, onClose }: { groups: NavGroups; onClose: () => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [idx, setIdx] = useState(0);
  const items = useMemo(() => {
    const all = groups.flatMap((g) => g.items.map((i) => ({ ...i, group: g.title ?? "" })));
    const t = q.trim().toLowerCase();
    return t ? all.filter((i) => `${i.label} ${i.group} ${i.keywords ?? ""}`.toLowerCase().includes(t)) : all;
  }, [groups, q]);
  const go = (href: string) => { onClose(); router.push(href); };
  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/40 p-4 pt-[12vh] backdrop-blur-sm" onClick={onClose}>
      <div role="dialog" aria-label="Jump to a page" className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-line px-4">
          <Search className="size-5 text-muted" />
          <input autoFocus value={q} onChange={(e) => { setQ(e.target.value); setIdx(0); }} placeholder="Jump to… (users, disputes, refunds)"
            className="h-14 flex-1 bg-transparent text-[15px] outline-none"
            onKeyDown={(e) => {
              if (e.key === "ArrowDown") { e.preventDefault(); setIdx((i) => Math.min(i + 1, items.length - 1)); }
              if (e.key === "ArrowUp") { e.preventDefault(); setIdx((i) => Math.max(i - 1, 0)); }
              if (e.key === "Enter" && items[idx]) go(items[idx].href);
              if (e.key === "Escape") onClose();
            }} />
          <kbd className="rounded border border-line px-1.5 text-[11px] text-muted">Esc</kbd>
        </div>
        <ul className="max-h-[50vh] overflow-y-auto p-2">
          {items.map((i, n) => (
            <li key={i.href}>
              <button type="button" onMouseEnter={() => setIdx(n)} onClick={() => go(i.href)}
                className={clsx("flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm", n === idx ? "bg-brand-50 text-brand-900" : "text-ink/80")}>
                <i.icon className="size-4 text-muted" />
                <span className="flex-1">{i.label}</span>
                {i.badge > 0 && <span className="rounded-full bg-amber-100 px-2 text-xs font-semibold text-amber-800">{i.badge} waiting</span>}
                <span className="text-xs text-muted">{i.group}</span>
              </button>
            </li>
          ))}
          {!items.length && <li className="px-3 py-8 text-center text-sm text-muted">No pages match “{q}”.</li>}
        </ul>
      </div>
    </div>
  );
}

function UserMenu({ me }: { me?: Me }) {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);
  if (!user) return null;
  return (
    <div ref={ref} className="relative">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="flex items-center gap-2 rounded-full py-1 pl-1 pr-2 hover:bg-canvas">
        <Avatar name={user.full_name} src={user.avatar_url} className="size-8 text-xs" />
        <span className="hidden text-left leading-tight md:block">
          <span className="block max-w-36 truncate text-sm font-semibold">{user.full_name}</span>
          <span className="block text-[11px] text-muted">{me?.role_name ?? "Admin"}</span>
        </span>
        <ChevronDown className="hidden size-4 text-muted md:block" />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-60 overflow-hidden rounded-xl bg-white shadow-xl ring-1 ring-line">
          <div className="border-b border-line px-4 py-3">
            <p className="truncate text-sm font-semibold">{user.full_name}</p>
            <p className="truncate text-xs text-muted">{user.email}</p>
            <p className="mt-1.5 inline-flex items-center gap-1 rounded-full bg-brand-50 px-2 py-0.5 text-[11px] font-semibold text-brand-800"><ShieldCheck className="size-3" />{me?.role_name ?? "Admin"}</p>
          </div>
          <Link href="/account" onClick={() => setOpen(false)} className="flex items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-canvas"><UserRound className="size-4 text-muted" />Account & two-factor</Link>
          <a href={process.env.NEXT_PUBLIC_SITE_URL ?? "/"} className="flex items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-canvas"><ExternalLink className="size-4 text-muted" />View marketplace</a>
          <button type="button" onClick={async () => { await logout(); router.replace("/login"); }} className="flex w-full items-center gap-2.5 border-t border-line px-4 py-2.5 text-sm text-red-600 hover:bg-red-50"><LogOut className="size-4" />Sign out</button>
        </div>
      )}
    </div>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  const { me, groups } = useNav();
  const pathname = usePathname();
  const base = useAdminBase();
  const [drawer, setDrawer] = useState(false);
  const [palette, setPalette] = useState(false);
  const total = groups.flatMap((g) => g.items).reduce((n, i) => n + i.badge, 0);

  // Record which console pages each admin opens (the API de-duplicates repeat views).
  const pageTitle = groups.flatMap((g) => g.items).find((i) => i.active)?.label;
  useEffect(() => {
    const path = pathname.replace(/^\/admin(?=\/|$)/, "") || "/";
    void http.post("/admin/activity/view", { path, title: pageTitle }).catch(() => {});
  }, [pathname, pageTitle]);

  const onKey = useCallback((e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((p) => !p); }
  }, []);
  useEffect(() => { document.addEventListener("keydown", onKey); return () => document.removeEventListener("keydown", onKey); }, [onKey]);
  useEffect(() => { void Promise.resolve().then(() => setDrawer(false)); }, [pathname]);
  useEffect(() => { document.body.style.overflow = drawer ? "hidden" : ""; return () => { document.body.style.overflow = ""; }; }, [drawer]);

  return (
    <div data-admin-shell className="min-h-dvh bg-canvas">
      <header className="sticky top-0 z-40 border-b border-line bg-white/90 backdrop-blur">
        <div className="flex h-14 items-center gap-2 px-3 sm:px-4">
          <button type="button" onClick={() => setDrawer(true)} className="relative rounded-lg p-2 hover:bg-canvas lg:hidden" aria-label="Open menu">
            <Menu className="size-5" />
            {total > 0 && <span className="absolute right-1 top-1 size-2 rounded-full bg-amber-500" />}
          </button>
          <Link href={base || "/"} className="flex items-center gap-2 lg:w-[232px]">
            <span className="grid size-8 place-items-center rounded-lg bg-brand-700 text-white"><ShieldCheck className="size-[18px]" /></span>
            <span className="text-[15px] font-extrabold tracking-tight">Goods<span className="text-accent-500">.ng</span></span>
            <span className="rounded-md bg-ink px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-white">Admin</span>
          </Link>
          <button type="button" onClick={() => setPalette(true)}
            className="ml-auto flex h-9 items-center gap-2 rounded-lg bg-canvas px-3 text-sm text-muted ring-1 ring-line transition hover:text-ink sm:w-72 lg:ml-4">
            <Search className="size-4" /><span className="hidden sm:inline">Jump to…</span>
            <kbd className="ml-auto hidden rounded border border-line bg-white px-1.5 text-[11px] sm:inline">⌘K</kbd>
          </button>
          <div className="flex items-center gap-1 sm:ml-auto">
            {process.env.NODE_ENV !== "production" && (
              <span className="hidden rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-800 xl:inline" title="Payments, escrow, KYC and BNPL use mock providers">DEV · mock providers</span>
            )}
            <UserMenu me={me} />
          </div>
        </div>
      </header>

      <div className="lg:grid lg:grid-cols-[256px_minmax(0,1fr)]">
        <aside className="hidden border-r border-line bg-white lg:sticky lg:top-14 lg:block lg:h-[calc(100dvh-3.5rem)] lg:overflow-y-auto lg:overscroll-contain">
          <Sidebar groups={groups} me={me} />
        </aside>
        <main className="flex min-h-[calc(100dvh-3.5rem)] min-w-0 flex-col">
          <div className="flex-1 px-4 py-5 sm:px-6 lg:px-8 lg:py-7">
            <div className="mx-auto max-w-7xl">{children}</div>
          </div>
          {/* Same skyline as the sign-in screens — no site footer in the console. */}
          <AfricaSkyline className="pointer-events-none mt-10" />
        </main>
      </div>

      {/* Phone/tablet drawer */}
      <div className={clsx("fixed inset-0 z-50 lg:hidden", drawer ? "visible" : "invisible")} aria-hidden={!drawer}>
        <div className={clsx("absolute inset-0 bg-black/40 transition-opacity", drawer ? "opacity-100" : "opacity-0")} onClick={() => setDrawer(false)} />
        <div className={clsx("absolute inset-y-0 left-0 flex w-[min(300px,85vw)] flex-col bg-white shadow-2xl transition-transform", drawer ? "translate-x-0" : "-translate-x-full")}>
          <div className="flex h-14 items-center justify-between border-b border-line px-4">
            <span className="text-sm font-bold">Admin menu</span>
            <button type="button" onClick={() => setDrawer(false)} className="rounded-lg p-2 hover:bg-canvas" aria-label="Close menu"><X className="size-5" /></button>
          </div>
          <div className="flex-1 overflow-y-auto overscroll-contain"><Sidebar groups={groups} me={me} onNavigate={() => setDrawer(false)} /></div>
        </div>
      </div>

      {/* Mounted only while open, so every open starts fresh with the cursor in the search box. */}
      {palette && <CommandPalette groups={groups} onClose={() => setPalette(false)} />}
      <AdminDialogHost />
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<PageLoader />}>
      <RequireAuth admin>{() => <Shell>{children}</Shell>}</RequireAuth>
    </Suspense>
  );
}
