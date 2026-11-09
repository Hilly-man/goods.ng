import type { MetadataRoute } from "next";
import { cacheLife } from "next/cache";
import { SITE_URL, absoluteMediaUrl } from "@/lib/seo";

const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const STATIC: { path: string; priority: number; changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"] }[] = [
  { path: "", priority: 1, changeFrequency: "daily" },
  { path: "/search", priority: 0.9, changeFrequency: "daily" },
  { path: "/sell", priority: 0.8, changeFrequency: "weekly" },
  { path: "/premium", priority: 0.7, changeFrequency: "weekly" },
  { path: "/flex", priority: 0.7, changeFrequency: "weekly" },
  { path: "/flex/about", priority: 0.7, changeFrequency: "weekly" },
  { path: "/how-it-works", priority: 0.6, changeFrequency: "monthly" },
  { path: "/buyer-protection", priority: 0.6, changeFrequency: "monthly" },
  { path: "/about", priority: 0.6, changeFrequency: "monthly" },
  { path: "/contact", priority: 0.5, changeFrequency: "monthly" },
  { path: "/faq", priority: 0.5, changeFrequency: "monthly" },
  { path: "/privacy", priority: 0.3, changeFrequency: "yearly" },
  { path: "/terms", priority: 0.3, changeFrequency: "yearly" },
  { path: "/refund-policy", priority: 0.4, changeFrequency: "yearly" },
];

type Cat = { slug: string; children: Cat[] };
type SitemapProduct = {
  slug: string;
  created_at: string;
  thumb_url: string | null;
  seller?: { slug: string } | null;
};

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  "use cache";
  cacheLife("hours");

  const out: MetadataRoute.Sitemap = STATIC.map((entry) => ({
    url: `${SITE_URL}${entry.path}`,
    changeFrequency: entry.changeFrequency,
    priority: entry.priority,
  }));

  try {
    const categories: Cat[] = await fetch(`${API}/api/v1/categories`).then((response) => response.json());
    const walk = (category: Cat) => {
      out.push({ url: `${SITE_URL}/c/${category.slug}`, changeFrequency: "daily", priority: 0.8 });
      category.children.forEach(walk);
    };
    categories.forEach(walk);

    const stores = new Set<string>();
    for (let page = 1; page <= 50; page++) {
      const result = await fetch(
        `${API}/api/v1/products?sort=newest&page_size=100&page=${page}`,
      ).then((response) => response.json());
      for (const product of (result.items ?? []) as SitemapProduct[]) {
        const image = absoluteMediaUrl(product.thumb_url);
        out.push({
          url: `${SITE_URL}/item/${product.slug}`,
          lastModified: product.created_at,
          changeFrequency: "weekly",
          priority: 0.7,
          ...(image ? { images: [image] } : {}),
        });
        if (product.seller?.slug) stores.add(product.seller.slug);
      }
      if (page >= (result.pages ?? 1)) break;
    }

    for (const slug of stores) {
      out.push({ url: `${SITE_URL}/store/${slug}`, changeFrequency: "weekly", priority: 0.6 });
    }
  } catch {
    // API unavailable (e.g. at build time): serve the static entries only.
  }

  return out;
}
