import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Goods Flex — Buy now, pay later",
  description:
    "Buy what you need now and spread the cost over 3 or 6 months with Goods Flex. Affordability checks, a mandatory guarantor and clear terms.",
  path: "/flex/about",
  image: ogImageUrl({
    eyebrow: "Goods Flex",
    title: "Buy now, pay over 3 or 6 months",
    subtitle: "Affordability checks, a mandatory guarantor and clear terms.",
    badge: "Instalments",
  }),
  keywords: ["Goods Flex", "buy now pay later Nigeria", "instalment payment Nigeria", "BNPL Nigeria"],
});

export default function Page() {
  return (
    <ProsePage title="Goods Flex" intro="Buy what you need now and spread the cost over 3 or 6 months.">
      <h2>How it works</h2>
      <ol>
        <li>Set up your Goods Flex profile: verify your phone, BVN, connect your bank account (read-only) and add a guarantor who consents by SMS.</li>
        <li>We analyse six months of transactions — salary or business inflows, existing loan repayments, failed debits and betting — to calculate a credit limit you can comfortably afford.</li>
        <li>Look for the <strong>Goods Flex</strong> option on eligible listings up to your limit, then apply.</li>
        <li>Our licensed lending partner makes the final credit decision and shows you the exact down payment, financing charge and instalment schedule.</li>
        <li>Accept the terms and pay the down payment. Your order is then fully funded and protected by escrow like any Protected Checkout order.</li>
        <li>Pay your instalments from the Goods Flex page. We&apos;ll remind you before each due date.</li>
      </ol>
      <h2>Guarantor required</h2>
      <p>A guarantor is <strong>required</strong> before you can use Goods Flex — it is not optional. Your guarantor must be someone other than you, verify their BVN against their name, and confirm by SMS link. Workplace verification is optional and raises your limit.</p>
      <h2>One plan at a time</h2>
      <p>You can only have <strong>one Goods Flex plan running at a time</strong>. Once every instalment on your current plan is paid, you can start another. This keeps repayments manageable and protects your credit standing. An unpaid offer expires after 24 hours and frees the slot automatically.</p>
      <h2>Your credit limit</h2>
      <p>Your limit starts with your bank statement and rises as you verify more about yourself: workplace verification and a consented guarantor unlock higher caps. Repaying your first plan on time also increases your limit. All limits, caps and the factors used are shown on your Goods Flex page — there are no hidden criteria.</p>
      <h2>Example</h2>
      <p>For a ₦1,500,000 item, a plan might be a ₦450,000 down payment, with the ₦1,050,000 balance plus financing charges paid over 3 months. <strong>This is only an illustration</strong> — your actual charges and schedule are set by the lending partner and always shown before you accept.</p>
      <h2>Borrow responsibly</h2>
      <ul>
        <li>Only commit to instalments you can comfortably afford.</li>
        <li>Missed payments may attract charges from the lender and affect future eligibility.</li>
        <li>Goods.ng does not lend money or make credit decisions.</li>
      </ul>
    </ProsePage>
  );
}
