"use client";

import { Suspense, use, useEffect, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Alert, Button, Checkbox, PageLoader } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, naira } from "@/lib/format";

type Req = { guarantor_name: string; borrower_name: string; relationship: string; status: string; amount_guaranteed: string; expires_at: string };

/** Public page for guarantors (no Goods.ng account needed); reached via the SMS link. */
function Consent({ token }: { token: string }) {
  const [r, setR] = useState<Req | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [agree, setAgree] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { http.get<Req>(`/bnpl/guarantor/${token}`).then(setR).catch((e) => setErr(errorMessage(e))); }, [token]);
  if (err) return <Alert tone="bad">{err}</Alert>;
  if (!r) return <PageLoader />;
  async function respond(yes: boolean) {
    setBusy(true);
    try {
      const res = await http.post<{ status: string }>(`/bnpl/guarantor/${token}`, { agree: yes });
      setR({ ...r!, status: res.status });
    } catch (e) { setErr(errorMessage(e)); } finally { setBusy(false); }
  }
  return (
    <div className="card space-y-4 p-6">
      <div className="flex items-center gap-2 text-brand-700"><ShieldCheck className="size-6" /><h1 className="text-xl font-bold text-ink">Guarantor request</h1></div>
      <p>Hello {r.guarantor_name.split(" ")[0]}, <b>{r.borrower_name}</b> ({r.relationship}) has named you as their guarantor for <b>Goods Flex</b> purchases on Goods.ng
        {Number(r.amount_guaranteed) > 0 ? <> up to <b>{naira(r.amount_guaranteed)}</b></> : null}.</p>
      <ul className="list-disc space-y-1 pl-5 text-sm text-ink/80">
        <li>If they stop repaying, our lending partner may contact you to help resolve the debt.</li>
        <li>Your BVN is verified with NIBSS and stored encrypted; only the last four digits are shown.</li>
        <li>You can decline or withdraw consent. Nothing changes for you if you decline, and the borrower&apos;s limit is suspended until someone else consents.</li>
        <li>This request expires {date(r.expires_at)}.</li>
      </ul>
      {r.status === "pending_consent" ? (
        <>
          <Checkbox checked={agree} onChange={(e) => setAgree(e.target.checked)} label={`I know ${r.borrower_name} and agree to guarantee their Goods Flex repayments${Number(r.amount_guaranteed) > 0 ? ` up to ${naira(r.amount_guaranteed)}` : ""}, and to Goods.ng processing my name, phone and BVN for this purpose.`} />
          <div className="flex gap-2">
            <Button disabled={!agree} loading={busy} onClick={() => respond(true)}>I agree</Button>
            <Button variant="outline" loading={busy} onClick={() => respond(false)}>Decline</Button>
          </div>
        </>
      ) : (
        <Alert tone={r.status === "consented" ? "good" : "info"} title={r.status === "consented" ? "Thank you — you've agreed" : `This request is ${r.status.replace("_", " ")}`} />
      )}
    </div>
  );
}

function Inner({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  return <Consent token={token} />;
}

export default function Page(props: { params: Promise<{ token: string }> }) {
  return <div className="container-page max-w-lg py-10"><Suspense fallback={<PageLoader />}><Inner {...props} /></Suspense></div>;
}
