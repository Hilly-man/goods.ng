import type { Metadata } from "next";
import Link from "next/link";
import { Bug, HelpCircle, Mail, MapPin, MessageCircle, Phone, ShieldAlert } from "lucide-react";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = {
  title: "Contact us",
  description: "Get help from the Goods.ng customer support team — email, phone, disputes and security reports.",
  alternates: { canonical: "/contact" },
};

export default function Page() {
  const items = [
    { icon: Mail, label: "Customer care", value: "support@goods.ng", note: "Questions, suggestions and feedback", href: "mailto:support@goods.ng" },
    { icon: Phone, label: "Phone (Mon–Sat, 8am–8pm)", value: "+234 201 330 0000", href: "tel:+2342013300000" },
    { icon: MessageCircle, label: "Disputes & order issues", value: "Open a dispute from your order page for the fastest response", href: "/orders" },
    { icon: MapPin, label: "Office", value: "Lagos, Nigeria" },
  ];
  return (
    <ProsePage
      title="Contact us"
      intro="The Goods.ng customer support team is always ready to answer your questions and give you the help you need."
    >
      <p>
        <b>Goods.ng customer care</b> — email your questions, suggestions and comments to{" "}
        <a href="mailto:support@goods.ng" className="font-semibold text-brand-700 underline">support@goods.ng</a>.
      </p>

      <div className="not-prose mt-5 grid gap-3 sm:grid-cols-2">
        {items.map((i) => {
          const body = (
            <>
              <i.icon className="mt-0.5 size-5 shrink-0 text-brand-700" />
              <span>
                <span className="block text-sm font-semibold">{i.label}</span>
                <span className="block text-sm text-muted">{i.value}</span>
                {i.note && <span className="block text-xs text-muted">{i.note}</span>}
              </span>
            </>
          );
          return i.href ? (
            <a key={i.label} href={i.href} className="flex gap-3 rounded-xl border border-line p-4 transition hover:border-brand-600">{body}</a>
          ) : (
            <div key={i.label} className="flex gap-3 rounded-xl border border-line p-4">{body}</div>
          );
        })}
      </div>

      <div className="not-prose mt-5 flex gap-3 rounded-xl bg-amber-50 p-4 text-amber-950 ring-1 ring-amber-200">
        <Bug className="mt-0.5 size-5 shrink-0 text-amber-700" />
        <p className="text-sm">
          <b>Found a bug or have a security question?</b> Get in touch with our team at{" "}
          <a href="mailto:security@goods.ng" className="font-semibold text-amber-900 underline">security@goods.ng</a>.
          Please include steps to reproduce, and don&apos;t test against other people&apos;s accounts or data.
        </p>
      </div>

      <div className="not-prose mt-5 flex flex-col items-start gap-3 rounded-2xl bg-brand-50 p-5 sm:flex-row sm:items-center sm:justify-between">
        <span className="flex items-center gap-3">
          <HelpCircle className="size-6 shrink-0 text-brand-700" />
          <span>
            <span className="block font-semibold">Check our Frequently Asked Questions</span>
            <span className="text-sm text-muted">Fees, delivery, disputes, Premium and Goods Flex — answered.</span>
          </span>
        </span>
        <Link href="/faq" className="inline-flex h-11 shrink-0 items-center rounded-lg bg-brand-700 px-5 text-sm font-semibold text-white hover:bg-brand-800">
          Visit FAQ page
        </Link>
      </div>

      <p className="mt-6 flex items-start gap-2 text-sm">
        <ShieldAlert className="mt-0.5 size-4 shrink-0 text-brand-700" />
        Goods.ng staff will never ask for your password, OTP or card PIN.
      </p>
    </ProsePage>
  );
}
