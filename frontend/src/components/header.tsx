"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Bell, ChevronDown, Heart, LayoutDashboard, LogOut, MapPin, MessageCircle, Plus, Search, Shield, Store, User } from "lucide-react";
import { Suspense, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Logo } from "./logo";
import { useAuth } from "./auth-provider";
import { http } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import { useIsAdminArea } from "@/lib/admin-area";
import { NG_STATES } from "@/lib/format";
import { Avatar } from "./avatar";

export function useCounts() {
  const { user } = useAuth();
  const [counts, setCounts] = useState({ messages: 0, notifications: 0 });
  const load = () => {
    if (!user) return;
    void Promise.all([
      http.get<{ unread: number }>("/conversations/unread-count"),
      http.get<{ unread: number }>("/notifications/unread-count"),
    ])
      .then(([m, n]) => setCounts({ messages: m.unread, notifications: n.unread }))
      .catch(() => {});
  };
  useEffect(load, [user]);
  usePolling(load, 30000, !!user);
  return user ? counts : { messages: 0, notifications: 0 };
}

function SearchBarInner({ className, autoFocus }: { className?: string; autoFocus?: boolean }) {
  const router = useRouter();
  const sp = useSearchParams();
  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const next = new URLSearchParams();
    const q = String(fd.get("q") ?? "").trim();
    const state = String(fd.get("state") ?? "");
    if (q) next.set("q", q);
    if (state) next.set("state", state);
    router.push(`/search?${next.toString()}`);
  }
  return (
    <form key={sp.toString()} onSubmit={submit} role="search" className={clsx("flex h-11 w-full overflow-hidden rounded-xl bg-white shadow-sm ring-1 ring-black/5", className)}>
      <label className="relative hidden shrink-0 items-center border-r border-line pl-3 sm:flex">
        <MapPin className="size-4 text-brand-700" aria-hidden />
        <span className="sr-only">Location</span>
        <select name="state" defaultValue={sp.get("state") ?? ""} className="h-full max-w-36 appearance-none bg-transparent pl-1.5 pr-6 text-sm font-medium text-ink outline-none">
          <option value="">All Nigeria</option>
          {NG_STATES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-1.5 size-3.5 text-muted" aria-hidden />
      </label>
      <input
        name="q"
        defaultValue={sp.get("q") ?? ""}
        autoFocus={autoFocus}
        type="search"
        placeholder="I am looking for…"
        aria-label="Search Goods.ng"
        className="min-w-0 flex-1 px-3 text-[15px] text-ink outline-none placeholder:text-muted/80"
      />
      <button type="submit" className="grid w-12 shrink-0 place-items-center bg-accent-500 text-ink transition hover:bg-accent-400 sm:w-14" aria-label="Search">
        <Search className="size-5" />
      </button>
    </form>
  );
}

export function SearchBar(props: { className?: string; autoFocus?: boolean }) {
  return (
    <Suspense fallback={<div className={clsx("h-11 w-full rounded-xl bg-white/90", props.className)} />}>
      <SearchBarInner {...props} />
    </Suspense>
  );
}

function AccountMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();
  useEffect(() => {
    const close = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && setOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);
  if (!user) return null;
  const item = "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm hover:bg-canvas";
  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex items-center gap-1.5 rounded-full py-1 pl-1 pr-2 text-white hover:bg-white/10"
      >
        <Avatar name={user.full_name} src={user.avatar_url} className="size-8 bg-white/15 text-sm text-white ring-1 ring-white/30" />
        <ChevronDown className="size-4" aria-hidden />
        <span className="sr-only">Account menu</span>
      </button>
      {open && (
        <div className="absolute right-0 top-11 z-50 w-60 rounded-xl bg-white p-1.5 text-ink shadow-[var(--shadow-pop)] ring-1 ring-line" onClick={() => setOpen(false)}>
          <div className="border-b border-line px-3 pb-2 pt-1.5">
            <p className="truncate text-sm font-semibold">{user.full_name}</p>
            <p className="truncate text-xs text-muted">{user.email}</p>
          </div>
          <Link href="/account" className={item}><User className="size-4" />My account</Link>
          <Link href="/orders" className={item}><LayoutDashboard className="size-4" />My orders</Link>
          <Link href="/saved" className={item}><Heart className="size-4" />Saved items</Link>
          {user.account_type !== "staff" && (user.seller ? (
            <Link href="/seller" className={item}><Store className="size-4" />Seller dashboard</Link>
          ) : (
            <Link href="/seller/onboarding" className={item}><Store className="size-4" />Start selling</Link>
          ))}
          {user.role !== "user" && <a href={process.env.NEXT_PUBLIC_ADMIN_URL || "/admin"} className={item}><Shield className="size-4" />Admin</a>}
          <button
            className={clsx(item, "w-full text-red-600")}
            onClick={async () => {
              await logout();
              router.push("/");
            }}
          >
            <LogOut className="size-4" />Log out
          </button>
        </div>
      )}
    </div>
  );
}

export function Header() {
  const { user, loading } = useAuth();
  const counts = useCounts();
  const compact = useIsAdminArea();
  return (
    <header className="site-header sticky top-0 z-40 bg-brand-800 text-white shadow-md">
      <div className="container-page flex h-14 items-center gap-3 md:h-16">
        <Logo light />
        {!compact && <SearchBar className="mx-auto hidden max-w-2xl md:flex" />}
        <nav className="ml-auto flex items-center gap-1" aria-label="Account">
          {!loading && user && (
            <>
{user.account_type !== "staff" && (
                            <Link href="/messages" className="relative hidden rounded-full p-2 hover:bg-white/10 md:block" aria-label={`Messages (${counts.messages} unread)`}>
                <MessageCircle className="size-5" />
                {counts.messages > 0 && <Dot n={counts.messages} />}
              </Link>
              )}
              <Link href="/notifications" className="relative rounded-full p-2 hover:bg-white/10" aria-label={`Notifications (${counts.notifications} unread)`}>
                <Bell className="size-5" />
                {counts.notifications > 0 && <Dot n={counts.notifications} />}
              </Link>
              {user.account_type !== "staff" && (
              <Link href="/saved" className="hidden rounded-full p-2 hover:bg-white/10 md:block" aria-label="Saved items">
                <Heart className="size-5" />
              </Link>
              )}
              <div className="hidden md:block">
                <AccountMenu />
              </div>
            </>
          )}
          {!loading && !user && (
            <div className="flex items-center gap-1 text-sm font-semibold">
              <Link href="/login" className="rounded-lg px-3 py-2 hover:bg-white/10">Sign in</Link>
              <Link href="/register" className="hidden rounded-lg px-3 py-2 hover:bg-white/10 sm:block">Register</Link>
            </div>
          )}
          {user?.account_type !== "staff" && <Link
            href={user?.seller ? "/seller/products/new" : "/seller/onboarding"}
            className="ml-1 hidden h-10 items-center gap-1.5 rounded-lg bg-accent-500 px-4 text-sm font-bold text-ink shadow-sm transition hover:bg-accent-400 md:inline-flex"
          >
            <Plus className="size-4" /> SELL
          </Link>}
        </nav>
      </div>
      {!compact && (
        <div className="container-page pb-2.5 md:hidden">
          <SearchBar />
        </div>
      )}
    </header>
  );
}

function Dot({ n }: { n: number }) {
  return (
    <span className="absolute -right-0.5 -top-0.5 grid min-w-[18px] place-items-center rounded-full bg-accent-500 px-1 text-[10px] font-bold leading-[18px] text-ink">
      {n > 99 ? "99+" : n}
    </span>
  );
}
