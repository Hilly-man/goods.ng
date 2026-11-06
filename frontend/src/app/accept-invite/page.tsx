"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Input, PageLoader } from "@/components/ui";
import { http, errorMessage, ApiError } from "@/lib/api";

type Invite = { full_name: string; email: string; role: string; expires_at: string };

/** Staff invitation: set your password for the admin console (staff accounts never self-register). */
function Accept() {
  const token = useSearchParams().get("token") ?? "";
  const [inv, setInv] = useState<Invite | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [fieldErr, setFieldErr] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  useEffect(() => { http.get<Invite>(`/auth/staff-invite/${token}`).then(setInv).catch((e) => setErr(errorMessage(e))); }, [token]);
  if (err) return <Alert tone="bad">{err}</Alert>;
  if (!inv) return <PageLoader />;
  if (done) return (
    <div className="space-y-3">
      <Alert tone="good" title="You're all set">Your password is saved. Sign in with {inv.email}.</Alert>
      <Link href="/login" className="block text-center font-semibold text-brand-700">Sign in to the admin console →</Link>
    </div>
  );
  return (
    <form className="space-y-4" onSubmit={async (e) => {
      e.preventDefault();
      if (pw !== pw2) return setFieldErr("Passwords don't match");
      setBusy(true); setFieldErr(undefined);
      try { await http.post(`/auth/staff-invite/${token}`, { password: pw }); setDone(true); }
      catch (e) { if (e instanceof ApiError && e.status === 422) setFieldErr(Object.values(e.fieldErrors)[0]); else setErr(errorMessage(e)); }
      finally { setBusy(false); }
    }}>
      <p className="flex items-start gap-2 rounded-lg bg-brand-50 p-3 text-sm text-brand-900"><ShieldCheck className="mt-0.5 size-4 shrink-0" />
        Hi {inv.full_name.split(" ")[0]}, you&apos;ve been invited as <b className="mx-1">{inv.role}</b> ({inv.email}).</p>
      <Input label="Choose a password" type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)}
        hint="At least 10 characters with letters, numbers and a symbol" error={fieldErr} />
      <Input label="Confirm password" type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
      <Button type="submit" block size="lg" loading={busy}>Set password</Button>
    </form>
  );
}

export default function Page() {
  return <AuthShell title="Join the Goods.ng admin team" sub="Set a password for your staff account."><Suspense fallback={<PageLoader />}><Accept /></Suspense></AuthShell>;
}
