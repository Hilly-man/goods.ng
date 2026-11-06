import Link from "next/link";
import { SearchX } from "lucide-react";
import { serverGet } from "@/lib/server-api";
import type { Facets, Page, ProductCard } from "@/lib/types";
import { ProductCollection } from "./product-collection";
import { ViewToggle } from "./view-toggle";
import { Filters, ResultsToolbar } from "./filters";

export type SP = Record<string, string | string[] | undefined>;

const KEYS = ["q", "state", "city", "min_price", "max_price", "condition", "brand", "verified", "premium", "negotiable",
  "bnpl", "protected", "with_photos", "posted_within", "sort", "page"];

export function pickQuery(sp: SP, extra: Record<string, string> = {}) {
  const out: Record<string, string | string[] | undefined> = {};
  for (const k of KEYS) if (sp[k] !== undefined) out[k] = sp[k];
  return { ...out, ...extra, page_size: "24" };
}

export async function ListingResults({ sp, category, title }: { sp: SP; category?: string; title: string }) {
  const query = pickQuery(sp, category ? { category } : {});
  const facetQuery: Record<string, string | string[] | undefined> = { ...query };
  ["sort", "page", "page_size"].forEach((k) => delete facetQuery[k]);
  const [data, facets] = await Promise.all([
    serverGet<Page<ProductCard>>("/products", query),
    serverGet<Facets>("/products/facets", facetQuery),
  ]);
  const page = data.page;
  const href = (p: number) => {
    const s = new URLSearchParams();
    for (const [k, v] of Object.entries(sp)) {
      if (v === undefined || k === "page") continue;
      (Array.isArray(v) ? v : [v]).forEach((x) => s.append(k, x));
    }
    if (p > 1) s.set("page", String(p));
    const qs = s.toString();
    return qs ? `?${qs}` : "?";
  };
  return (
    <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
      <Filters facets={facets} />
      <div className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="rounded-full bg-white px-3 py-1.5 text-sm text-muted shadow-sm ring-1 ring-line/60">
            <span className="font-semibold text-ink">{data.total.toLocaleString("en-US")}</span> results for{" "}
            <span className="font-semibold text-ink">{title}</span>
          </p>
          <div className="flex items-center gap-2">
            <ResultsToolbar />
            <ViewToggle />
          </div>
        </div>
        {data.items.length === 0 ? (
          <div className="card flex flex-col items-center px-6 py-14 text-center">
            <SearchX className="size-10 text-muted" />
            <h2 className="mt-3 font-semibold">No ads match your search</h2>
            <p className="mt-1 text-sm text-muted">Try fewer filters, a different spelling, or search all of Nigeria.</p>
            <Link href="/search" className="mt-4 text-sm font-semibold text-brand-700 hover:underline">Clear all filters</Link>
          </div>
        ) : (
          <ProductCollection items={data.items} eagerCount={4} placement={category ? "category" : "search"} />
        )}
        {data.pages > 1 && (
          <nav aria-label="Pagination" className="mt-6 flex items-center justify-center gap-2">
            {page > 1 && <Link className="chip" href={href(page - 1)} rel="prev">← Previous</Link>}
            <span className="px-2 text-sm text-muted">Page {page} of {data.pages}</span>
            {page < data.pages && <Link className="chip" href={href(page + 1)} rel="next">Next →</Link>}
          </nav>
        )}
      </div>
    </div>
  );
}

export function ResultsSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-[300px_1fr]">
      <div className="card skeleton hidden h-[640px] lg:block" />
      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
        {Array.from({ length: 10 }).map((_, i) => <div key={i} className="card skeleton aspect-[3/4]" />)}
      </div>
    </div>
  );
}
