"use client";

import { Suspense as RouteSuspense } from "react";
import { use, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, Button, ButtonLink, Checkbox, PageLoader } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { date, naira } from "@/lib/format";
import type { FinancingOption } from "@/lib/types";

type App = { id: string; status: string; order_id: string | null; purchase_amount: string; tenor_months: number; decline_reason: string | null; offer_terms: FinancingOption; offer_expires_at: string | null; credit_decision_ref: string; provider: string };

function View({ id }: { id: string }) {
  const { data: a } = useApi<App>(`/bnpl/applications/${id}`);
  const [accept, setAccept] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  if (!a) return <PageLoader />;
  if (a.status === "declined") return <Alert tone="bad" title="Application not approved">{a.decline_reason} You can still buy with Protected Checkout.</Alert>;
  const t = a.offer_terms;
  return (
    <div className="card space-y-4 p-5">
      {a.provider === "mock" && <Alert tone="warn" title="Development mode">This decision comes from a mock lending partner with illustrative terms. No credit is extended.</Alert>}
      {a.status === "approved" && <Alert tone="good" title="You're approved">Review the partner&apos;s terms below. Offer valid until {date(a.offer_expires_at, true)}.</Alert>}
      <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <div><dt className="text-muted">Purchase amount</dt><dd className="font-bold">{naira(a.purchase_amount)}</dd></div>
        <div><dt className="text-muted">Down payment (today)</dt><dd className="font-bold">{naira(t.down_payment)}</dd></div>
        <div><dt className="text-muted">Financed amount</dt><dd className="font-bold">{naira(t.financed_amount)}</dd></div>
        <div><dt className="text-muted">Financing charge</dt><dd className="font-bold">{naira(t.financing_charge)}</dd></div>
        <div><dt className="text-muted">Total payable</dt><dd className="font-bold">{naira(t.total_payable)}</dd></div>
        <div><dt className="text-muted">Decision reference</dt><dd className="font-mono text-xs">{a.credit_decision_ref}</dd></div>
      </dl>
      <div>
        <h2 className="font-semibold">Repayment schedule</h2>
        <table className="mt-2 w-full text-sm"><tbody>
          {t.schedule.map((s) => <tr key={s.sequence} className="border-b border-line/60"><td className="py-2">Instalment {s.sequence}</td><td>{date(s.due_date)}</td><td className="text-right font-semibold">{naira(s.amount)}</td></tr>)}
        </tbody></table>
        <p className="mt-2 text-xs text-muted">{t.apr_disclosure}</p>
      </div>
      {a.status === "approved" && (
        <>
          <Checkbox checked={accept} onChange={(e) => setAccept(e.target.checked)} label="I have read and accept these financing terms from the lending partner, and I can afford the repayments." />
          {err && <Alert tone="bad">{err}</Alert>}
          <Button size="lg" disabled={!accept} loading={busy} onClick={async () => {
            setBusy(true); setErr(null);
            try { const r = await http.post<{ authorization_url: string }>(`/bnpl/applications/${a.id}/accept`, { accept_terms: true }); window.location.href = r.authorization_url; }
            catch (e) { setErr(errorMessage(e)); setBusy(false); }
          }}>Accept & pay {naira(t.down_payment)} down payment</Button>
        </>
      )}
      {["accepted", "active", "completed"].includes(a.status) && a.order_id && <ButtonLink href={`/orders/${a.order_id}`}>View order</ButtonLink>}
    </div>
  );
}

function Inner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RequireAuth>{() => <div className="container-page max-w-3xl py-6"><h1 className="mb-4 text-2xl font-bold">Goods Flex application</h1><View id={id} /></div>}</RequireAuth>;
}

export default function Page(props: { params: Promise<{ id: string }> }) {
  return (
    <RouteSuspense fallback={<PageLoader />}>
      <Inner {...props} />
    </RouteSuspense>
  );
}
