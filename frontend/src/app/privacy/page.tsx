import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Privacy Policy",
  description:
    "How Goods.ng collects, uses and protects personal data under the Nigeria Data Protection Act 2023, including bank data and guarantors.",
  path: "/privacy",
  image: ogImageUrl({
    eyebrow: "Legal",
    title: "Privacy Policy",
    subtitle: "How Goods.ng collects, uses and protects personal data.",
    badge: "NDPA 2023",
  }),
  keywords: ["Goods.ng privacy policy", "NDPA 2023", "data protection Nigeria", "marketplace privacy"],
});

export default function Page() {
  return (
    <ProsePage title="Privacy Policy" updated="5 November 2026">
      <p>This policy explains how Goods.ng collects and uses personal data, in line with the Nigeria Data Protection Act 2023.</p>
      <h2>What we collect</h2>
      <ul>
        <li>Account details: name, email, phone number, location.</li>
        <li>Seller verification documents (e.g. NIN, CAC). Identifiers are encrypted at rest and access by staff is logged.</li>
        <li>Listings, messages, offers, orders, reviews and delivery details.</li>
        <li>Payment references from our payment partners. We never store full card details.</li>
        <li>For Goods Flex: your BVN (encrypted at rest, only the last four digits shown), employment details you provide, six months of bank transaction data from your connected account, and your guarantor&apos;s name, phone and BVN (encrypted) with their consent record.</li>
        <li>Device and usage data for security and fraud prevention.</li>
      </ul>
      <h2>Bank data and Goods Flex</h2>
      <p>We access your bank transactions through a licensed open-banking provider, with read-only consent you give when you link the account. We use the data only to calculate your Goods Flex limit, assess affordability and prevent fraud. We do not move money from your account. You can withdraw consent or ask us to delete the connection by contacting privacy@goods.ng; we may keep records needed to meet legal and regulatory obligations.</p>
      <p>If you name a guarantor, we share your name and the amount being guaranteed with them so they can make an informed decision. We record their consent, IP address and time. A guarantor can decline without any consequence to them.</p>
      <h2>How we use it</h2>
      <ul>
        <li>To run the marketplace, process orders and resolve disputes.</li>
        <li>To verify identities and prevent fraud.</li>
        <li>To send notifications you can control in your settings.</li>
      </ul>
      <h2>Sharing</h2>
      <p>We share data only with service providers needed to run Goods.ng (payment, escrow, lending, SMS/email and hosting partners), with the other party to a transaction (e.g. your delivery address with the seller after payment), or where required by law. Goods Flex applications are shared with our lending partner only with your consent.</p>
      <h2 id="cookies">Cookies &amp; advertising</h2>
      <p><b>Necessary cookies</b> keep you signed in, protect your account (for example the security check on sign-in) and remember your choices. They are always on.</p>
      <p><b>Marketing cookies</b> are only used if you choose &quot;Accept all&quot; (or tick Marketing). They let Meta (Facebook/Instagram) and Google measure our ads — for example that someone who clicked an ad viewed an item, contacted a seller or bought it — and show you relevant Goods.ng listings on their platforms. When you buy with marketing cookies accepted, we may send Meta a purchase notice from our servers containing the order value, product IDs and a one-way-hashed (not readable) email and phone number, so the same purchase isn&apos;t double-counted.</p>
      <p>You can change your choice at any time with <b>Cookie settings</b> at the bottom of every page. We also record which site sent you to Goods.ng (for example a Google search or a Facebook post) to recommend relevant listings; you can clear this from &quot;Recommended for you&quot;.</p>
      <h2>Your rights</h2>
      <p>You can access, correct or delete your data, and object to certain processing, by contacting privacy@goods.ng. Some records (e.g. financial transactions) must be kept to meet legal obligations.</p>
      <h2>Security</h2>
      <p>We use encryption in transit and at rest for sensitive data, hashed passwords, access controls and audit logs.</p>
    </ProsePage>
  );
}
