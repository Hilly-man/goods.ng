"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, ButtonLink, Spinner } from "@/components/ui";
import { http } from "@/lib/api";

function Verify() {
  const ref = useSearchParams().get("reference");
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!ref) return;
    let n = 0, alive = true;
    const tick = async () => {
      const p = await http.post<{ status: string }>(`/payments/${ref}/verify`).catch(() => null);
      if (!alive) return;
      if (p && p.status !== "initialized") { setStatus(p.status); return; }
      if (++n < 10) setTimeout(tick, 2000); else setStatus("pending");
    };
    tick();
    return () => { alive = false; };
  }, [ref]);

  if (!status) return <div className="flex flex-col items-center gap-3 py-10"><Spinner className="size-8" /><p>Confirming your payment…</p></div>;
  if (status === "success") {
    return (
      <div className="space-y-3">
        <Alert tone="good" title="Your listing is promoted!">It now has extra visibility in search and on the home feed until the package ends.</Alert>
        <ButtonLink href="/seller/products">Back to my products</ButtonLink>
      </div>
    );
  }
  if (status === "pending") {
    return <Alert tone="info" title="Still confirming">We&apos;ll activate the promotion as soon as the payment is confirmed.</Alert>;
  }
  return (
    <div className="space-y-3">
      <Alert tone="bad" title="Payment not completed">The promotion was not activated and you were not charged.</Alert>
      <ButtonLink href="/seller/products" variant="outline">Back to my products</ButtonLink>
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <div className="max-w-lg"><Suspense><Verify /></Suspense></div>}</RequireAuth>;
}
