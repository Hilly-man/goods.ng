import type { Metadata } from "next";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Goods Flex — Buy now, pay later",
  description:
    "Build a Goods Flex credit profile, connect your bank securely, add a guarantor and pay for eligible purchases over 3 or 6 months.",
  path: "/flex",
  image: ogImageUrl({
    eyebrow: "Goods Flex",
    title: "Buy now, pay over 3 or 6 months",
    subtitle: "A transparent affordability check, a mandatory guarantor and clear instalments.",
    badge: "Instalments",
  }),
  keywords: ["Goods Flex", "buy now pay later Nigeria", "instalment payment Nigeria", "BNPL Nigeria", "credit profile Nigeria"],
});

export default function FlexLayout({ children }: { children: React.ReactNode }) {
  return children;
}
