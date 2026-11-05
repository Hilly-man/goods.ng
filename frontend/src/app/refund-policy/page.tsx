import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "Refund & Dispute Policy", alternates: { canonical: "/refund-policy" } };

export default function Page() {
  return (
    <ProsePage title="Refund & Dispute Policy" updated="5 November 2026">
      <h2>1. Scope</h2>
      <p>This policy applies only to orders paid through Goods.ng Protected Checkout (including Goods Flex orders). Transactions completed outside Goods.ng are not covered.</p>
      <h2>2. Cancellations before dispatch</h2>
      <ul>
        <li>Unpaid orders can be cancelled at any time and expire automatically after 60 minutes.</li>
        <li>Paid orders can be cancelled by the buyer until the seller accepts the order, with a full refund.</li>
        <li>If the seller declines or cannot fulfil a paid order, the buyer receives a full refund automatically.</li>
      </ul>
      <h2>3. Opening a dispute</h2>
      <p>Buyers may open a dispute from the time the seller accepts the order until they confirm receipt, or within 3 days of the seller marking the order delivered. Sellers may open a dispute if a buyer refuses to confirm a delivered order. While a dispute is open, funds remain safeguarded and are not released.</p>
      <h2>4. Evidence and review</h2>
      <p>Both parties can add messages and photo evidence (e.g. waybills, tracking, unboxing photos). Goods.ng reviews the evidence and decides to release funds to the seller, refund the buyer, or close the dispute.</p>
      <h2>5. Refund approval</h2>
      <p>Refunds resulting from a dispute must be approved by a second, independent Goods.ng administrator before they are processed. Refunds are returned to the original payment method through our payment partner; timing depends on the bank or card issuer (typically 3–10 working days).</p>
      <h2>6. Goods Flex orders</h2>
      <p>If a Goods Flex order is refunded, the down payment is refunded to you and the financing agreement is cancelled with our lending partner, subject to the partner&apos;s terms.</p>
      <h2>7. Fees</h2>
      <p>The buyer protection fee is refunded with full refunds. Partial refunds are handled case by case.</p>
      <h2>8. Abuse</h2>
      <p>Accounts that make fraudulent claims or repeatedly abuse disputes may be suspended.</p>
    </ProsePage>
  );
}
