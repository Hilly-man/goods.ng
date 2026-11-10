import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Terms & Conditions",
  description:
    "The rules for using the Goods.ng marketplace, including accounts, listings, payments, Goods Flex, payouts and disputes.",
  path: "/terms",
  image: ogImageUrl({
    eyebrow: "Legal",
    title: "Terms & Conditions",
    subtitle: "The rules for using the Goods.ng marketplace.",
    badge: "Legal",
  }),
  keywords: ["Goods.ng terms", "marketplace terms Nigeria", "user agreement", "seller terms"],
});

export default function Page() {
  return (
    <ProsePage title="Terms & Conditions" updated="10 November 2026">
      <h2>1. About these terms</h2>
      <p>These terms govern your use of Goods.ng (the &quot;Platform&quot;). By creating an account or using the Platform you agree to them. Goods.ng provides a marketplace that connects buyers and sellers; unless stated otherwise, Goods.ng is not the seller of items listed.</p>

      <h2>2. Accounts and verification</h2>
      <ul>
        <li>You must be at least 18 years old and provide accurate information.</li>
        <li>You are responsible for keeping your login details secure.</li>
        <li>We may require a verified email address and phone number before you can check out, sell or use Goods Flex.</li>
        <li>We may suspend accounts involved in fraud, abuse or breach of these terms.</li>
      </ul>

      <h2>3. Listings and delivery</h2>
      <p>Sellers must own or be authorised to sell listed items, describe them accurately and comply with Nigerian law. Prohibited items include counterfeit goods, weapons, drugs, stolen property and anything illegal to sell in Nigeria. We may remove listings at our discretion.</p>
      <p>Delivery may be by pickup, seller-arranged delivery, a private courier, or arranged directly between buyer and seller outside the Platform. Integrated courier partners are not live yet. Where a seller marks an order delivered, the buyer receives a delivery PIN and must share it at handover; the seller cannot mark delivery without it.</p>

      <h2>4. Ways to transact</h2>
      <p><strong>Protected Checkout:</strong> payments are processed and held by our licensed payment and escrow partner and released in line with our Refund &amp; Dispute Policy. <strong>Direct contact or outside payment:</strong> if you choose to arrange delivery or pay the seller outside the Platform, that transaction is solely between buyer and seller and is not covered by escrow protection or dispute resolution. You will always see this warning and must confirm it before proceeding.</p>

      <h2>5. Fees and payments</h2>
      <ul>
        <li>Listing is free.</li>
        <li>Sellers pay a commission on completed Protected Checkout sales; buyers pay a protection fee shown at checkout.</li>
        <li>Premium Seller subscriptions and promotions are billed as displayed.</li>
        <li>Goods Flex adds a financing charge of <strong>3% per month on the financed balance</strong>, shown with the total payable before acceptance.</li>
        <li>Fees may change with notice. Existing orders keep the fees shown when they were created.</li>
      </ul>

      <h2>6. Premium Seller</h2>
      <p>Premium status is a paid subscription giving additional features. It is separate from identity or business verification and is not an endorsement of a seller.</p>
      <p>Premium listings may be given higher placement on Goods.ng, shown in promoted (&quot;Top&quot;) positions, and advertised by Goods.ng on other platforms such as Google and Facebook/Instagram, using the listing&apos;s title, photos, price and description. Goods.ng decides where and how its own advertising runs and pays for it; this doesn&apos;t guarantee any number of views, enquiries or sales.</p>

      <h2>7. Goods Flex — buyer terms</h2>
      <p>Goods Flex lets an approved buyer pay <strong>40% of the item price today</strong> and spread the remaining <strong>60% over 3 or 6 months</strong>. A financing charge of <strong>3% per month on the financed balance</strong> applies. The exact down payment, charge, total payable and instalment schedule are shown before you accept, and the final credit decision is made by our licensed lending partner.</p>
      <p>Goods.ng does not lend money or make the credit decision. Your limit is calculated from the bank transactions you choose to share and the verification steps you complete; it is not a promise that any particular purchase will be approved. You may have only one Goods Flex plan running at a time, and a new plan is only available after the previous plan is fully paid or cancelled. Late or missed instalments may lead to collection action through the lending partner and may affect future eligibility.</p>

      <h2>8. Goods Flex — seller terms</h2>
      <p>Goods Flex is <strong>opt-in on each listing</strong>. By enabling it, the seller agrees to wait for the financed portion: after delivery the seller receives the down-payment share, and the remaining 60% is paid in monthly instalments as the buyer pays. This can take the full 3 or 6 months.</p>
      <p>The seller receives <strong>70% of the 3% monthly financing charge</strong>; Goods.ng keeps 30% for verification, collections, support and protection. Standard commission and protection fees still apply. If the buyer misses payments, the unpaid instalments are not released to the seller; Goods.ng will pursue collection but does not guarantee the unpaid balance. Sellers can turn Goods Flex off for future listings; accepted plans continue. Full seller terms are at <a href="/seller/flex-terms">/seller/flex-terms</a>.</p>

      <h2>9. Guarantors</h2>
      <p>A guarantor is required before you can use Goods Flex. By naming a guarantor, you confirm you have their permission to share their name and phone number with us. Your guarantor will receive a link explaining the request and the maximum amount they may be asked to cover, and must consent before your limit is activated. A guarantor may decline or withdraw consent, in which case your Goods Flex limit is suspended until another guarantor consents. Guarantor obligations are governed by the lending partner&apos;s agreement and applicable law.</p>

      <h2>10. Seller wallet and payouts</h2>
      <p>Released earnings are held in your seller wallet. Funds clear for <strong>24 hours</strong> after release so a buyer can raise a post-delivery complaint. Withdrawals are reviewed by an authorised administrator and are then sent to your verified bank account by our licensed payout partner; <strong>allow at least 24 hours after a withdrawal is initiated</strong> for the money to arrive. Failed transfers return the funds to your available balance. A buyer complaint or dispute may place the affected amount, and in some cases your payouts, on hold until resolved.</p>

      <h2>11. Liability</h2>
      <p>To the extent permitted by law, Goods.ng is not liable for transactions completed outside Protected Checkout or for the quality, safety or legality of items listed by sellers.</p>

      <h2>12. Governing law</h2>
      <p>These terms are governed by the laws of the Federal Republic of Nigeria.</p>
    </ProsePage>
  );
}
