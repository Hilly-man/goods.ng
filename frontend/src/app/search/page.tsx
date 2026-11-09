import type { Metadata } from "next";
import { Suspense } from "react";
import { DEFAULT_DESCRIPTION, ogImageUrl, pageMetadata } from "@/lib/seo";
import { ListingResults, ResultsSkeleton, type SP } from "@/components/listing-results";
import { TrackSignal } from "@/components/recommended";

export async function generateMetadata({ searchParams }: { searchParams: Promise<SP> }): Promise<Metadata> {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.trim() : "";
  const where = typeof sp.state === "string" ? ` in ${sp.state}` : " in Nigeria";
  const hasFilters = Object.keys(sp).some((key) => {
    const value = sp[key];
    return key !== "page" && value !== undefined && value !== "";
  });
  return pageMetadata({
    title: q ? `${q} for sale${where}` : `Buy & sell${where}`,
    description: q
      ? `Find ${q}${where} on Goods.ng. Compare prices, chat with verified sellers and pay safely with Protected Checkout.`
      : DEFAULT_DESCRIPTION,
    path: "/search",
    image: ogImageUrl({
      eyebrow: "Search",
      title: q ? `${q}${where}` : "All ads in Nigeria",
      subtitle: "Compare prices, chat with verified sellers and pay safely with Protected Checkout.",
      badge: "Goods.ng",
    }),
    noindex: hasFilters,
    keywords: q
      ? [q, `${q}${where}`, `buy ${q} in Nigeria`, `used ${q} in Nigeria`, "Goods.ng"]
      : undefined,
  });
}

async function Results({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q : "";
  return (
    <>
      {q && <TrackSignal kind="search" query={q} category_slug={typeof sp.category === "string" ? sp.category : undefined} />}
      <h1 className="mb-4 text-xl font-bold tracking-tight sm:text-2xl">{q ? `Results for “${q}”` : "All ads"}</h1>
      <ListingResults sp={sp} title={`${q ? `“${q}”` : "all ads"} in ${typeof sp.state === "string" ? sp.state : "Nigeria"}`} />
    </>
  );
}

export default function SearchPage({ searchParams }: { searchParams: Promise<SP> }) {
  return (
    <div className="container-page py-5">
      <Suspense fallback={<ResultsSkeleton />}>
        <Results searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
