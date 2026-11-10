import type { Metadata } from "next";
import { ProsePage } from "@/components/prose";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Privacy Policy",
  description:
    "How Goods.ng collects, uses and protects personal data under the Nigeria Data Protection Act 2023, including bank data, guarantors, payouts and analytics.",
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
    <ProsePage title="Privacy Policy" updated="10 November 2026">
      <p>This policy explains how Goods.ng collects and uses personal data, in line with the Nigeria Data Protection Act 2023.</p>

      <h2>What we collect</h2>
      <ul>
        <li>Account details: name, email, phone number, location, and whether your email and phone are verified.</li>
        <li>Seller verification documents (e.g. NIN, CAC). Identifiers are encrypted at rest and staff access is logged.</li>
        <li>Listings, messages, offers, orders, delivery addresses, delivery PINs, evidence photos, reviews and dispute records.</li>
        <li>Payment references from our payment partners. We never store full card details.</li>
        <li>Seller payout details: bank name, account name, account number (encrypted, only the last four digits shown) and payout history.</li>
        <li>For Goods Flex: your BVN (encrypted at rest, only the last four digits shown), employment details, six months of bank transaction data from your connected account, credit decision and repayment history, and your guarantor&apos;s name, phone and BVN (encrypted) with their consent record.</li>
        <li>Device and usage data for security and fraud prevention, plus anonymous traffic analytics described below.</li>
      </ul>

      <h2>Bank data and Goods Flex</h2>
      <p>We access your bank transactions through a licensed open-banking provider, with read-only consent you give when you link the account. We use the data only to calculate your Goods Flex limit, assess affordability and prevent fraud. We do not move money from your account. You can withdraw consent or ask us to delete the connection by contacting privacy@goods.ng; we may keep records needed to meet legal and regulatory obligations.</p>
      <p>If you name a guarantor, we share your name and the amount being guaranteed with them so they can make an informed decision. We record their consent, IP address and time. A guarantor can decline without any consequence to them.</p>
      <p>If you sell with Goods Flex enabled, you agree to receive the financed portion in monthly instalments. We keep the instalment schedule, payout records and any default or collection notes connected to that agreement.</p>

      <h2>How we use it</h2>
      <ul>
        <li>To run the marketplace, process orders, payouts and disputes.</li>
        <li>To verify identities, assess affordability and prevent fraud.</li>
        <li>To send verification codes and notifications you can control in your settings.</li>
        <li>To understand aggregate site usage so we can improve the marketplace.</li>
        <li>To meet legal, tax, accounting and regulatory obligations.</li>
      </ul>

      <h2>Sharing</h2>
      <p>We share data only with service providers needed to run Goods.ng — payment, escrow, lending, payout, open-banking, SMS/email and hosting providers — with the other party to a transaction (for example your delivery details with the seller after payment), or where required by law. Goods Flex applications are shared with our lending partner as part of the credit decision. Payout details are shared with our payout partner only to send your withdrawal.</p>

      <h2 id="cookies">Cookies, analytics &amp; advertising</h2>
      <p><b>Necessary cookies</b> keep you signed in, protect your account (for example the security check on sign-in and CSRF protection) and remember your choices. They are always on.</p>
      <p><b>First-party traffic analytics</b> uses a random identifier already stored in your browser and records the pages you visit, the referring page and the time. It does <b>not</b> store your IP address, and we do not use it to track you across other websites. It powers aggregate visitor and live-user counts in our admin console. We keep these records for up to 400 days. Our site respects Global Privacy Control and Do Not Track for these pings.</p>
      <p><b>Marketing cookies</b> are only used if you choose &quot;Accept all&quot; (or tick Marketing). They let Meta (Facebook/Instagram) and Google measure our ads — for example that someone who clicked an ad viewed an item, contacted a seller or bought it — and show you relevant Goods.ng listings on their platforms. When you buy with marketing cookies accepted, we may send Meta a purchase notice from our servers containing the order value, product IDs and a one-way-hashed (not readable) email and phone number, so the same purchase isn&apos;t double-counted.</p>
      <p>You can change your choice at any time with <b>Cookie settings</b> at the bottom of every page. We also record which site sent you to Goods.ng (for example a Google search or a Facebook post) to recommend relevant listings; you can clear this from &quot;Recommended for you&quot;.</p>

      <h2>Retention</h2>
      <p>We keep account, order, payment and payout records for as long as your account is active and afterwards where law requires (for example tax and financial records). Anonymous traffic records are deleted after about 400 days. Verification and Good Flex records may be kept for the periods required by our regulators and lending partner.</p>

      <h2>Your rights</h2>
      <p>You can access, correct or delete your data, and object to certain processing, by contacting privacy@goods.ng. Some records (for example financial transactions and payout history) must be kept to meet legal obligations.</p>

      <h2>Security</h2>
      <p>We use encryption in transit and at rest for sensitive data, hashed passwords, access controls, audit logs and independent approval for payouts and refunds.</p>
    </ProsePage>
  );
}
