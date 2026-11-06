"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { Check, Loader2 } from "lucide-react";

export type CaptchaConfig = { required: boolean; provider: "mock" | "recaptcha" | "turnstile" | null; site_key: string | null };

type Widget = { render: (el: HTMLElement, opts: Record<string, unknown>) => unknown; remove?: (id: unknown) => void; reset?: (id?: unknown) => void };
declare global {
  interface Window { grecaptcha?: Widget & { ready?: (cb: () => void) => void }; turnstile?: Widget }
}

const SCRIPTS = {
  recaptcha: "https://www.google.com/recaptcha/api.js?render=explicit",
  turnstile: "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit",
} as const;
const loading: Partial<Record<keyof typeof SCRIPTS, Promise<void>>> = {};

function loadScript(provider: keyof typeof SCRIPTS) {
  return (loading[provider] ??= new Promise<void>((resolve, reject) => {
    const s = document.createElement("script");
    s.src = SCRIPTS[provider];
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("captcha script failed to load"));
    document.head.appendChild(s);
  }));
}

/**
 * "I'm not a robot" check. Calls onToken(token) when solved and onToken(null) when it expires.
 * Remount it (change `key`) to get a fresh challenge — tokens are single-use.
 */
export function Captcha({ config, onToken }: { config: CaptchaConfig; onToken: (t: string | null) => void }) {
  const box = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);
  const provider = config.provider;

  useEffect(() => {
    if (provider !== "recaptcha" && provider !== "turnstile") return;
    if (!config.site_key) return;
    let id: unknown;
    let alive = true;
    loadScript(provider)
      .then(() => new Promise<void>((r) => {
        const ready = () => (provider === "recaptcha" ? window.grecaptcha?.render : window.turnstile?.render) ? r() : setTimeout(ready, 50);
        ready();
      }))
      .then(() => {
        if (!alive || !box.current) return;
        const api = provider === "recaptcha" ? window.grecaptcha! : window.turnstile!;
        id = api.render(box.current, {
          sitekey: config.site_key,
          callback: (t: string) => onToken(t),
          "expired-callback": () => onToken(null),
          "error-callback": () => onToken(null),
        });
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
      try { if (provider === "turnstile" && id !== undefined) window.turnstile?.remove?.(id); } catch { /* already gone */ }
    };
  }, [provider, config.site_key, onToken]);

  if (provider === "mock") return <MockCaptcha onToken={onToken} />;
  if (failed) return <p className="rounded-lg bg-red-50 p-3 text-sm text-red-700">The “I’m not a robot” check couldn’t load. Check your connection and refresh the page.</p>;
  return <div ref={box} className="min-h-[65px]" aria-label="I'm not a robot verification" />;
}

/** Development stand-in that looks and behaves like a checkbox captcha. Never accepted in production. */
function MockCaptcha({ onToken }: { onToken: (t: string | null) => void }) {
  const [state, setState] = useState<"idle" | "checking" | "done">("idle");
  return (
    <div className="flex h-[74px] w-full max-w-[304px] items-center justify-between rounded-md border border-[#d3d3d3] bg-[#f9f9f9] px-3 shadow-sm">
      <button type="button" role="checkbox" aria-checked={state === "done"} disabled={state !== "idle"}
        onClick={() => { setState("checking"); setTimeout(() => { setState("done"); onToken("mock-ok"); }, 700); }}
        className="flex items-center gap-3 text-left">
        <span className={clsx("grid size-7 place-items-center rounded-sm border-2 bg-white transition",
          state === "done" ? "border-transparent" : "border-[#c1c1c1] hover:border-[#b2b2b2]")}>
          {state === "checking" && <Loader2 className="size-5 animate-spin text-sky-600" />}
          {state === "done" && <Check className="size-6 text-brand-600" strokeWidth={3} />}
        </span>
        <span className="text-[14px] text-[#282727]">I&apos;m not a robot</span>
      </button>
      <span className="text-right leading-tight">
        <span className="block rounded bg-amber-100 px-1 text-[9px] font-bold uppercase text-amber-800">Dev mock</span>
        <span className="mt-0.5 block text-[9px] text-[#555]">No data sent</span>
      </span>
    </div>
  );
}
