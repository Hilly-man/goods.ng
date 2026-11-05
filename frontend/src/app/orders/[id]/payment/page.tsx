"use client";

import { PageLoader as RouteLoader } from "@/components/ui";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, ButtonLink, Spinner } from "@/components/ui";
import { http } from "@/lib/api";

function Verify({ orderId }: { orderId: string }) {
  const ref = useSearchParams().get("reference");
  const router = useRouter();
  const [state, setState] = useState<"checking" | "failed" | "pending">("checking");
  useEffect(() => {
    if (!ref) return;
    let tries = 0, alive = true;
    const tick = async () => {
      // Server-side verification with the provider — the redirect itself proves nothing.
      const p = await http.post<{ status: string }>(`/payments/${ref}/verify`).catch(() => null);
      if (!alive) return;
      if (p?.status === "success") return router.replace(`/orders/${orderId}?paid=1`);
      if (p && ["failed", "abandoned"].includes(p.status)) return setState("failed");
      if (++tries > 10) return setState("pending");
      setTimeout(tick, 2000);
    };
    tick();
    return () => { alive = false; };
  }, [ref, orderId, router]);
  if (state === "failed") return <div className="space-y-3"><Alert tone="bad" title="Payment not completed">No money has been taken for this order, or it will be reversed by your bank.</Alert><ButtonLink href={`/orders/${orderId}`}>Back to order</ButtonLink></div>;
  if (state === "pending") return <div className="space-y-3"><Alert tone="info" title="Still confirming your payment">We&apos;ll update your order as soon as the payment provider confirms it.</Alert><ButtonLink href={`/orders/${orderId}`}>View order</ButtonLink></div>;
  return <div className="flex flex-col items-center gap-3 py-10 text-center"><Spinner className="size-8" /><p className="font-semibold">Confirming your payment with the provider…</p><p className="text-sm text-muted">Please don&apos;t close this page.</p></div>;
}

function Inner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RequireAuth>{() => <div className="container-page max-w-lg py-10"><Suspense><Verify orderId={id} /></Suspense></div>}</RequireAuth>;
}

export default function Page(props: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<RouteLoader />}>
      <Inner {...props} />
    </Suspense>
  );
}
