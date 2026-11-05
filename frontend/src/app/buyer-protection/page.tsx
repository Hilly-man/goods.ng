import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "Buyer & Seller Protection", alternates: { canonical: "/buyer-protection" } };

export default function Page() {
  return (
    <ProsePage title="Buyer & Seller Protection" intro="Protection applies to transactions paid through Goods.ng Protected Checkout.">
      <h2>How your money is protected</h2>
      <p>When you pay through Protected Checkout, the payment is collected and held by our licensed payment and escrow partner — not paid straight to the seller. Goods.ng instructs release only after delivery is confirmed, a dispute is resolved, or the confirmation window passes without a dispute.</p>
      <h2>Buyers are covered for</h2>
      <ul>
        <li>Item not received</li>
        <li>Item significantly different from the description</li>
        <li>Item damaged on arrival</li>
        <li>Wrong item sent</li>
        <li>Seller failing to fulfil the order</li>
        <li>Delivery disputes</li>
      </ul>
      <h2>Sellers are protected against</h2>
      <ul>
        <li>False buyer claims — disputes are decided on evidence such as waybills, tracking and photos</li>
        <li>Fake payment confirmations — orders are only marked paid after server-to-server verification with the payment provider</li>
        <li>Buyers refusing to confirm valid deliveries — sellers can open a dispute, and funds auto-release after the window</li>
        <li>Fraudulent refund requests — refunds after dispatch require review and approval by two separate Goods.ng staff</li>
      </ul>
      <h2>What is not covered</h2>
      <p>Deals arranged via WhatsApp, phone or in person and paid outside Goods.ng are not covered by escrow protection or our dispute resolution process.</p>
      <h2 id="safety">Safety tips</h2>
      <ul>
        <li>Never pay a seller directly to &quot;reserve&quot; an item.</li>
        <li>Ignore payment &quot;alerts&quot; or screenshots — check your order status on Goods.ng.</li>
        <li>Inspect items before confirming receipt.</li>
        <li>Meet in busy public places for pickups and bring someone with you.</li>
        <li>Report suspicious listings or messages using the Report button.</li>
      </ul>
      <p>Read the full <Link href="/refund-policy">Refund &amp; Dispute Policy</Link>.</p>
    </ProsePage>
  );
}
