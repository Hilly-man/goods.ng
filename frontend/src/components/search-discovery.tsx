"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpLeft, Clock3 } from "lucide-react";
import { clearHistory as clearInterestHistory } from "@/lib/interest";
import { clearRecentlyViewed, clearRecentSearches, getRecentlyViewed, getRecentSearches } from "@/lib/search-history";
import { errorMessage } from "@/lib/api";
import type { ProductCard as Product } from "@/lib/types";
import { ProductCard } from "./product-card";
import { AutoCarousel } from "./auto-carousel";
import { useToast } from "./ui";

export function SearchDiscovery() {
  const [searches, setSearches] = useState<string[]>([]);
  const [viewed, setViewed] = useState<Product[]>([]);
  const toast = useToast();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearches(getRecentSearches());
      setViewed(getRecentlyViewed());
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const clearSearches = () => {
    clearRecentSearches();
    setSearches([]);
  };
  const clearViewed = () => {
    clearRecentlyViewed();
    setViewed([]);
  };
  const clearAll = async () => {
    clearSearches();
    clearViewed();
    try {
      await clearInterestHistory();
    } catch (error) {
      toast(`History cleared on this device. ${errorMessage(error)}`, "bad");
    }
  };

  return (
    <div className="container-page min-h-[calc(100dvh-3.5rem)] space-y-5 py-4 pb-24">
      <section aria-labelledby="recent-searches">
        <div className="mb-2 flex items-center justify-between bg-brand-50 px-3 py-2">
          <h1 id="recent-searches" className="text-sm font-semibold text-muted">You searched</h1>
          {searches.length > 0 && (
            <button type="button" onClick={clearSearches} className="text-sm font-semibold text-brand-700 hover:underline">
              Clear
            </button>
          )}
        </div>
        {searches.length ? (
          <ul className="divide-y divide-line">
            {searches.map((query) => (
              <li key={query}>
                <Link href={`/search?q=${encodeURIComponent(query)}`}
                  className="flex items-center gap-3 px-3 py-3.5 text-ink hover:bg-brand-50">
                  <Clock3 className="size-4 shrink-0 text-muted" aria-hidden />
                  <span className="min-w-0 flex-1 truncate font-medium">{query}</span>
                  <ArrowUpLeft className="size-4 shrink-0 text-muted" aria-hidden />
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="px-3 py-3 text-sm text-muted">Your recent searches will appear here.</p>
        )}
      </section>

      <section aria-labelledby="recently-viewed">
        <div className="mb-3 flex items-center justify-between bg-brand-50 px-3 py-2">
          <h2 id="recently-viewed" className="text-sm font-semibold text-muted">Recently viewed</h2>
          {viewed.length > 0 && (
            <button type="button" onClick={clearViewed} className="text-sm font-semibold text-brand-700 hover:underline">
              Clear
            </button>
          )}
        </div>
        {viewed.length > 0 ? (
          <AutoCarousel label="Recently viewed listings" arrows={false} slideClassName="basis-[34%] sm:basis-[calc((100%-1.5rem)/3)]">
            {viewed.map((product) => <ProductCard key={product.id} p={product} compact placement="search" />)}
          </AutoCarousel>
        ) : (
          <p className="px-3 py-2 text-sm text-muted">Listings you open will appear here.</p>
        )}
      </section>

      <div className="grid grid-cols-2 gap-3 pt-1">
        <button type="button" onClick={() => void clearAll()}
          className="rounded-xl border border-brand-600 bg-white px-3 py-3 text-sm font-semibold text-brand-700 hover:bg-brand-50">
          Clear history
        </button>
        <Link href="/search?showAll=1"
          className="rounded-xl bg-accent-500 px-3 py-3 text-center text-sm font-bold text-ink hover:bg-accent-400">
          See all ads
        </Link>
      </div>
    </div>
  );
}
