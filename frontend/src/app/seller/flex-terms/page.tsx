import type { Metadata } from "next";
import Link from "next/link";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = {
  title: "Goods Flex — seller terms",
  description: "What it means to accept pay small-small (Goods Flex) on a listing.",
  robots: { index: false, follow: true },
};

export default function Page() {
  return (
    <ProsePage
      title="Goods Flex — seller terms"
      intro="Read this before you allow pay small-small on a listing."
    >
      <h2>What you are agreeing to</h2>
      <p>
        When you enable <strong>Goods Flex</strong> on a listing, buyers can pay 40% today and spread the remaining
        60% over <strong>3 or 6 months</strong>. You are choosing to wait for the financed part instead of receiving
        the full price at delivery. Only enable it on listings where you can wait.
      </p>

      <h2>How and when you get paid</h2>
      <ul>
        <li>After delivery, you receive the buyer&apos;s <strong>40% down-payment share</strong> (less the normal commission and protection fee).</li>
        <li>The remaining <strong>60% is paid to you in monthly instalments</strong> as the buyer pays. This can take the full 3 or 6 months.</li>
        <li>Each instalment includes your share of the financing charge. <strong>You receive 70% of the 3% monthly charge; Goods.ng keeps 30%</strong> for credit checks, collections, support and protection.</li>
        <li>Standard seller commission and the buyer protection fee still apply to the sale.</li>
      </ul>

      <h2>If the buyer misses a payment</h2>
      <p>
        Unpaid instalments are not released to you. Goods.ng will remind the buyer, work with the guarantor and pursue
        collection, but <strong>we do not guarantee the unpaid balance</strong>. You can turn Goods Flex off for future
        listings at any time; plans already accepted continue to their end.
      </p>

      <h2>Buyer checks still apply</h2>
      <p>
        Goods.ng still verifies the buyer&apos;s phone and email, runs the bank-statement affordability check, requires a
        consented guarantor and allows only one running plan at a time. A buyer must be approved before the order is funded.
      </p>

      <h2>Your choice, per listing</h2>
      <p>
        Goods Flex is opt-in on each listing. Untick it when creating or editing a listing to stop new buyers choosing
        instalments. Orders already placed are not affected.
      </p>

      <h2>Questions?</h2>
      <p>
        Contact <a href="mailto:support@goods.ng">support@goods.ng</a> before enabling Goods Flex if anything here is
        unclear. You must accept these terms in the listing form before Goods Flex can be enabled.
      </p>

      <p>
        <Link href="/seller/products/new">Back to add a listing</Link>
      </p>
    </ProsePage>
  );
}
