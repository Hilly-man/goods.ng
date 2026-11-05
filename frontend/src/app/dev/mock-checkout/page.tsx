"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import { Alert, Button, PageLoader } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { naira } from "@/lib/format";

/** DEVELOPMENT ONLY — stands in for a payment provider's hosted checkout page. Backend route exists only in dev/test. */
function MockCheckout() {
  const ref = useSearchParams().get("reference") ?? "";
  const [info, setInfo] = useState<{ amount: string; status: string; purpose: string; callback_url: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  useEffect(() => { http.get<typeof info>(`/dev/mock-provider/payments/${ref}`).then(setInfo).catch((e) => setErr(errorMessage(e))); }, [ref]);
  if (err) return <Alert tone="bad">{err}</Alert>;
  if (!info) return <PageLoader />;
  async function simulate(outcome: "success" | "failed") {
    setBusy(outcome);
    try {
      await http.post(`/dev/mock-provider/payments/${ref}/simulate`, { outcome });
      window.location.href = info!.callback_url.replace(/^https?:\/\/[^/]+/, "");
    } catch (e) { setErr(errorMessage(e)); setBusy(null); }
  }
  return (
    <div className="card space-y-4 p-6">
      <div className="flex items-center gap-2 text-amber-700"><FlaskConical className="size-5" /><span className="text-sm font-bold uppercase tracking-wide">Mock payment provider</span></div>
      <Alert tone="warn">Development only. No real money moves. In production this page is the licensed provider&apos;s hosted checkout.</Alert>
      <p className="text-sm text-muted">Reference <span className="font-mono">{ref}</span> · {info.purpose.replace(/_/g, " ")}</p>
      <p className="text-3xl font-extrabold">{naira(info.amount, { kobo: true })}</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <Button size="lg" loading={busy === "success"} onClick={() => simulate("success")}>Simulate successful payment</Button>
        <Button size="lg" variant="outline" loading={busy === "failed"} onClick={() => simulate("failed")}>Simulate failed payment</Button>
      </div>
    </div>
  );
}

export default function Page() {
  return <div className="container-page max-w-md py-10"><Suspense><MockCheckout /></Suspense></div>;
}
