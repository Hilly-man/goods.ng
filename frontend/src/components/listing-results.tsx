import Link from "next/link";
import { SearchX } from "lucide-react";
import { serverGet } from "@/lib/server-api";
import type { Facets, Page, ProductCard } from "@/lib/types";
import { ProductCollection } from "./product-collection";
import { ViewToggle } from "./view-toggle";
import { Filters, ResultsToolbar } from "./filters";

export type SP = Record<string, string | string[] | undefined>;

const KEYS = ["q", "state", "city", "min_price", "max_price", "condition", "brand", "verified", "premium", "negotiable",
  "bnpl", "protected", "with_photos", "posted_within", "sort"];

// Search and category pages intentionally show every matching listing (no pagination). The API caps
// page_size at 100, so fetch the remaining pages in parallel and de-duplicate blended sponsored ads.
const MAX_PAGES = 50;

export function pickQuery(sp: SP, extra: Record<string, string> = {}) {
  const out: Record<string, string | string[] | undefined> = {};
  for (const k of KEYS) if (sp[k] !== undefined) out[k] = sp[k];
  return { ...out, ...extra, page_size: "100" };
}

async function allProducts(query: Record<string, string | string[] | undefined>): Promise<Page<ProductCard>> {
  const first = await serverGet<Page<ProductCard>>("/products", query);
  if (first.pages <= 1) return first;
  const totalPages = Math.min(first.pages, MAX_PAGES);
  const rest = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, i) =>
      serverGet<Page<ProductCard>>("/products", { ...query, page: String(i + 2) })),
  );
  const seen = new Set<string>();
  const items = [first.items, ...rest.map((p) => p.items)].flat().filter((p) => {
    if (seen.has(p.id)) return false;
    seen.add(p.id);
    return true;
  });
  return { ...first, items, pages: 1 };
}

export async function ListingResults({ sp, category, title }: { sp: SP; category?: string; title: string }) {
  const query = pickQuery(sp, category ? { category } : {});
  const facetQuery: Record<string, string | string[] | undefined> = { ...query };
  ["sort", "page", "page_size"].forEach((k) => delete facetQuery[k]);
  const [data, facets] = await Promise.all([
    allProducts(query),
    serverGet<Facets>("/products/facets", facetQuery),
  ]);
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
