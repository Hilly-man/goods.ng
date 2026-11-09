import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: ["/", "/og"],
        disallow: [
          "/account",
          "/seller",
          "/admin",
          "/orders",
          "/messages",
          "/checkout",
          "/offers",
          "/saved",
          "/notifications",
          "/guarantor",
          "/flex/applications",
          "/accept-invite",
          "/login",
          "/register",
          "/forgot-password",
          "/dev",
          "/api/",
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
