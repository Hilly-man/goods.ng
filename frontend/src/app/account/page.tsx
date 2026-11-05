"use client";

import Link from "next/link";
import { useState } from "react";
import { Bell, CalendarClock, ChevronRight, Handshake, Heart, MessageCircle, Package, Phone, Store } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/components/auth-provider";
import { Alert, Badge, Button, Input, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { StateCitySelect } from "@/components/state-city-select";
import type { User } from "@/lib/types";

function PhoneVerify({ user }: { user: User }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const [phone, setPhone] = useState(user.phone ?? "");
  const [sent, setSent] = useState(false);
  const [dev, setDev] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (user.phone_verified) {
    return <p className="flex items-center gap-2 text-sm"><Phone className="size-4 text-brand-700" />{user.phone} <Badge tone="good">Verified</Badge></p>;
  }
  return (
    <div className="space-y-3">
      <Alert tone="warn" title="Verify your phone number">Required to sell, submit verification documents and use Goods Flex.</Alert>
      {!sent ? (
        <div className="flex gap-2">
          <div className="flex-1"><Input aria-label="Phone number" placeholder="0803 123 4567" value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
          <Button loading={busy} onClick={async () => {
            setBusy(true); setErr(null);
            try {
              const r = await http.post<{ dev_code?: string }>("/auth/otp/request", { phone: phone || undefined });
              setDev(r.dev_code ?? null); setSent(true);
            } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
          }}>Send code</Button>
        </div>
      ) : (
        <div className="space-y-2">
          {dev && <Alert tone="info" title="Development mode">SMS is not connected in development. Your code is {dev}.</Alert>}
          <div className="flex gap-2">
            <div className="flex-1"><Input aria-label="Verification code" inputMode="numeric" maxLength={6} placeholder="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} /></div>
            <Button loading={busy} onClick={async () => {
              setBusy(true); setErr(null);
              try { setUser(await http.post<User>("/auth/otp/verify", { code })); toast("Phone number verified"); }
              catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
            }}>Verify</Button>
          </div>
          <button className="text-sm text-brand-700 hover:underline" onClick={() => setSent(false)}>Change number or resend</button>
        </div>
      )}
      {err && <Alert tone="bad">{err}</Alert>}
    </div>
  );
}

function Profile({ user }: { user: User }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ full_name: user.full_name, state: user.state ?? "", city: user.city ?? "" });
  const [busy, setBusy] = useState(false);
  return (
    <form className="grid gap-3 sm:grid-cols-3" onSubmit={async (e) => {
      e.preventDefault(); setBusy(true);
      try { setUser(await http.patch<User>("/users/me", { full_name: f.full_name, state: f.state || undefined, city: f.city || undefined })); toast("Profile saved"); }
      catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
    }}>
      <Input label="Full name" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} />
      <StateCitySelect state={f.state} city={f.city} onChange={(v) => setF({ ...f, ...v })} />
      <div className="sm:col-span-3"><Button type="submit" loading={busy}>Save profile</Button></div>
    </form>
  );
}

const LINKS = [
  { href: "/orders", icon: Package, label: "My orders", sub: "Track protected purchases" },
  { href: "/offers", icon: Handshake, label: "My offers", sub: "Negotiations with sellers" },
  { href: "/messages", icon: MessageCircle, label: "Messages", sub: "Chats with sellers" },
  { href: "/saved", icon: Heart, label: "Saved items", sub: "Your favourites" },
  { href: "/flex", icon: CalendarClock, label: "Goods Flex", sub: "Instalments & repayments" },
  { href: "/account/notifications", icon: Bell, label: "Notification settings", sub: "Email, SMS & in-app" },
];

export default function AccountPage() {
  return (
    <RequireAuth>
      {(user) => (
        <div className="container-page max-w-4xl space-y-4 py-6">
          <h1 className="text-2xl font-bold">Hi, {user.full_name.split(" ")[0]}</h1>
          <div className="grid gap-2 sm:grid-cols-2">
            {LINKS.map((l) => (
              <Link key={l.href} href={l.href} className="card flex items-center gap-3 p-4 hover:shadow-[var(--shadow-pop)]">
                <span className="grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700"><l.icon className="size-5" /></span>
                <span className="flex-1"><span className="block font-semibold">{l.label}</span><span className="text-sm text-muted">{l.sub}</span></span>
                <ChevronRight className="size-4 text-muted" />
              </Link>
            ))}
            <Link href={user.seller ? "/seller" : "/seller/onboarding"} className="card flex items-center gap-3 bg-gradient-to-r from-brand-700 to-brand-800 p-4 text-white sm:col-span-2">
              <Store className="size-6" />
              <span className="flex-1"><span className="block font-semibold">{user.seller ? "Seller dashboard" : "Start selling on Goods.ng"}</span><span className="text-sm text-white/80">{user.seller ? user.seller.store_name : "Free listings. Protected payments."}</span></span>
              <ChevronRight className="size-4" />
            </Link>
          </div>
          <section className="card space-y-3 p-5"><h2 className="font-semibold">Phone number</h2><PhoneVerify user={user} /></section>
          <section className="card p-5"><h2 className="mb-3 font-semibold">Profile</h2><p className="mb-3 text-sm text-muted">{user.email}</p><Profile user={user} /></section>
        </div>
      )}
    </RequireAuth>
  );
}
