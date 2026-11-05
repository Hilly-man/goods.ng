"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ArrowDownUp, ChevronDown, Clock, MapPin, Minus, Plus, SlidersHorizontal, X } from "lucide-react";
import { Suspense, useState } from "react";
import clsx from "clsx";
import { CONDITION_LABEL, nairaCompact } from "@/lib/format";
import type { Facets } from "@/lib/types";
import { Button } from "./ui";
import { useLocations } from "./state-city-select";

const FILTER_PARAMS = ["state", "city", "min_price", "max_price", "condition", "brand", "verified", "premium", "negotiable",
  "bnpl", "protected", "with_photos", "posted_within"];

const ads = (n: number) => `${n.toLocaleString("en-US")} ${n === 1 ? "ad" : "ads"}`;

function useUpdate() {
  const router = useRouter();
  const pathname = usePathname();
  const sp = useSearchParams();
  return (mut: (s: URLSearchParams) => void) => {
    const s = new URLSearchParams(sp.toString());
    mut(s);
    s.delete("page");
    const qs = s.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };
}

/** Card with a header and a −/+ toggle, like a classifieds filter panel. */
function Section({ title, sub, children, defaultOpen = true }: { title: string; sub?: string; children: React.ReactNode; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section className="card overflow-hidden">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 px-4 py-3.5 text-left">
        <span>
          <span className="block text-[15px] font-semibold">{title}</span>
          {sub && <span className="block text-xs text-muted">{sub}</span>}
        </span>
        {open ? <Minus className="size-4 text-muted" /> : <Plus className="size-4 text-muted" />}
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </section>
  );
}

function CheckRow({ label, count, checked, onChange, type = "checkbox", disabled }: {
  label: React.ReactNode; count?: number; checked: boolean; onChange: () => void; type?: "checkbox" | "radio"; disabled?: boolean;
}) {
  return (
    <label className={clsx("flex cursor-pointer items-center gap-3 py-1.5 text-[15px]", disabled && "cursor-default opacity-50")}>
      <input type={type} checked={checked} onChange={onChange} disabled={disabled} className="size-[18px] shrink-0 accent-brand-700" />
      <span>
        {label}
        {count !== undefined && <span className="text-brand-700"> • {ads(count)}</span>}
      </span>
    </label>
  );
}

function priceLabel(min: number | null, max: number | null) {
  if (min === null && max !== null) return `Under ${nairaCompact(String(max))}`;
  if (max === null && min !== null) return `More than ${nairaCompact(String(min))}`;
  return `${nairaCompact(String(min))} – ${nairaCompact(String(max))}`;
}

function CategoryCard({ facets }: { facets: Facets }) {
  const sp = useSearchParams();
  const [all, setAll] = useState(false);
  const { parent, current, items } = facets.categories;
  const keep = new URLSearchParams(sp.toString());
  ["page", "brand"].forEach((k) => keep.delete(k));
  const qs = keep.toString() ? `?${keep}` : "";
  const visible = all ? items : items.slice(0, 6);
  return (
    <section className="card overflow-hidden">
      <h2 className="bg-brand-700 px-4 py-3 text-[15px] font-bold text-white">Categories</h2>
      <div className="px-4 py-3">
        {parent && (
          <Link href={`/c/${parent.slug}${qs}`} className={clsx("block py-1 font-semibold hover:text-brand-700", current === parent.slug && "text-brand-800")}>
            {parent.name}
          </Link>
        )}
        <ul className={clsx(parent && "pl-4")}>
          {visible.map((c) => (
            <li key={c.slug}>
              <Link href={`/c/${c.slug}${qs}`} aria-current={current === c.slug ? "page" : undefined}
                className={clsx("flex items-baseline gap-1.5 py-1 text-[15px] hover:text-brand-700", current === c.slug && "font-semibold text-brand-800")}>
                <span>{c.name}</span>
                <span className="text-sm text-muted">| {c.count.toLocaleString("en-US")}</span>
              </Link>
            </li>
          ))}
        </ul>
        {items.length > 6 && (
          <button type="button" onClick={() => setAll(!all)} className={clsx("mt-1 text-sm font-medium text-brand-700 underline underline-offset-4", parent && "ml-4")}>
            {all ? "Show less" : `Show all ${items.length}`}
          </button>
        )}
        {current && <Link href={`/search${qs}`} className="mt-2 block text-xs text-muted hover:text-brand-700">← All categories</Link>}
      </div>
    </section>
  );
}

