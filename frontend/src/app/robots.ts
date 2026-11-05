import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: "*", allow: "/", disallow: ["/account", "/seller", "/admin", "/orders", "/messages", "/checkout", "/offers", "/flex/applications", "/dev", "/api/"] }],
    sitemap: `${SITE}/sitemap.xml`,
  };
}
