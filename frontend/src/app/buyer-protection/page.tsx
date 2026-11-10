import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Buyer & Seller Protection",
  description:
    "How Goods.ng Protected Checkout safeguards your money until delivery, how delivery PINs and disputes work, and what is covered.",
  path: "/buyer-protection",
  image: ogImageUrl({
    eyebrow: "Buyer protection",
    title: "Your money is safeguarded until delivery",
    subtitle: "Protected Checkout with disputes, evidence and refunds.",
    badge: "Shop safely",
  }),
  keywords: ["buyer protection Nigeria", "escrow protection", "safe online shopping Nigeria", "Goods.ng Protected Checkout"],
});

export default function Page() {
  return (
    <ProsePage title="Buyer & Seller Protection" intro="Protection applies to transactions paid through Goods.ng Protected Checkout, including Goods Flex.">
      <h2>How your money is protected</h2>
      <p>When you pay through Protected Checkout, the payment is collected and held by our licensed payment and escrow partner — not paid straight to the seller. Goods.ng instructs release only after delivery is confirmed with your delivery PIN, a dispute is resolved, or the confirmation window passes without a dispute.</p>
      <h2>Buyers are covered for</h2>
      <ul>
        <li>Item not received</li>
        <li>Item significantly different from the description</li>
        <li>Item damaged on arrival</li>
        <li>Wrong item sent</li>
        <li>Seller failing to fulfil the order</li>
        <li>Delivery disputes</li>
        <li>Goods Flex orders, on the same basis — your instalment plan is protected by the same escrow flow</li>
      </ul>
      <h2>Sellers are protected against</h2>
      <ul>
        <li>False buyer claims — disputes are decided on evidence such as waybills, tracking, photos and the delivery PIN</li>
        <li>Fake payment confirmations — orders are only marked paid after server-to-server verification with the payment provider</li>
        <li>Buyers refusing to confirm valid deliveries — sellers can open a dispute, and funds auto-release after the window</li>
        <li>Fraudulent refund requests — refunds after dispatch require review and approval by two separate Goods.ng staff</li>
      </ul>
      <h2>Goods Flex sellers</h2>
      <p>Goods Flex is opt-in per listing. The seller receives the down-payment share after delivery, then the remaining 60% in monthly instalments as the buyer pays. If the buyer defaults, unpaid instalments are not released to the seller; Goods.ng pursues collection but does not guarantee the unpaid balance. Interests and terms are shown in the <Link href="/seller/flex-terms">seller terms</Link>.</p>
      <h2>What is not covered</h2>
      <p>Deals arranged via WhatsApp, phone or in person and paid outside Goods.ng are not covered by escrow protection or our dispute resolution process. Arranging delivery directly with a seller is allowed, but payment outside the app is not protected. Integrated courier partners are coming soon.</p>
      <h2 id="safety">Safety tips</h2>
      <ul>
        <li>Never pay a seller directly to &quot;reserve&quot; an item.</li>
        <li>Ignore payment &quot;alerts&quot; or screenshots — check your order status on Goods.ng.</li>
        <li>Inspect items before sharing your delivery PIN or confirming receipt.</li>
        <li>Meet in busy public places for pickups and bring someone with you.</li>
        <li>Report suspicious listings or messages using the Report button.</li>
      </ul>
      <p>Read the full <Link href="/refund-policy">Refund &amp; Dispute Policy</Link>.</p>
    </ProsePage>
  );
}
