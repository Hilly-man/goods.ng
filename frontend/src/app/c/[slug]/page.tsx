import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ChevronRight } from "lucide-react";
import { NotFoundError, serverGet } from "@/lib/server-api";
import { ListingResults, ResultsSkeleton, type SP } from "@/components/listing-results";

type Cat = {
  id: string; name: string; slug: string; description: string | null;
  parent: { name: string; slug: string } | null; children: { name: string; slug: string }[];
};

async function getCategory(slug: string) {
  try {
    return await serverGet<Cat>(`/categories/${slug}`);
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const c = await getCategory(slug);
  return {
    title: `${c.name} for sale in Nigeria`,
    description: `Buy and sell ${c.name.toLowerCase()} on Goods.ng. Compare prices, chat with verified sellers and pay safely with Protected Checkout.`,
    alternates: { canonical: `/c/${c.slug}` },
  };
}

async function Content({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<SP> }) {
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const c = await getCategory(slug);
  return (
    <>
      <nav aria-label="Breadcrumb" className="mb-2 flex items-center gap-1 text-xs text-muted">
        <Link href="/" className="hover:text-brand-700">Home</Link>
        <ChevronRight className="size-3" />
        {c.parent && (
          <>
            <Link href={`/c/${c.parent.slug}`} className="hover:text-brand-700">{c.parent.name}</Link>
            <ChevronRight className="size-3" />
          </>
        )}
        <span className="text-ink">{c.name}</span>
      </nav>
      <h1 className="text-xl font-bold tracking-tight sm:text-3xl">
        {c.name} in {typeof sp.city === "string" ? `${sp.city}, ` : ""}{typeof sp.state === "string" ? sp.state : "Nigeria"}
      </h1>
      {c.children.length > 0 && (
        <div className="scrollbar-none -mx-3 mt-3 flex gap-2 overflow-x-auto px-3 pb-1 lg:hidden">
          {c.children.map((ch) => (
            <Link key={ch.slug} href={`/c/${ch.slug}`} className="chip shrink-0">{ch.name}</Link>
          ))}
        </div>
      )}
      <div className="mt-4">
        <ListingResults sp={sp} category={c.slug} title={`${c.name} in ${typeof sp.state === "string" ? sp.state : "Nigeria"}`} />
      </div>
    </>
  );
}

export default function CategoryPage(props: { params: Promise<{ slug: string }>; searchParams: Promise<SP> }) {
  return (
    <div className="container-page py-5">
      <Suspense fallback={<ResultsSkeleton />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}
