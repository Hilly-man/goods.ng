"use client";

import type { ProductCard as P } from "@/lib/types";
import { AutoCarousel } from "./auto-carousel";
import { ProductCard } from "./product-card";

/**
 * Featured listings carousel — always cards (ignores the grid/list preference).
 * 3 per view on phones, 4 on tablets, 5 on desktop; auto-advances to the left.
 */
export function FeaturedCarousel({ items }: { items: P[] }) {
  return (
    <AutoCarousel label="Featured listings"
      slideClassName="basis-[calc((100%-1rem)/3)] sm:basis-[calc((100%-2.25rem)/4)] lg:basis-[calc((100%-3rem)/5)]">
      {items.map((p, i) => <ProductCard key={p.id} p={p} eager={i < 5} compact />)}
    </AutoCarousel>
  );
}
