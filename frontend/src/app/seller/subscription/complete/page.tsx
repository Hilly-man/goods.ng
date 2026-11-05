"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/components/auth-provider";
import { Alert, ButtonLink, Spinner } from "@/components/ui";
import { http } from "@/lib/api";

function Verify() {
  const ref = useSearchParams().get("reference");
  const { reload } = useAuth();
  const [status, setStatus] = useState<string | null>(null);
  useEffect(() => {
    if (!ref) return;
    let n = 0, alive = true;
    const tick = async () => {
      const p = await http.post<{ status: string }>(`/payments/${ref}/verify`).catch(() => null);
      if (!alive) return;
      if (p && p.status !== "initialized") { setStatus(p.status); if (p.status === "success") reload(); return; }
      if (++n < 10) setTimeout(tick, 2000); else setStatus("pending");
    };
    tick();
    return () => { alive = false; };
  }, [ref, reload]);
  if (!status) return <div className="flex flex-col items-center gap-3 py-10"><Spinner className="size-8" /><p>Confirming your payment…</p></div>;
  if (status === "success") return <div className="space-y-3"><Alert tone="good" title="Welcome to Premium!">Your Premium Seller features are now active.</Alert><ButtonLink href="/seller/storefront">Set up WhatsApp & call buttons</ButtonLink></div>;
  if (status === "pending") return <Alert tone="info" title="Still confirming">We&apos;ll activate Premium as soon as the payment is confirmed.</Alert>;
  return <div className="space-y-3"><Alert tone="bad" title="Payment not completed">Premium was not activated.</Alert><ButtonLink href="/premium">Try again</ButtonLink></div>;
}

export default function Page() {
  return <RequireAuth seller>{() => <div className="max-w-lg"><Suspense><Verify /></Suspense></div>}</RequireAuth>;
}
