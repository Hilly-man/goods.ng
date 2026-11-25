import type { Metadata } from "next";
import { byListings } from "@/lib/format";
import { TrackSignal } from "@/components/recommended";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ChevronRight } from "lucide-react";
import { NotFoundError, serverGet } from "@/lib/server-api";
import { SITE_URL, ogImageUrl, pageMetadata, truncate } from "@/lib/seo";
import { ListingResults, ResultsSkeleton, type SP } from "@/components/listing-results";
import { CategoryIcon } from "@/components/icons";

type Cat = {
  id: string; name: string; slug: string; description: string | null;
  parent: { name: string; slug: string } | null;
  children: { name: string; slug: string; image_url: string; icon: string | null; listing_count: number }[];
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
  const description = c.description
    ? truncate(c.description, 155)
    : `Buy and sell ${c.name.toLowerCase()} on Goods.ng. Compare prices, chat with verified sellers and pay safely with Protected Checkout.`;
  return pageMetadata({
    title: `${c.name} for sale in Nigeria`,
    description,
    path: `/c/${c.slug}`,
    image: ogImageUrl({
      eyebrow: c.parent?.name ?? "Category",
      title: c.name,
      subtitle: "Compare prices, chat with verified sellers and pay safely with Protected Checkout.",
      badge: "Shop safely",
    }),
    keywords: [
      c.name,
      `${c.name} Nigeria`,
      `buy ${c.name} in Nigeria`,
      `sell ${c.name} in Nigeria`,
      ...(c.parent ? [c.parent.name] : []),
      "Goods.ng",
    ],
  });
}

function CategoryJsonLd({ c }: { c: Cat }) {
  const url = `${SITE_URL}/c/${c.slug}`;
  const description = c.description ?? `Buy and sell ${c.name.toLowerCase()} on Goods.ng.`;
  const crumbs = [
    { name: "Home", item: SITE_URL },
    ...(c.parent ? [{ name: c.parent.name, item: `${SITE_URL}/c/${c.parent.slug}` }] : []),
    { name: c.name, item: url },
  ];
  const data = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${c.name} for sale in Nigeria`,
    description,
    url,
    isPartOf: { "@type": "WebSite", name: "Goods.ng", url: SITE_URL },
    breadcrumb: {
      "@type": "BreadcrumbList",
      itemListElement: crumbs.map((crumb, index) => ({
        "@type": "ListItem",
        position: index + 1,
        name: crumb.name,
        item: crumb.item,
      })),
    },
  };
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}

async function Content({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<SP> }) {
  const [{ slug }, sp] = await Promise.all([params, searchParams]);
  const c = await getCategory(slug);
  return (
    <>
      <CategoryJsonLd c={c} />
      <TrackSignal kind="view" category_slug={c.slug} query={typeof sp.q === "string" ? sp.q : undefined} />
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
        <nav aria-label="Subcategories" className="scrollbar-none -mx-3 mt-3 overflow-x-auto px-3 pb-1 lg:hidden">
          <ul className="flex gap-3">
            {byListings(c.children).map((ch) => (
              <li key={ch.slug} className="w-[76px] shrink-0">
                <Link href={`/c/${ch.slug}`} className="flex flex-col items-center gap-1.5 rounded-xl p-1 text-center">
                  <span className="grid size-16 place-items-center overflow-hidden rounded-2xl bg-[#EEF0FF] p-1.5">
                    {ch.image_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={ch.image_url} alt="" loading="lazy" className="size-full rounded-[10px] bg-white object-cover" />
                    ) : (
                      <CategoryIcon name={ch.icon} className="size-6 text-brand-700" />
                    )}
                  </span>
                  <span className="line-clamp-2 w-full text-[11.5px] font-medium leading-tight">{ch.name}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
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