function FilterBody({ facets }: { facets: Facets }) {
  const sp = useSearchParams();
  const update = useUpdate();
  const loc = useLocations();
  const state = sp.get("state") ?? "";
  const city = sp.get("city") ?? "";
  const [min, setMin] = useState(sp.get("min_price") ?? "");
  const [max, setMax] = useState(sp.get("max_price") ?? "");
  const [allBrands, setAllBrands] = useState(false);
  const conditions = sp.getAll("condition");
  const brand = sp.get("brand") ?? "";
  const clean = (v: string) => v.replace(/[^\d]/g, "");
  const toggle = (k: string) => update((s) => (s.get(k) ? s.delete(k) : s.set(k, "true")));
  const applyPrice = (lo: string, hi: string) =>
    update((s) => {
      if (clean(lo)) s.set("min_price", clean(lo));
      else s.delete("min_price");
      if (clean(hi)) s.set("max_price", clean(hi));
      else s.delete("max_price");
    });
  const brands = allBrands ? facets.brands : facets.brands.slice(0, 8);
  const conds = (Object.keys(CONDITION_LABEL) as (keyof typeof CONDITION_LABEL)[]).filter(
    (c) => (facets.conditions[c] ?? 0) > 0 || conditions.includes(c),
  );
  const on = (k: string) => !!sp.get(k);
  const flagRow = (param: string, key: keyof Facets["flags"], label: string) => (
    <CheckRow key={param} label={label} count={facets.flags[key]} checked={on(param)}
      disabled={!on(param) && facets.flags[key] === 0} onChange={() => toggle(param)} />
  );

  return (
    <div className="space-y-3">
      <CategoryCard facets={facets} />

      <Section title="Location" sub={city ? `${city}, ${state}` : state || "All Nigeria"}>
        <div className="space-y-2">
          <div className="relative">
            <MapPin className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-brand-700" />
            <select aria-label="State" className="input appearance-none pl-9 pr-9" value={state}
              onChange={(e) => update((s) => { s.delete("city"); if (e.target.value) s.set("state", e.target.value); else s.delete("state"); })}>
              <option value="">All Nigeria</option>
              {(loc?.states ?? []).map((x) => <option key={x}>{x}</option>)}
            </select>
            <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          </div>
          {state && (
            <div className="relative">
              <select aria-label="City" className="input appearance-none pr-9" value={city}
                onChange={(e) => update((s) => (e.target.value ? s.set("city", e.target.value) : s.delete("city")))}>
                <option value="">All of {state}</option>
                {(loc?.cities[state] ?? []).map((c) => <option key={c}>{c}</option>)}
              </select>
              <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
            </div>
          )}
        </div>
      </Section>

      <Section title="Price, ₦">
        <form onSubmit={(e) => { e.preventDefault(); applyPrice(min, max); }}>
          <div className="flex items-center gap-2">
            <input className="input h-12" inputMode="numeric" placeholder="min" aria-label="Minimum price" value={min} onChange={(e) => setMin(e.target.value)} />
            <span className="text-muted">–</span>
            <input className="input h-12" inputMode="numeric" placeholder="max" aria-label="Maximum price" value={max} onChange={(e) => setMax(e.target.value)} />
          </div>
          {facets.price_ranges.length > 0 && (
            <div className="mt-3">
              {facets.price_ranges.map((r) => {
                const lo = r.min === null ? "" : String(r.min);
                const hi = r.max === null ? "" : String(r.max);
                return (
                  <CheckRow key={`${lo}-${hi}`} type="radio" label={priceLabel(r.min, r.max)} count={r.count}
                    checked={clean(min) === lo && clean(max) === hi}
                    onChange={() => { setMin(lo); setMax(hi); }} />
                );
              })}
            </div>
          )}
          <div className="mt-3 flex justify-between text-xs font-bold uppercase tracking-wide">
            <button type="button" className="text-muted hover:text-ink" onClick={() => { setMin(""); setMax(""); applyPrice("", ""); }}>Clear</button>
            <button type="submit" className="text-brand-700 hover:text-brand-800">Save</button>
          </div>
        </form>
      </Section>

      {conds.length > 0 && (
        <Section title="Condition">
          {conds.map((c) => (
            <CheckRow key={c} label={CONDITION_LABEL[c]} count={facets.conditions[c] ?? 0} checked={conditions.includes(c)}
              onChange={() => update((s) => {
                const cur = s.getAll("condition").filter((x) => x !== c);
                s.delete("condition");
                (conditions.includes(c) ? cur : [...cur, c]).forEach((x) => s.append("condition", x));
              })} />
          ))}
        </Section>
      )}

      {facets.brands.length > 0 && (
        <Section title="Brand">
          <CheckRow type="radio" label="Any brand" checked={!brand} onChange={() => update((s) => s.delete("brand"))} />
          {brands.map((b) => (
            <CheckRow key={b.name} type="radio" label={b.name} count={b.count} checked={brand.toLowerCase() === b.name.toLowerCase()}
              onChange={() => update((s) => s.set("brand", b.name))} />
          ))}
          {facets.brands.length > 8 && (
            <button type="button" onClick={() => setAllBrands(!allBrands)} className="mt-1 text-sm font-medium text-brand-700 underline underline-offset-4">
              {allBrands ? "Show less" : `Show all ${facets.brands.length}`}
            </button>
          )}
        </Section>
      )}

      <Section title="Verified sellers">
        {flagRow("verified", "verified_only", "Verified sellers")}
        {flagRow("premium", "premium_only", "Premium sellers")}
      </Section>

      <Section title="Deals & payment">
        {flagRow("protected", "protected", "Protected Checkout")}
        {flagRow("bnpl", "bnpl", "Goods Flex (pay small-small)")}
        {flagRow("negotiable", "negotiable", "Negotiable price")}
      </Section>

      <Section title="Photos">{flagRow("with_photos", "with_photos", "With photos")}</Section>

      {FILTER_PARAMS.some((k) => sp.get(k)) && (
        <button type="button" className="w-full rounded-lg border border-line bg-white py-2.5 text-sm font-semibold text-brand-700 hover:border-brand-600"
          onClick={() => update((s) => FILTER_PARAMS.forEach((k) => s.delete(k)))}>
          Clear all filters
        </button>
      )}
    </div>
  );
}

