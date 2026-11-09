import type { MetadataRoute } from "next";
import { SITE_NAME } from "@/lib/seo";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: `${SITE_NAME} — Buy. Sell. Trade with Confidence.`,
    short_name: SITE_NAME,
    description:
      "Nigeria's marketplace for phones, cars, electronics, fashion, property and more. Chat and negotiate, pay with Protected Checkout, or spread payments with Goods Flex.",
    start_url: "/",
    display: "standalone",
    background_color: "#F7FAF4",
    theme_color: "#18251D",
    orientation: "portrait",
    categories: ["shopping", "business", "lifestyle"],
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-192-maskable.png", sizes: "192x192", type: "image/png", purpose: "maskable" },
      { src: "/icon-512-maskable.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml" },
    ],
  };
}
