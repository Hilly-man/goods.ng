import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "Terms & Conditions", alternates: { canonical: "/terms" } };

export default function Page() {
  return (
    <ProsePage title="Terms & Conditions" updated="5 November 2026">
      <h2>1. About these terms</h2>
      <p>These terms govern your use of Goods.ng (the &quot;Platform&quot;). By creating an account or using the Platform you agree to them. Goods.ng provides a marketplace that connects buyers and sellers; unless stated otherwise, Goods.ng is not the seller of items listed.</p>
      <h2>2. Accounts</h2>
      <ul>
        <li>You must be at least 18 years old and provide accurate information.</li>
        <li>You are responsible for keeping your login details secure.</li>
        <li>We may suspend accounts involved in fraud, abuse or breach of these terms.</li>
      </ul>
      <h2>3. Listings</h2>
      <p>Sellers must own or be authorised to sell listed items, describe them accurately and comply with Nigerian law. Prohibited items include counterfeit goods, weapons, drugs, stolen property and anything illegal to sell in Nigeria. We may remove listings at our discretion.</p>
      <h2>4. Two ways to transact</h2>
      <p><strong>Protected Checkout:</strong> payments are processed and held by our licensed payment and escrow partner and released in line with our Refund &amp; Dispute Policy. <strong>Direct contact:</strong> transactions arranged and paid outside the Platform are solely between buyer and seller and are not covered by escrow protection or dispute resolution.</p>
      <h2>5. Fees</h2>
      <p>Listing is free. Sellers pay a commission on completed Protected Checkout sales; buyers pay a protection fee shown at checkout. Premium Seller subscriptions and promotions are billed as displayed. Fees may change with notice.</p>
      <h2>6. Premium Seller</h2>
      <p>Premium status is a paid subscription giving additional features. It is separate from identity or business verification and is not an endorsement of a seller.</p>
      <p>Premium listings may be given higher placement on Goods.ng, shown in promoted (&quot;Top&quot;) positions, and advertised by Goods.ng on other platforms such as Google and Facebook/Instagram, using the listing&apos;s title, photos, price and description. Goods.ng decides where and how its own advertising runs and pays for it; this doesn&apos;t guarantee any number of views, enquiries or sales.</p>
      <h2>7. Goods Flex</h2>
      <p>Goods Flex financing is provided by a licensed lending partner under its own agreement. Goods.ng does not lend money or make credit decisions. Your limit is calculated from the bank transactions you choose to share and from the verification steps you complete; it is not a promise that the lending partner will approve any particular purchase. You may have only one Goods Flex plan running at a time, and a new plan is only available after the previous plan is fully paid or cancelled.</p>
      <h2>8. Guarantors</h2>
      <p>A guarantor is required before you can use Goods Flex. By naming a guarantor, you confirm you have their permission to share their name and phone number with us. Your guarantor will receive a link explaining the request and the maximum amount they may be asked to cover, and must consent before your limit is activated. A guarantor may decline or withdraw consent, in which case your Goods Flex limit is suspended until another guarantor consents. Guarantor obligations are governed by the lending partner&apos;s agreement and applicable law.</p>
      <h2>9. Liability</h2>
      <p>To the extent permitted by law, Goods.ng is not liable for transactions completed outside Protected Checkout or for the quality, safety or legality of items listed by sellers.</p>
      <h2>10. Governing law</h2>
      <p>These terms are governed by the laws of the Federal Republic of Nigeria.</p>
    </ProsePage>
  );
}
