import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "Frequently asked questions", alternates: { canonical: "/faq" } };

const FAQ: [string, string][] = [
  ["Is it free to post an ad?", "Yes. Listing on Goods.ng is free. Sellers pay a small commission only when an item sells through Protected Checkout."],
  ["What is Protected Checkout?", "A way to pay through Goods.ng where your money is held by our licensed escrow partner until you confirm you received the item as described."],
  ["How much is the protection fee?", "1.5% of the item price, capped at ₦5,000. It's shown clearly before you pay."],
  ["When does the seller get paid?", "After you confirm receipt, or automatically 3 days after the seller marks the order delivered if no dispute is raised."],
  ["Can I negotiate the price?", "Yes, on listings marked negotiable. Make an offer and the seller can accept, decline or counter."],
  ["Am I protected if I pay a seller on WhatsApp?", "No. Only payments made through Goods.ng Protected Checkout are covered by escrow protection and our dispute process."],
  ["What is Goods Flex?", "Buy now and pay over 3 or 6 months through our licensed lending partner, subject to approval. You see all charges before accepting."],
  ["What does the Premium badge mean?", "The seller has a paid Premium subscription. It is different from the Verified badge, which means Goods.ng has checked their identity or business."],
  ["How do I become a verified seller?", "Verify your phone number, then submit your ID (or CAC documents for businesses) from your seller dashboard."],
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
