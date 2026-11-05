import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "About Goods.ng", alternates: { canonical: "/about" } };

export default function Page() {
  return (
    <ProsePage title="About Goods.ng" intro="Goods.ng is a Nigerian marketplace built on a simple idea: buying and selling online should feel as safe as buying in person.">
      <h2>Why we exist</h2>
      <p>Classified marketplaces made it easy to find things, but left buyers and sellers to manage trust on their own. Too many deals end with a fake alert, a missing item or a seller who never got paid. Goods.ng keeps the speed and choice of a classifieds site, and adds the protections a modern marketplace should have.</p>
      <h2>What makes us different</h2>
      <ul>
        <li><strong>Protected Checkout</strong> — buyer payments are held by a licensed escrow and payment partner and released to the seller only after delivery is confirmed.</li>
        <li><strong>Real negotiation</strong> — make offers and counteroffers in-app; the agreed price flows straight into checkout.</li>
        <li><strong>Direct contact when you want it</strong> — Premium sellers can be reached on WhatsApp or by phone, with clear warnings about what is and isn&apos;t protected.</li>
        <li><strong>Goods Flex</strong> — spread the cost of bigger purchases through our licensed lending partner.</li>
        <li><strong>Seller reputation</strong> — identity and business verification, verified-purchase reviews and transparent sales history.</li>
      </ul>
      <h2>Built for Nigeria</h2>
      <p>Goods.ng is designed for mobile first, works on slower connections and lower-end Android phones, and prices everything in Naira. We are starting in Nigeria, with an architecture ready for the rest of Africa.</p>
    </ProsePage>
  );
}
