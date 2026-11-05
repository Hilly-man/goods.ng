import type { Metadata } from "next";
import { Mail, MapPin, MessageCircle, Phone } from "lucide-react";
import { ProsePage } from "@/components/prose";

export const metadata: Metadata = { title: "Contact us", alternates: { canonical: "/contact" } };

export default function Page() {
  const items = [
    { icon: Mail, label: "Email support", value: "support@goods.ng", href: "mailto:support@goods.ng" },
    { icon: Phone, label: "Phone (Mon–Sat, 8am–8pm)", value: "+234 201 330 0000", href: "tel:+2342013300000" },
    { icon: MessageCircle, label: "Disputes & order issues", value: "Open a dispute from your order page for the fastest response", href: "/orders" },
    { icon: MapPin, label: "Office", value: "Lagos, Nigeria" },
  ];
  return (
    <ProsePage title="Contact us" intro="We're here to help buyers and sellers.">
      <div className="not-prose grid gap-3 sm:grid-cols-2">
        {items.map((i) => (
          <a key={i.label} href={i.href} className="flex gap-3 rounded-xl border border-line p-4 hover:border-brand-600">
            <i.icon className="mt-0.5 size-5 shrink-0 text-brand-700" />
            <span><span className="block text-sm font-semibold">{i.label}</span><span className="text-sm text-muted">{i.value}</span></span>
          </a>
        ))}
      </div>
      <p className="mt-6 text-sm">Goods.ng staff will never ask for your password, OTP or card PIN.</p>
    </ProsePage>
  );
}
