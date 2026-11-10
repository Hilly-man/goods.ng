import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Frequently asked questions",
  description:
    "Answers about Protected Checkout, fees, refunds, Goods Flex, verification, delivery and selling on Goods.ng.",
  path: "/faq",
  image: ogImageUrl({
    eyebrow: "Help centre",
    title: "Frequently asked questions",
    subtitle: "Protected Checkout, fees, refunds, Flex and verification.",
    badge: "Answers",
  }),
  keywords: ["Goods.ng FAQ", "Protected Checkout questions", "Goods Flex FAQ", "selling on Goods.ng"],
});

const FAQ: [string, string][] = [
  ["Is it free to post an ad?", "Yes. Listing on Goods.ng is free. Sellers pay a small commission only when an item sells through Protected Checkout."],
  ["What is Protected Checkout?", "A way to pay through Goods.ng where your money is held by our licensed escrow partner until you confirm you received the item as described."],
  ["Do I need a verified account to buy?", "Yes. You need a verified email address and phone number before checkout. It takes a minute from Account settings."],
  ["How much is the protection fee?", "1.5% of the item price, capped at ₦5,000. It's shown clearly before you pay."],
  ["When does the seller get paid?", "For normal Protected Checkout, after you confirm receipt (or automatically after the confirmation window). Released earnings then clear for 24 hours before withdrawal. Withdrawals are reviewed and paid to the seller's bank account; allow at least 24 hours for the transfer."],
  ["What is Goods Flex?", "Buy now, pay later: pay 40% today and spread the remaining 60% over 3 or 6 months. A financing charge of 3% per month applies to the financed balance. The exact down payment, charge, total and schedule are shown before you accept."],
  ["Do sellers get the full amount upfront with Goods Flex?", "No. The seller opts in per listing and receives the down-payment share after delivery, then the remaining 60% in monthly instalments as the buyer pays. This can take 3 to 6 months. Sellers receive 70% of the financing charge."],
  ["What if a Goods Flex buyer misses a payment?", "Goods.ng and the lending partner remind the buyer and pursue collection through the guarantor, but unpaid instalments are not released to the seller. Goods.ng does not guarantee the unpaid balance."],
  ["How is delivery confirmed?", "The seller cannot mark an order delivered without the buyer's 6-digit delivery PIN (or a verified carrier event). Share the PIN only when the item is handed over."],
  ["Can I arrange delivery with the seller myself?", "Yes. Sellers can offer 'arrange delivery with buyer'. You then agree delivery directly. Integrated courier partners (GIG, Fez, Shipbubble) are coming soon; private couriers are seller-arranged."],
  ["Am I protected if I pay a seller on WhatsApp or outside the app?", "No. Only payments made through Goods.ng Protected Checkout are covered by escrow protection and our dispute process. Outside transactions are between you and the seller."],
  ["Can I negotiate the price?", "Yes, on listings marked negotiable. Make an offer and the seller can accept, decline or counter."],
  ["What does the Premium badge mean?", "The seller has a paid Premium subscription. It is different from the Verified badge, which means Goods.ng has checked their identity or business."],
  ["How do I become a verified seller?", "Verify your email and phone, then submit your ID (or CAC documents for businesses) from your seller dashboard."],
  ["How do refunds work?", "Approved refunds go back to your original payment method through our payment partner. See the Refund & Dispute Policy for details."],
];

export default function Page() {
  return (
    <ProsePage title="Frequently asked questions">
      <div className="not-prose divide-y divide-line">
        {FAQ.map(([q, a]) => (
          <details key={q} className="group py-3">
            <summary className="cursor-pointer list-none font-semibold marker:hidden">
              <span className="flex items-center justify-between gap-4">{q}<span className="text-brand-700 transition group-open:rotate-45">+</span></span>
            </summary>
            <p className="mt-2 text-ink/80">{a}</p>
          </details>
        ))}
      </div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
        "@context": "https://schema.org", "@type": "FAQPage",
        mainEntity: FAQ.map(([q, a]) => ({ "@type": "Question", name: q, acceptedAnswer: { "@type": "Answer", text: a } })),
      }).replace(/</g, "\\u003c") }} />
    </ProsePage>
  );
}
