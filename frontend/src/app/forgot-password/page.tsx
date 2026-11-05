"use client";

import Link from "next/link";
import { useState } from "react";
import { AuthShell } from "@/components/auth-shell";
import { Alert, Button, Input } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [step, setStep] = useState<"email" | "code" | "done">("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [devCode, setDevCode] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setErr(null);
    try { await fn(); } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
  }
  return (
    <AuthShell title="Reset your password" sub={step === "email" ? "We'll email you a 6-digit code." : undefined}>
      {err && <Alert tone="bad" className="mb-4">{err}</Alert>}
      {step === "email" && (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); run(async () => {
          const r = await http.post<{ dev_code?: string }>("/auth/password/forgot", { email });
          setDevCode(r.dev_code ?? null);
          setStep("code");
        }); }}>
          <Input label="Email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <Button type="submit" block loading={busy}>Send code</Button>
        </form>
      )}
      {step === "code" && (
        <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); run(async () => {
          await http.post("/auth/password/reset", { email, code, new_password: pw });
          setStep("done");
        }); }}>
          <Alert tone="info">If an account exists for {email}, a code is on its way.</Alert>
          {devCode && <Alert tone="warn" title="Development mode">Code: {devCode}</Alert>}
          <Input label="6-digit code" inputMode="numeric" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value)} />
          <Input label="New password" type="password" autoComplete="new-password" required value={pw} onChange={(e) => setPw(e.target.value)} hint="At least 8 characters with letters and numbers" />
          <Button type="submit" block loading={busy}>Update password</Button>
        </form>
      )}
      {step === "done" && (
        <div className="space-y-4">
          <Alert tone="good" title="Password updated">You&apos;ve been signed out of all devices for your security.</Alert>
          <Link href="/login" className="block text-center font-semibold text-brand-700">Sign in →</Link>
        </div>
      )}
    </AuthShell>
  );
}
