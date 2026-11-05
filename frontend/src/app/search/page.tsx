import type { Metadata } from "next";
import { Suspense } from "react";
import { ListingResults, ResultsSkeleton, type SP } from "@/components/listing-results";

export async function generateMetadata({ searchParams }: { searchParams: Promise<SP> }): Promise<Metadata> {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q : "";
  const where = typeof sp.state === "string" ? ` in ${sp.state}` : " in Nigeria";
  return {
    title: q ? `${q} for sale${where}` : `Buy & sell${where}`,
    alternates: { canonical: "/search" },
    robots: { index: !q || q.length < 60, follow: true },
  };
}

async function Results({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q : "";
  return (
    <>
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
