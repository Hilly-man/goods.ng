"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button, Input } from "@/components/ui";
import { errorMessage } from "@/lib/api";

export { safeNext } from "@/lib/safe-next";
import { safeNext } from "@/lib/safe-next";

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const u = await login(email, password);
      router.replace(next === "/" && u.role !== "user" ? "/admin" : next);
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      {err && <Alert tone="bad">{err}</Alert>}
      <Input label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
      <div className="text-right text-sm"><Link href="/forgot-password" className="font-medium text-brand-700 hover:underline">Forgot password?</Link></div>
      <Button type="submit" block size="lg" loading={busy}>Sign in</Button>
      <p className="text-center text-sm text-muted">New to Goods.ng? <Link href={`/register${next !== "/" ? `?next=${encodeURIComponent(next)}` : ""}`} className="font-semibold text-brand-700 hover:underline">Create an account</Link></p>
    </form>
  );
}
