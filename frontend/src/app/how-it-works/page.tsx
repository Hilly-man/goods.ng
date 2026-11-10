import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "How Goods.ng works",
  description:
    "Buy with Protected Checkout, Goods Flex or direct arrangement. See how payment, delivery PINs, payouts and disputes work.",
  path: "/how-it-works",
  image: ogImageUrl({
    eyebrow: "How it works",
    title: "Protected Checkout, Flex or direct",
    subtitle: "Choose how you pay and how delivery is arranged.",
    badge: "Guide",
  }),
  keywords: ["how Goods.ng works", "protected checkout steps", "buy safely in Nigeria", "marketplace guide"],
});

export default function Page() {
  return (
    <ProsePage title="How Goods.ng works" intro="Buy fully protected, pay in instalments, or arrange directly with the seller. Here's how each works.">
      <h2>Option A — Protected Checkout (recommended)</h2>
      <ol>
        <li>Verify your email and phone, then find an item and tap <strong>Buy with Protected Checkout</strong> (or make an offer first).</li>
        <li>Review the item, seller, delivery option and protection fee. Everything is shown before you pay.</li>
        <li>Pay by card or bank transfer through our licensed payment partner. Goods.ng confirms the payment directly with the provider — never from screenshots.</li>
        <li>Your funds are safeguarded by our escrow partner. The seller is notified and prepares your order.</li>
        <li>The seller dispatches and adds tracking details. You follow progress in <Link href="/orders">My orders</Link>. When the order is marked delivered you receive a <strong>6-digit delivery PIN</strong>.</li>
        <li>Inspect the item, share the PIN at handover and tap <strong>Confirm receipt</strong>. The seller cannot mark delivery without the PIN or a verified carrier event.</li>
        <li>Something wrong? Open a dispute before confirming, or within 24 hours after confirming. Funds stay safeguarded or on hold while our team reviews.</li>
      </ol>
      <p>If you don&apos;t confirm or raise a dispute within 3 days of delivery, funds are released automatically. Released seller earnings then clear for 24 hours before they can be withdrawn.</p>

      <h2>Option B — Direct contact or outside payment</h2>
      <p>Sellers can be reached on WhatsApp, by phone or in-app chat, and some listings let you arrange delivery directly with the seller. If you agree a deal and pay the seller outside Goods.ng, that transaction is <strong>not covered by escrow protection or our dispute process</strong>. You will always see a warning and must confirm it before proceeding. Integrated courier partners are coming soon; private couriers are arranged by the seller.</p>

      <h2>Option C — Goods Flex (pay small-small)</h2>
      <p>On eligible listings, choose Goods Flex to pay <strong>40% of the item price today</strong> and spread the remaining <strong>60% over 3 or 6 months</strong>. A financing charge of <strong>3% per month on the financed balance</strong> applies; the exact down payment, total and schedule are shown before you accept.</p>
      <ul>
        <li>Set up your Flex profile: verified phone and email, BVN, read-only bank connection and a guarantor who consents by SMS.</li>
        <li>Your credit limit comes from six months of bank transactions and your verification level, subject to the lending partner&apos;s approval.</li>
        <li>Only one Flex plan can run at a time. Pay instalments from the Goods Flex page before each due date.</li>
        <li>The seller opts in per listing and is paid the down-payment share after delivery, then the financed balance in monthly instalments as you pay.</li>
      </ul>
      <p>See <Link href="/flex/about">Goods Flex</Link> for the full terms and <Link href="/seller/flex-terms">seller terms</Link>.</p>

      <h2>Negotiating</h2>
      <p>On negotiable listings, tap <strong>Make an offer</strong>. The seller can accept, decline or counter, and you can counter back. Offers expire after 48 hours. Once accepted, you have 24 hours to check out at the agreed price. The public listing price never changes.</p>
    </ProsePage>
  );
}
