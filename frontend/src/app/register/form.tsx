"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button, Checkbox, Input } from "@/components/ui";
import { ApiError, errorMessage } from "@/lib/api";
import { safeNext } from "../login/form";

export function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [f, setF] = useState({ full_name: "", email: "", phone: "", password: "" });
  const [terms, setTerms] = useState(false);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) => setF({ ...f, [k]: e.target.value });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const local: Record<string, string> = {};
    if (f.password.length < 8 || !/\d/.test(f.password) || !/[a-z]/i.test(f.password)) local.password = "Use at least 8 characters with letters and numbers";
    if (!terms) local.terms = "Please accept the terms to continue";
    setErrs(local);
    if (Object.keys(local).length) return;
    setBusy(true);
    setErr(null);
    try {
      await register({ ...f, phone: f.phone || undefined });
      router.replace(next === "/" ? "/account?welcome=1" : next);
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) setErrs(e.fieldErrors);
      else setErr(errorMessage(e));
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {err && <Alert tone="bad">{err}</Alert>}
      <Input label="Full name" autoComplete="name" required value={f.full_name} onChange={set("full_name")} error={errs.full_name} />
      <Input label="Email" type="email" autoComplete="email" required value={f.email} onChange={set("email")} error={errs.email} />
      <Input label="Phone number" type="tel" autoComplete="tel" placeholder="0803 123 4567" value={f.phone} onChange={set("phone")} error={errs.phone} hint="Needed to sell, verify your account and use Goods Flex." />
      <Input label="Password" type="password" autoComplete="new-password" required value={f.password} onChange={set("password")} error={errs.password} />
      <div>
        <Checkbox checked={terms} onChange={(e) => setTerms(e.target.checked)} label={<>I agree to the <Link href="/terms" className="text-brand-700 underline">Terms</Link> and <Link href="/privacy" className="text-brand-700 underline">Privacy Policy</Link>.</>} />
        {errs.terms && <p className="mt-1 text-sm text-red-600">{errs.terms}</p>}
      </div>
      <Button type="submit" block size="lg" loading={busy}>Create account</Button>
      <p className="text-center text-sm text-muted">Already have an account? <Link href="/login" className="font-semibold text-brand-700 hover:underline">Sign in</Link></p>
    </form>
  );
}
