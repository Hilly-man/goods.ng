import type { MetadataRoute } from "next";
import { cacheLife } from "next/cache";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
const API = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
const STATIC = ["", "/about", "/how-it-works", "/buyer-protection", "/sell", "/premium", "/contact", "/faq", "/privacy", "/terms", "/refund-policy", "/flex/about", "/search"];

type Cat = { slug: string; children: Cat[] };

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  "use cache";
  cacheLife("hours");
  const out: MetadataRoute.Sitemap = STATIC.map((p) => ({ url: `${SITE}${p}`, changeFrequency: "weekly", priority: p === "" ? 1 : 0.5 }));
  try {
    const cats: Cat[] = await fetch(`${API}/api/v1/categories`).then((r) => r.json());
    const walk = (c: Cat) => {
      out.push({ url: `${SITE}/c/${c.slug}`, changeFrequency: "daily", priority: 0.8 });
      c.children.forEach(walk);
    };
    cats.forEach(walk);
    for (let page = 1; page <= 20; page++) {
      const r = await fetch(`${API}/api/v1/products?sort=newest&page_size=100&page=${page}`).then((x) => x.json());
      for (const p of r.items as { slug: string; created_at: string }[]) {
        out.push({ url: `${SITE}/item/${p.slug}`, lastModified: p.created_at, changeFrequency: "weekly", priority: 0.7 });
      }
      if (page >= r.pages) break;
    }
  } catch {
    // API unavailable (e.g. at build time): serve the static entries only.
  }
  return out;
}
