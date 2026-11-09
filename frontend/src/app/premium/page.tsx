import type { Metadata } from "next";
import { Suspense } from "react";
import { Check, Crown } from "lucide-react";
import { serverGet } from "@/lib/server-api";
import type { Plan } from "@/lib/types";
import { naira } from "@/lib/format";
import { SubscribeButton } from "./subscribe-button";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Premium Seller",
  description:
    "WhatsApp and call buttons, an enhanced storefront, featured listing credits, priority search visibility and advanced analytics.",
  path: "/premium",
  image: ogImageUrl({
    eyebrow: "Premium seller",
    title: "Grow faster with Premium",
    subtitle: "Contact buttons, enhanced storefront, featured listings and analytics.",
    badge: "Seller tools",
  }),
  keywords: ["Goods.ng Premium", "premium seller Nigeria", "seller analytics", "featured listings"],
});

async function Plans() {
  const plans = await serverGet<Plan[]>("/subscriptions/plans");
  return (
    <div className="grid gap-4 md:grid-cols-3">
      {plans.map((p, i) => (
        <div key={p.id} className={`card relative flex flex-col p-6 ${i === 1 ? "ring-2 ring-premium-500" : ""}`}>
          {i === 1 && <span className="absolute -top-3 left-6 rounded-full bg-premium-500 px-3 py-0.5 text-xs font-bold text-white">Best value</span>}
          <h2 className="text-lg font-bold">{p.name}</h2>
          <p className="mt-2"><span className="text-3xl font-extrabold">{naira(p.price)}</span> <span className="text-sm text-muted">/ {p.interval_days} days</span></p>
          <p className="mt-1 text-sm text-muted">{p.featured_listing_quota} featured listing credits</p>
          <ul className="mt-4 flex-1 space-y-2 text-sm">
            {p.features.map((f) => <li key={f} className="flex gap-2"><Check className="size-4 shrink-0 text-brand-700" />{f}</li>)}
          </ul>
          <div className="mt-6"><SubscribeButton plan={p.code} /></div>
        </div>
      ))}
    </div>
  );
}

export default function Page() {
  return (
    <div className="container-page py-8">
      <div className="mx-auto max-w-2xl text-center">
        <span className="inline-grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-amber-200 to-yellow-100 text-premium-600"><Crown className="size-7" /></span>
        <h1 className="mt-3 text-3xl font-extrabold tracking-tight">Become a Premium Seller</h1>
        <p className="mt-2 text-muted">Let buyers reach you instantly on WhatsApp and phone, stand out with a premium storefront and badge, and get more views with featured listings and priority placement.</p>
      </div>
      <div className="mt-8">
        <Suspense fallback={<div className="grid gap-4 md:grid-cols-3">{[0, 1, 2].map((i) => <div key={i} className="card skeleton h-96" />)}</div>}>
          <Plans />
        </Suspense>
      </div>
      <p className="mx-auto mt-6 max-w-2xl text-center text-xs text-muted">Premium status is a paid subscription and is separate from identity or business verification. Premium features activate only after your payment is verified with our payment provider. Premium listings that meet our quality bar may also be promoted in Top spots and advertised by Goods.ng on Google and Facebook/Instagram at no extra cost.</p>
    </div>
  );
}
