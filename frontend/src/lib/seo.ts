import type { Metadata } from "next";

const rawSite = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const SITE_URL = rawSite.replace(/\/+$/, "");
export const SITE_NAME = "Goods.ng";
export const SITE_LOCALE = "en_NG";
export const TWITTER_HANDLE = process.env.NEXT_PUBLIC_TWITTER_HANDLE?.trim() || undefined;
export const FACEBOOK_APP_ID = process.env.NEXT_PUBLIC_FACEBOOK_APP_ID?.trim() || undefined;

export const DEFAULT_DESCRIPTION =
  "Nigeria's marketplace for phones, cars, electronics, fashion, property and more. Chat and negotiate with sellers, pay with escrow-protected checkout, or spread payments with Goods Flex.";

export const DEFAULT_KEYWORDS = [
  "Goods.ng",
  "buy and sell in Nigeria",
  "Nigeria marketplace",
  "online classifieds Nigeria",
  "phones for sale Nigeria",
  "cars for sale Nigeria",
  "electronics Nigeria",
  "fashion Nigeria",
  "property Nigeria",
  "escrow protected checkout",
  "buy now pay later Nigeria",
  "Goods Flex",
];

export function absoluteUrl(path = "/"): string {
  if (/^https?:\/\//i.test(path)) return path;
  return `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

export function absoluteMediaUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (/^https?:\/\//i.test(url)) return url;
  if (url.startsWith("/")) return `${SITE_URL}${url}`;
  return undefined;
}

export function truncate(text: string, max = 160): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  const cut = clean.slice(0, max - 1);
  const lastSpace = cut.lastIndexOf(" ");
  return `${(lastSpace > max * 0.6 ? cut.slice(0, lastSpace) : cut).trimEnd()}…`;
}

export function ogImageUrl(input: {
  title: string;
  subtitle?: string;
  eyebrow?: string;
  price?: string;
  image?: string | null;
  badge?: string;
}): string {
  const params = new URLSearchParams();
  params.set("title", truncate(input.title, 100));
  if (input.subtitle) params.set("subtitle", truncate(input.subtitle, 150));
  if (input.eyebrow) params.set("eyebrow", truncate(input.eyebrow, 40));
  if (input.price) params.set("price", truncate(input.price, 24));
  if (input.badge) params.set("badge", truncate(input.badge, 32));
  if (input.image) params.set("image", input.image);
  return `${SITE_URL}/og?${params.toString()}`;
}

export const DEFAULT_OG_IMAGE = ogImageUrl({
  eyebrow: "Nigeria's trusted marketplace",
  title: "Buy. Sell. Trade with Confidence.",
  subtitle: "Chat and negotiate directly, pay with escrow-protected checkout, or spread the cost with Goods Flex.",
  badge: "Protected Checkout",
});

export type PageMetadataInput = {
  title: string;
  description: string;
  path: string;
  image?: string;
  imageAlt?: string;
  type?: "website" | "article";
  noindex?: boolean;
  keywords?: string[];
  absoluteTitle?: boolean;
  other?: Record<string, string>;
};

export function pageMetadata(input: PageMetadataInput): Metadata {
  const {
    title,
    description,
    path,
    image = DEFAULT_OG_IMAGE,
    imageAlt,
    type = "website",
    noindex = false,
    keywords = DEFAULT_KEYWORDS,
    absoluteTitle = false,
    other = {},
  } = input;

  const canonical = absoluteUrl(path);
  const meta: Record<string, string> = { ...other };
  if (FACEBOOK_APP_ID) meta["fb:app_id"] = FACEBOOK_APP_ID;

  const twitter: NonNullable<Metadata["twitter"]> = {
    card: "summary_large_image",
    title,
    description,
    images: [image],
  };
  if (TWITTER_HANDLE) {
    twitter.site = TWITTER_HANDLE;
    twitter.creator = TWITTER_HANDLE;
  }

  return {
    title: absoluteTitle ? { absolute: title } : title,
    description,
    keywords,
    authors: [{ name: SITE_NAME, url: SITE_URL }],
    creator: SITE_NAME,
    publisher: SITE_NAME,
    category: "Shopping",
    alternates: { canonical },
    robots: noindex
      ? { index: false, follow: true, googleBot: { index: false, follow: true } }
      : {
          index: true,
          follow: true,
          googleBot: {
            index: true,
            follow: true,
            "max-image-preview": "large",
            "max-snippet": -1,
            "max-video-preview": -1,
          },
        },
    openGraph: {
      type,
      url: canonical,
      siteName: SITE_NAME,
      locale: SITE_LOCALE,
      title,
      description,
      images: [{ url: image, width: 1200, height: 630, alt: imageAlt ?? title }],
    },
    twitter,
    other: Object.keys(meta).length ? meta : undefined,
  };
}
