"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import clsx from "clsx";
import { Bell, CalendarClock, Camera, ChevronRight, Copy, Handshake, Heart, KeyRound, Loader2, Mail, MessageCircle, Package, Phone, Store, Trash2 } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/components/auth-provider";
import { Alert, Badge, Button, Input, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { StateCitySelect } from "@/components/state-city-select";
import type { User } from "@/lib/types";
import { Avatar } from "@/components/avatar";

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

function EmailVerify({ user }: { user: User }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const [sent, setSent] = useState(false);
  const [dev, setDev] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  if (user.email_verified) {
    return <p className="flex items-center gap-2 text-sm"><Mail className="size-4 text-brand-700" />{user.email} <Badge tone="good">Verified</Badge></p>;
  }
  async function resend() {
    setBusy(true); setErr(null);
    try {
      const r = await http.post<{ dev_code?: string }>("/auth/email/resend", {});
      setDev(r.dev_code ?? null); setSent(true);
    } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
  }
  return (
    <div className="space-y-3">
      <Alert tone="warn" title="Verify your email address">Required before checkout. We&apos;ll send a 6-digit code to {user.email}.</Alert>
      {!sent ? (
        <Button loading={busy} onClick={resend}>Send verification code</Button>
      ) : (
        <div className="space-y-2">
          {dev && <Alert tone="info" title="Development mode">Email is not connected in development. Your code is {dev}.</Alert>}
          <div className="flex gap-2">
            <div className="flex-1"><Input aria-label="Email verification code" inputMode="numeric" maxLength={6} placeholder="6-digit code" value={code} onChange={(e) => setCode(e.target.value)} /></div>
            <Button loading={busy} onClick={async () => {
              setBusy(true); setErr(null);
              try { setUser(await http.post<User>("/auth/email/verify", { code })); toast("Email verified"); }
              catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
            }}>Verify</Button>
          </div>
          <button className="text-sm text-brand-700 hover:underline" onClick={resend}>Resend code</button>
        </div>
      )}
      {err && <Alert tone="bad">{err}</Alert>}
    </div>
  );
}

const MAX_PHOTO_MB = 8;
const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

function ProfilePhoto({ user }: { user: User }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const input = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function upload(file: File) {
    if (!PHOTO_TYPES.includes(file.type)) return toast("Choose a JPEG, PNG or WebP image", "bad");
    if (file.size > MAX_PHOTO_MB * 1024 * 1024) return toast(`Photo must be under ${MAX_PHOTO_MB}MB`, "bad");
    const url = URL.createObjectURL(file);
    setPreview(url);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      setUser(await http.post<User>("/users/me/avatar", fd));
      toast("Profile photo updated");
    } catch (e) {
      toast(errorMessage(e), "bad");
    } finally {
      setPreview(null);
      URL.revokeObjectURL(url);
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  async function remove() {
    setBusy(true);
    try { setUser(await http.del<User>("/users/me/avatar")); toast("Profile photo removed"); }
    catch (e) { toast(errorMessage(e), "bad"); }
    finally { setBusy(false); }
  }

  const src = preview ?? user.avatar_url;
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative">
        <Avatar name={user.full_name} src={src} className={clsx("size-28 text-3xl ring-4 ring-white shadow-md", busy && "opacity-60")} />
        {busy && <Loader2 className="absolute inset-0 m-auto size-7 animate-spin text-brand-700" aria-label="Uploading" />}
        <button
          type="button"
          onClick={() => input.current?.click()}
          disabled={busy}
          aria-label={user.avatar_url ? "Change profile photo" : "Add profile photo"}
          className="absolute bottom-0 right-0 grid size-9 place-items-center rounded-full bg-white text-ink shadow-md ring-1 ring-line transition hover:bg-canvas disabled:opacity-60"
        >
          <Camera className="size-4" />
        </button>
        <input ref={input} type="file" accept={PHOTO_TYPES.join(",")} className="sr-only" tabIndex={-1}
               onChange={(e) => { const f = e.target.files?.[0]; if (f) void upload(f); }} />
      </div>
      <div className="flex items-center gap-3 text-sm">
        <button type="button" disabled={busy} onClick={() => input.current?.click()} className="font-semibold text-brand-700 hover:underline disabled:opacity-60">
          {user.avatar_url ? "Change photo" : "Upload a photo"}
        </button>
        {user.avatar_url && (
          <button type="button" disabled={busy} onClick={() => void remove()} className="inline-flex items-center gap-1 text-muted hover:text-red-600 disabled:opacity-60">
            <Trash2 className="size-3.5" />Remove
          </button>
        )}
      </div>
      <p className="text-center text-xs text-muted">Optional. JPEG, PNG or WebP up to {MAX_PHOTO_MB}MB. Buyers and sellers see it in chats.</p>
    </div>
  );
}

function Profile({ user }: { user: User }) {
  const { setUser } = useAuth();
  const toast = useToast();
  const [f, setF] = useState({ full_name: user.full_name, state: user.state ?? "", city: user.city ?? "" });
  const [busy, setBusy] = useState(false);
  return (
    <div className="grid gap-6 md:grid-cols-[200px_1fr] md:gap-8">
      <ProfilePhoto user={user} />
      <div className="space-y-4">
        <form className="grid gap-3 sm:grid-cols-2" onSubmit={async (e) => {
          e.preventDefault(); setBusy(true);
          try { setUser(await http.patch<User>("/users/me", { full_name: f.full_name, state: f.state || undefined, city: f.city || undefined })); toast("Profile saved"); }
          catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
        }}>
          <div className="sm:col-span-2"><Input label="Full name" value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} /></div>
          <div className="sm:col-span-2"><Input label="Email" value={user.email} disabled hint={user.email_verified ? "Verified" : undefined} /></div>
          <StateCitySelect state={f.state} city={f.city} onChange={(v) => setF({ ...f, ...v })} />
          <div className="sm:col-span-2"><Button type="submit" loading={busy}>Save details</Button></div>
        </form>
        <div className="flex items-center gap-3 rounded-xl border border-line p-3 text-sm">
          <GoogleMark />
          <span className="flex-1 font-medium">Google</span>
          {user.google_linked
            ? <Badge tone="good">Connected</Badge>
            : <span className="text-right text-xs text-muted">Not connected — sign in with Google using {user.email} to link it.</span>}
        </div>
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" className="size-5 shrink-0" aria-hidden>
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

type TotpSetup = { secret: string; otpauth_url: string; qr_svg: string };

function TotpQr({ setup }: { setup: TotpSetup }) {
  const toast = useToast();
  const [showKey, setShowKey] = useState(false);
  const grouped = setup.secret.replace(/(.{4})/g, "$1 ").trim();
  return (
    <div className="grid gap-5 rounded-xl border border-line p-4 sm:grid-cols-[auto_1fr] sm:items-center">
      <div className="mx-auto rounded-xl bg-white p-2 ring-1 ring-line">
        {/* QR is rendered by our API from the otpauth URL — never by a third-party QR service. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={setup.qr_svg} alt="QR code to add Goods.ng to your authenticator app" className="size-44" />
      </div>
      <ol className="space-y-2 text-sm">
        <li><b>1. Install an authenticator app</b> — Google Authenticator, Microsoft Authenticator or Authy.</li>
        <li><b>2. Scan this QR code</b> in the app (tap <b>+</b> → <i>Scan a QR code</i>). &ldquo;Goods.ng&rdquo; will appear with a 6-digit code.</li>
        <li className="pt-1">
          {!showKey ? (
            <button type="button" className="font-semibold text-brand-700 hover:underline" onClick={() => setShowKey(true)}>Can&apos;t scan? Enter a setup key instead</button>
          ) : (
            <span className="block rounded-lg bg-canvas p-3">
              <span className="block text-xs text-muted">Setup key (time-based)</span>
              <span className="mt-1 flex items-center gap-2">
                <code className="flex-1 break-all font-mono text-[15px] tracking-wide">{grouped}</code>
                <button type="button" aria-label="Copy setup key" className="rounded-md p-1.5 text-muted hover:bg-white hover:text-ink"
                        onClick={() => { void navigator.clipboard?.writeText(setup.secret).then(() => toast("Setup key copied")); }}>
                  <Copy className="size-4" />
                </button>
              </span>
            </span>
          )}
        </li>
      </ol>
    </div>
  );
}

function TwoFactor({ user }: { user: User }) {
  const { reload } = useAuth();
  const toast = useToast();
  const [setup, setSetup] = useState<TotpSetup | null>(null);
  const [codes, setCodes] = useState<string[] | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (codes) {
    return (
      <div className="space-y-3">
        <Alert tone="good" title="Two-factor authentication enabled">
          Save these recovery codes somewhere safe. Each can be used once if you lose your authenticator.
          <div className="mt-2 grid grid-cols-2 gap-1 font-mono text-xs">{codes.map((c) => <span key={c}>{c}</span>)}</div>
        </Alert>
        <Button variant="outline" onClick={() => setCodes(null)}>I&apos;ve saved them</Button>
      </div>
    );
  }

  if (user.two_factor_enabled) {
    return (
      <div className="space-y-3">
        <p className="flex items-center gap-2 text-sm"><KeyRound className="size-4 text-brand-700" />Two-factor is <Badge tone="good">Enabled</Badge></p>
        <div className="grid gap-2 sm:grid-cols-2">
          <Input label="Password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Input label="Code or recovery code" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} />
        </div>
        {err && <Alert tone="bad">{err}</Alert>}
        <Button variant="outline" loading={busy} onClick={async () => {
          setBusy(true); setErr(null);
          try {
            await http.post("/auth/2fa/disable", { password, code });
            setPassword(""); setCode(""); await reload(); toast("Two-factor authentication disabled");
          } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
        }}>Disable two-factor</Button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {!setup ? (
        <>
          <p className="text-sm text-muted">Add an authenticator app as a second step at login. Recommended for every admin account.</p>
          <Button loading={busy} onClick={async () => {
            setBusy(true); setErr(null);
            try { setSetup(await http.post<TotpSetup>("/auth/2fa/setup")); }
            catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
          }}>Set up two-factor</Button>
        </>
      ) : (
        <>
          <TotpQr setup={setup} />
          <Input label="3. Enter the 6-digit code from the app" inputMode="numeric" maxLength={6} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
          {err && <Alert tone="bad">{err}</Alert>}
          <Button loading={busy} disabled={code.length !== 6} onClick={async () => {
            setBusy(true); setErr(null);
            try {
              const r = await http.post<{ recovery_codes: string[] }>("/auth/2fa/enable", { code });
              setCodes(r.recovery_codes); setSetup(null); setCode(""); await reload(); toast("Two-factor authentication enabled");
            } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
          }}>Enable two-factor</Button>
        </>
      )}
      {!setup && err && <Alert tone="bad">{err}</Alert>}
    </div>
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
          <div className="flex items-center gap-3">
            <Avatar name={user.full_name} src={user.avatar_url} className="size-12 text-lg" />
            <h1 className="text-2xl font-bold">Hi, {user.full_name.split(" ")[0]}</h1>
          </div>
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
          <section id="personal-details" className="card p-5 sm:p-6"><h2 className="mb-5 text-lg font-semibold">Personal details</h2><Profile user={user} /></section>
          <section className="card space-y-3 p-5"><h2 className="font-semibold">Email address</h2><EmailVerify user={user} /></section>
          <section className="card space-y-3 p-5"><h2 className="font-semibold">Phone number</h2><PhoneVerify user={user} /></section>
          <section className="card space-y-3 p-5"><h2 className="font-semibold">Two-factor authentication</h2><TwoFactor user={user} /></section>
        </div>
      )}
    </RequireAuth>
  );
}
