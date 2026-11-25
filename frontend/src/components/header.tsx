"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Bell, ChevronDown, Heart, LayoutDashboard, LogOut, MapPin, MessageCircle, Plus, Search, Shield, Store, User } from "lucide-react";
import { Suspense, useEffect, useId, useRef, useState } from "react";
import clsx from "clsx";
import { Logo } from "./logo";
import { useAuth } from "./auth-provider";
import { http } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import { useIsAdminArea } from "@/lib/admin-area";
import { NG_STATES } from "@/lib/format";
import { useLocations } from "./state-city-select";
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
  const [location, setLocation] = useState({ state: sp.get("state") ?? "", city: sp.get("city") ?? "" });
  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const next = new URLSearchParams();
    const q = String(fd.get("q") ?? "").trim();
    if (q) next.set("q", q);
    if (location.state) next.set("state", location.state);
    if (location.city) next.set("city", location.city);
    router.push(`/search?${next.toString()}`);
  }
  return (
    <form key={sp.toString()} onSubmit={submit} role="search" className={clsx("relative flex h-11 w-full rounded-xl bg-white shadow-sm ring-1 ring-black/5", className)}>
      <LocationPicker
        state={location.state}
        city={location.city}
        onChange={setLocation}
      />
      <input
        name="q"
        defaultValue={sp.get("q") ?? ""}
        autoFocus={autoFocus}
        type="search"
        placeholder="I am looking for…"
        aria-label="Search Goods.ng"
        className="min-w-0 flex-1 px-3 text-[15px] text-ink outline-none placeholder:text-muted/80"
      />
      <button type="submit" className="grid w-12 shrink-0 place-items-center rounded-r-xl bg-accent-500 text-ink transition hover:bg-accent-400 sm:w-14" aria-label="Search">
        <Search className="size-5" />
      </button>
    </form>
  );
}

function LocationPicker({ state, city, onChange }: {
  state: string;
  city: string;
  onChange: (location: { state: string; city: string }) => void;
}) {
  const locations = useLocations();
  const searchId = useId();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const search = useRef<HTMLInputElement>(null);
  const states = (locations?.states ?? NG_STATES).filter((name) => name.toLowerCase().includes(query.trim().toLowerCase()));
  const cities = Object.entries(locations?.cities ?? {})
    .flatMap(([region, names]) => names.map((name) => ({ name, region })))
    .filter(({ name, region }) => {
      const term = query.trim().toLowerCase();
      return term && (name.toLowerCase().includes(term) || region.toLowerCase().includes(term));
    })
    .slice(0, 12);
  const label = city ? `${city}, ${state}` : state || "All Nigeria";

  useEffect(() => {
    if (open) search.current?.focus();
  }, [open]);
  useEffect(() => {
    const close = (e: PointerEvent) => {
      if (root.current && !root.current.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, []);

  const chooseRegion = (region: string) => {
    onChange({ state: region, city: "" });
    setOpen(false);
    setQuery("");
  };
  const chooseCity = (name: string, region: string) => {
    onChange({ state: region, city: name });
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={root} className="relative z-30 flex max-w-[42%] shrink-0 items-center border-r border-line sm:max-w-36">
      <button type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}
        aria-label={`Location: ${label}`} className="flex h-full min-w-0 items-center gap-1.5 rounded-l-xl px-2.5 text-sm font-medium text-ink hover:bg-canvas sm:px-3">
        <MapPin className="size-4 shrink-0 text-brand-700" aria-hidden />
        <span className="truncate">{label}</span>
        <ChevronDown className="size-3.5 shrink-0 text-muted" aria-hidden />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl bg-white text-ink shadow-[var(--shadow-pop)] ring-1 ring-line">
          <div className="border-b border-line p-3">
            <label htmlFor={searchId} className="mb-1.5 block text-xs font-semibold text-muted">Search by city or region</label>
            <input ref={search} id={searchId} type="search" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter a city or region" className="input h-10 text-sm" />
          </div>
          <div className="max-h-64 overflow-y-auto p-2">
            <button type="button" onClick={() => { onChange({ state: "", city: "" }); setOpen(false); setQuery(""); }}
              className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium hover:bg-brand-50">All Nigeria</button>
            {states.length > 0 && (
              <div className="mt-2">
                <p className="px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">Regions</p>
                {states.map((region) => (
                  <button key={region} type="button" onClick={() => chooseRegion(region)}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-brand-50">{region}</button>
                ))}
              </div>
            )}
            {cities.length > 0 && (
              <div className="mt-2">
                <p className="px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-muted">Cities</p>
                {cities.map(({ name, region }) => (
                  <button key={`${region}-${name}`} type="button" onClick={() => chooseCity(name, region)}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-brand-50">{name}, {region}</button>
                ))}
              </div>
            )}
            {query.trim() && states.length === 0 && cities.length === 0 && (
              <p className="px-3 py-3 text-sm text-muted">No matching city or region</p>
            )}
          </div>
        </div>
      )}
    </div>
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
