import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "How Goods.ng works", alternates: { canonical: "/how-it-works" } };

export default function Page() {
  return (
    <ProsePage title="How Goods.ng works" intro="Two ways to buy: Protected Checkout through Goods.ng, or direct contact with the seller. Here's how each works.">
      <h2>Option A — Protected Checkout (recommended)</h2>
      <ol>
        <li>Find an item and tap <strong>Buy with Protected Checkout</strong> (or make an offer first).</li>
        <li>Review the item, seller, delivery charge and protection fee. Everything is shown before you pay.</li>
        <li>Pay by card or bank transfer through our licensed payment partner. Goods.ng confirms the payment directly with the provider — never from screenshots.</li>
        <li>Your funds are safeguarded by our escrow partner. The seller is notified and prepares your order.</li>
        <li>The seller dispatches and adds tracking details. You follow progress in <Link href="/orders">My orders</Link>.</li>
        <li>When the item arrives, inspect it and tap <strong>Confirm receipt</strong>. Only then are funds released to the seller.</li>
        <li>Something wrong? Open a dispute before confirming and funds stay safeguarded while our team reviews.</li>
      </ol>
      <p>If you don&apos;t confirm or raise a dispute within 3 days of the seller marking delivery, funds are released automatically.</p>
      <h2>Option B — Direct contact</h2>
      <p>Premium sellers can be reached on WhatsApp or by phone, and anyone can chat in-app. If you agree a deal and pay the seller directly, that transaction happens outside Goods.ng and <strong>is not covered by escrow protection or our dispute process</strong>. You&apos;ll always see this warning before contacting a seller directly.</p>
      <h2>Negotiating</h2>
      <p>On negotiable listings, tap <strong>Make an offer</strong>. The seller can accept, decline or counter, and you can counter back. Offers expire after 48 hours. Once accepted, you have 24 hours to check out at the agreed price. The public listing price never changes.</p>
      <h2>Goods Flex</h2>
      <p>On eligible items, choose Goods Flex to pay a down payment now and the balance in monthly instalments. See <Link href="/flex/about">Goods Flex</Link>.</p>
    </ProsePage>
  );
}
