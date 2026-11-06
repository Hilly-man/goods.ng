"use client";

import { Landmark } from "lucide-react";
import { FilterChips, AdminPageHeader, StatusBadge } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable } from "@/components/admin-table";
import { Alert, Badge, PageLoader } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { date, naira, titleCase } from "@/lib/format";

type E = { id: string; order_id: string; order_number: string; status: string; provider: string; provider_escrow_ref: string | null; amount: string; seller_amount: string; platform_amount: string; funded_at: string | null; release_eligible_at: string | null; released_at: string | null; refunded_at: string | null };
type L = { trial_balance: { debits: string; credits: string; balanced: boolean }; accounts: { code: string; name: string; type: string; balance: string }[]; transactions: { id: string; kind: string; reference: string | null; description: string; created_at: string; entries: { account: string; direction: string; amount: string }[] }[] };
type R = Record<string, string | boolean | number | string[]>;

function Recon() {
  const { data } = useApi<R>("/admin/reconciliation");
  if (!data) return <PageLoader />;
  const issues = (data.missing_funding_entries as string[]).length + (data.missing_settlement_entries as string[]).length + (data.paid_orders_not_funded as string[]).length + Number(data.webhooks_with_errors);
  return (
    <Alert tone={issues === 0 && data.ledger_balanced && data.obligations_match_open_escrow ? "good" : "bad"} title="Reconciliation">
      Ledger balanced: <b>{String(data.ledger_balanced)}</b> · Escrow obligations {naira(String(data.escrow_obligations_ledger))} vs open escrow {naira(String(data.open_escrow_value))} (<b>{data.obligations_match_open_escrow ? "match" : "MISMATCH"}</b>) ·
      Missing funding entries: {(data.missing_funding_entries as string[]).join(", ") || "none"} · Missing settlements: {(data.missing_settlement_entries as string[]).join(", ") || "none"} ·
      Paid but unfunded orders: {(data.paid_orders_not_funded as string[]).join(", ") || "none"} · Webhooks with errors: {String(data.webhooks_with_errors)}
    </Alert>
  );
}

function Ledger() {
  const { data } = useApi<L>("/admin/ledger");
  if (!data) return <PageLoader />;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div className="card overflow-x-auto p-4">
        <h2 className="mb-2 font-semibold">Accounts <span className="text-xs font-normal text-muted">(debits {naira(data.trial_balance.debits)} = credits {naira(data.trial_balance.credits)})</span></h2>
        <table className="w-full text-sm"><tbody>{data.accounts.map((a) => <tr key={a.code} className="border-b border-line/60"><td className="py-1.5 font-mono text-xs">{a.code}</td><td className="text-xs text-muted">{a.type}</td><td className="text-right font-semibold">{naira(a.balance, { kobo: true })}</td></tr>)}</tbody></table>
      </div>
      <div className="card max-h-[480px] overflow-y-auto p-4">
        <h2 className="mb-2 font-semibold">Recent journal entries</h2>
        {data.transactions.map((t) => (
          <div key={t.id} className="border-b border-line/60 py-2 text-xs">
            <p className="font-semibold">{t.kind} · {t.reference} <span className="font-normal text-muted">{date(t.created_at, true)}</span></p>
            {t.entries.map((e, i) => <p key={i} className="font-mono">{e.direction === "debit" ? "DR" : "   CR"} {e.account} {naira(e.amount, { kobo: true })}</p>)}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Page() {
  const [status, setStatus] = useState("");
  return (
    <div className="space-y-4">
      <AdminPageHeader icon={Landmark} title="Escrow & ledger" description="Money held for protected orders, reconciled against the double-entry ledger." />
      <Recon />
      <AdminTable<E> path="/admin/escrow" query={{ status: status || undefined }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["pending_payment", "awaiting_seller", "processing", "dispatched", "awaiting_buyer_confirmation", "disputed", "refund_pending", "completed", "refunded", "cancelled"].map((s) => ({ value: s, label: titleCase(s) }))]} />} columns={[
        { key: "o", label: "Order", render: (e) => <><Link href={`/orders/${e.order_id}`} className="font-mono text-brand-700">{e.order_number}</Link><p className="font-mono text-[10px] text-muted">{e.provider}:{e.provider_escrow_ref ?? "—"}</p></> },
        { key: "s", label: "Status", render: (e) => <StatusBadge status={e.status} /> },
        { key: "a", label: "Held", render: (e) => naira(e.amount) },
        { key: "sp", label: "Seller / Platform", render: (e) => <span className="text-xs">{naira(e.seller_amount)} / {naira(e.platform_amount)}</span> },
        { key: "f", label: "Funded", render: (e) => date(e.funded_at, true) },
        { key: "r", label: "Auto-release", render: (e) => date(e.release_eligible_at, true) },
        { key: "x", label: "Settled", render: (e) => (e.released_at ? `Released ${date(e.released_at)}` : e.refunded_at ? `Refunded ${date(e.refunded_at)}` : "—") },
      ]} />
      <Ledger />
    </div>
  );
}