function FiltersInner({ facets }: { facets: Facets }) {
  const sp = useSearchParams();
  const [open, setOpen] = useState(false);
  const active = FILTER_PARAMS.filter((k) => sp.get(k)).length;
  // Re-mount the panel when the URL changes so local inputs (price boxes) reflect the applied filters.
  const k = sp.toString();
  return (
    <>
      <aside className="hidden h-fit lg:block" aria-label="Filters">
        <FilterBody key={k} facets={facets} />
      </aside>
      <div className="lg:hidden">
        <button onClick={() => setOpen(true)} className="chip w-full justify-center py-2.5 font-semibold">
          <SlidersHorizontal className="size-4" /> Filters {active > 0 && <span className="rounded-full bg-brand-700 px-1.5 text-xs text-white">{active}</span>}
        </button>
        {open && (
          <div className="fixed inset-0 z-50 flex flex-col bg-canvas" role="dialog" aria-modal="true" aria-label="Filters">
            <div className="flex items-center justify-between border-b border-line bg-white px-4 py-3">
              <h2 className="font-semibold">Filters</h2>
              <button onClick={() => setOpen(false)} aria-label="Close filters" className="rounded-full p-1.5 hover:bg-black/5"><X className="size-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto p-3"><FilterBody key={k} facets={facets} /></div>
            <div className="border-t border-line bg-white p-3"><Button block onClick={() => setOpen(false)}>Show {ads(facets.total)}</Button></div>
          </div>
        )}
      </div>
    </>
  );
}

export function Filters({ facets }: { facets: Facets }) {
  return (
    <Suspense fallback={<div className="card hidden h-96 lg:block" />}>
      <FiltersInner facets={facets} />
    </Suspense>
  );
}

function Pill({ icon, label, value, options, onChange }: {
  icon: React.ReactNode; label: string; value: string; options: [string, string][]; onChange: (v: string) => void;
}) {
  return (
    <label className="relative inline-flex h-10 items-center gap-2 rounded-lg border border-line bg-white pl-3 pr-8 text-sm font-medium shadow-sm hover:border-brand-600">
      {icon}
      <span aria-hidden>{options.find(([v]) => v === value)?.[1]}</span>
      <select aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} className="absolute inset-0 cursor-pointer opacity-0">
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 size-4 text-muted" />
    </label>
  );
}

function ToolbarInner() {
  const sp = useSearchParams();
  const update = useUpdate();
  return (
    <div className="flex items-center gap-2">
      <Pill icon={<ArrowDownUp className="size-4" />} label="Sort" value={sp.get("sort") ?? "relevance"}
        options={[["relevance", "Most relevant"], ["newest", "Newest first"], ["price_asc", "Lowest price"], ["price_desc", "Highest price"]]}
        onChange={(v) => update((s) => (v === "relevance" ? s.delete("sort") : s.set("sort", v)))} />
      <Pill icon={<Clock className="size-4" />} label="Posted" value={sp.get("posted_within") ?? ""}
        options={[["", "Any time"], ["1", "Last 24 hours"], ["7", "Last 7 days"], ["30", "Last 30 days"]]}
        onChange={(v) => update((s) => (v ? s.set("posted_within", v) : s.delete("posted_within")))} />
    </div>
  );
}

export function ResultsToolbar() {
  return (
    <Suspense fallback={<div className="h-10" />}>
      <ToolbarInner />
    </Suspense>
  );
}
