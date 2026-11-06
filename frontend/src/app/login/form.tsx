"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button, Input } from "@/components/ui";
import { ApiError, errorMessage, http } from "@/lib/api";
import { Captcha, type CaptchaConfig } from "@/components/captcha";
import { isAdminHost, useIsAdminArea } from "@/lib/admin-area";
import { GoogleButton, OAUTH_ERRORS } from "@/components/google-button";

export { safeNext } from "@/lib/safe-next";
import { safeNext } from "@/lib/safe-next";

export function LoginForm() {
  const { login, verifyMfa } = useAuth();
  const router = useRouter();
  const sp = useSearchParams();
  const next = safeNext(sp.get("next"));
  const oauthError = sp.get("oauth_error");
  const adminArea = useIsAdminArea();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mfaTicket, setMfaTicket] = useState<string | null>(null);
  const [mfaCode, setMfaCode] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // "I'm not a robot": shown when this browser hasn't signed in within 24h, or after failed attempts.
  const [captcha, setCaptcha] = useState<CaptchaConfig | null>(null);
  const [captchaToken, setCaptchaToken] = useState<string | null>(null);
  const [captchaKey, setCaptchaKey] = useState(0);
  const onCaptcha = useCallback((t: string | null) => setCaptchaToken(t), []);
  const freshCaptcha = () => { setCaptchaToken(null); setCaptchaKey((k) => k + 1); };
  useEffect(() => {
    let alive = true;
    http.get<CaptchaConfig>("/auth/captcha").then((c) => { if (alive) setCaptcha(c); }).catch(() => {});
    return () => { alive = false; };
  }, []);
  const needCaptcha = !!captcha?.required && !!captcha.provider;

  // Google sign-in for an account with 2FA comes back as /login#mfa=<ticket>; the hash never reaches a server.
  useEffect(() => {
    const m = window.location.hash.match(/^#mfa=([\w.-]+)$/);
    if (!m) return;
    history.replaceState(null, "", window.location.pathname + window.location.search);
    void Promise.resolve().then(() => setMfaTicket(m[1]));
  }, []);

  function go(u: { role: string }) {
    if (next === "/" && u.role !== "user") {
      // Admins land on the console: "/" on the admin subdomain; elsewhere the subdomain (or /admin if none).
      if (isAdminHost()) router.replace("/");
      else if (process.env.NEXT_PUBLIC_ADMIN_URL) window.location.assign(process.env.NEXT_PUBLIC_ADMIN_URL);
      else router.replace("/admin");
      return;
    }
    router.replace(next);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      if (mfaTicket) {
        go(await verifyMfa(mfaTicket, mfaCode));
        return;
      }
      const r = await login(email, password, captchaToken);
      if ("mfaRequired" in r) {
        setMfaTicket(r.ticket);
        setBusy(false);
        return;
      }
      go(r.user);
    } catch (e) {
      if (e instanceof ApiError && e.code === "captcha_required") {
        const cfg = (e.details as { config?: CaptchaConfig } | undefined)?.config;
        setCaptcha(cfg ?? { required: true, provider: captcha?.provider ?? "mock", site_key: captcha?.site_key ?? null });
        setErr(captchaToken ? "That check expired — please tick “I’m not a robot” again." : "Please tick “I’m not a robot” to continue.");
      } else {
        setErr(errorMessage(e));
      }
      if (needCaptcha || (e instanceof ApiError && e.code === "captcha_required")) freshCaptcha();
      setBusy(false);
    }
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      {err && <Alert tone="bad">{err}</Alert>}
      {!err && oauthError && <Alert tone="bad">{OAUTH_ERRORS[oauthError] ?? OAUTH_ERRORS.google}</Alert>}
      {mfaTicket ? (
        <>
          <Alert tone="info" title="Two-factor authentication">Enter the 6-digit code from your authenticator app, or one of your recovery codes.</Alert>
          <Input label="Authentication code" inputMode="numeric" autoComplete="one-time-code" required value={mfaCode} onChange={(e) => setMfaCode(e.target.value)} />
          <Button type="submit" block size="lg" loading={busy}>Verify and sign in</Button>
          <button type="button" className="w-full text-center text-sm text-brand-700 hover:underline" onClick={() => { setMfaTicket(null); setMfaCode(""); setErr(null); }}>Use a different account</button>
        </>
      ) : (
        <>
          {!adminArea && <GoogleButton next={next} label="Continue with Google" divider="or sign in with email" />}
          <Input label="Email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input label="Password" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          <div className="text-right text-sm"><Link href="/forgot-password" className="font-medium text-brand-700 hover:underline">Forgot password?</Link></div>
          {needCaptcha && captcha && (
            <div className="flex justify-center">
              <Captcha key={captchaKey} config={captcha} onToken={onCaptcha} />
            </div>
          )}
          <Button type="submit" block size="lg" loading={busy} disabled={needCaptcha && !captchaToken}>Sign in</Button>
          {needCaptcha && !captchaToken && <p className="-mt-2 text-center text-xs text-muted">For your security we check it’s really you when you sign in on a new device or after a day away.</p>}
          <p className="text-center text-sm text-muted">New to Goods.ng? <Link href={`/register${next !== "/" ? `?next=${encodeURIComponent(next)}` : ""}`} className="font-semibold text-brand-700 hover:underline">Create an account</Link></p>
        </>
      )}
    </form>
  );
}
