import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Refund & Dispute Policy",
  description:
    "Cancellations, disputes, refunds and timelines for orders paid through Goods.ng Protected Checkout and Goods Flex.",
  path: "/refund-policy",
  image: ogImageUrl({
    eyebrow: "Legal",
    title: "Refund & Dispute Policy",
    subtitle: "Cancellations, disputes, refunds and timelines.",
    badge: "Buyer protection",
  }),
  keywords: ["Goods.ng refund policy", "dispute policy Nigeria", "protected checkout refunds", "Goods Flex refunds"],
});

export default function Page() {
  return (
    <ProsePage title="Refund & Dispute Policy" updated="10 November 2026">
      <h2>1. Scope</h2>
      <p>This policy applies only to orders paid through Goods.ng Protected Checkout (including Goods Flex orders). Transactions completed outside Goods.ng, including deals where you arrange delivery and pay the seller directly, are not covered.</p>

      <h2>2. Cancellations before dispatch</h2>
      <ul>
        <li>Unpaid orders can be cancelled at any time and expire automatically after 60 minutes.</li>
        <li>Paid orders can be cancelled by the buyer until the seller accepts the order, with a full refund.</li>
        <li>If the seller declines or cannot fulfil a paid order, the buyer receives a full refund automatically.</li>
      </ul>

      <h2>3. Opening a dispute</h2>
      <p>Buyers may open a dispute from the time the seller accepts the order until they confirm receipt. Buyers may also raise a post-delivery complaint for <strong>24 hours after confirming receipt</strong>; that complaint places the affected seller payout on hold while it is reviewed. Sellers may open a dispute if a buyer refuses to confirm a delivered order. While a dispute or complaint is open, the affected funds remain safeguarded or on hold.</p>
      <p>Delivery is confirmed with a buyer-only PIN. The seller cannot mark an order delivered without the PIN or a verified carrier event. Integrated carrier partners are coming soon; private couriers remain seller-arranged.</p>

      <h2>4. Evidence and review</h2>
      <p>Both parties can add messages and photo evidence (for example waybills, tracking, unboxing photos). Goods.ng reviews the evidence and decides to release funds to the seller, refund the buyer, or close the dispute.</p>

      <h2>5. Refund approval and timing</h2>
      <p>Refunds resulting from a dispute must be approved by a second, independent Goods.ng administrator before they are processed. Refunds are returned to the original payment method through our payment partner; timing depends on the bank or card issuer (typically 3–10 working days).</p>

      <h2>6. Goods Flex orders</h2>
      <p>If a Goods Flex order is refunded, the down payment and any instalments already paid are refunded to you, and the remaining instalments are cancelled. The financing agreement is cancelled with our lending partner, subject to the partner&apos;s terms. Where the seller has already received funds, we may reverse or hold the seller&apos;s wallet balance, including any instalment payouts not yet released.</p>

      <h2>7. Seller wallet and payouts</h2>
      <p>Released seller earnings clear for 24 hours so a post-delivery complaint can be raised. Withdrawals are reviewed by an authorised administrator before our payout partner sends them; allow at least 24 hours after a withdrawal is initiated for the money to arrive. A dispute, complaint, refund or failed transfer can place funds on hold or return them to the available balance.</p>

      <h2>8. Fees</h2>
      <p>The buyer protection fee is refunded with full refunds. Partial refunds are handled case by case. Goods Flex financing charges on cancelled or refunded plans are reversed with the lending partner, subject to its terms.</p>

      <h2>9. Abuse</h2>
      <p>Accounts that make fraudulent claims or repeatedly abuse disputes may be suspended.</p>
    </ProsePage>
  );
}
