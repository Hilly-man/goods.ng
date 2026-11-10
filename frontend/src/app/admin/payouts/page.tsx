"use client";

import { Banknote } from "lucide-react";
import { useState } from "react";
import { AdminPageHeader, FilterChips, StatusBadge, confirmAction } from "@/components/admin-ui";
import { AdminTable, askReason } from "@/components/admin-table";
import { Button, useToast } from "@/components/ui";
import { errorMessage, http } from "@/lib/api";
import { date, naira, titleCase } from "@/lib/format";

type P = {
  id: string; amount: string; fee: string; status: string; seller_name: string | null;
  bank_account: { bank_name: string; account_name: string; account_last4: string } | null;
  provider_reference: string | null; requested_at: string; reviewed_at: string | null;
  review_note: string | null; paid_at: string | null; failure_reason: string | null;
};

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("requested");
  return (
    <>
      <AdminPageHeader icon={Banknote} title="Seller payouts" description={<>Withdrawals must be reviewed and approved by a staff member with <b>payouts.approve</b> before the payout partner sends money. Check the account name against the seller&apos;s verified business or owner name.</>} />
      <AdminTable<P>
        path="/admin/payouts"
        query={{ status: status || undefined }}
        filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "", label: "All" }, ...["requested", "approved", "processing", "paid", "failed", "rejected"].map((s) => ({ value: s, label: titleCase(s) }))]} />}
        columns={[
          { key: "s", label: "Seller", render: (p) => <b>{p.seller_name ?? "—"}</b> },
          { key: "a", label: "Amount", render: (p) => <b>{naira(p.amount)}</b> },
          { key: "b", label: "Bank", render: (p) => p.bank_account ? (<><p>{p.bank_account.bank_name} ·••{p.bank_account.account_last4}</p><p className="text-xs text-muted">{p.bank_account.account_name}</p></>) : "—" },
          { key: "st", label: "Status", render: (p) => <><StatusBadge status={p.status} />{p.review_note && <p className="mt-1 max-w-xs text-xs text-red-600">{p.review_note}</p>}{p.failure_reason && <p className="mt-1 max-w-xs text-xs text-red-600">{p.failure_reason}</p>}</> },
          { key: "t", label: "Requested", render: (p) => date(p.requested_at, true) },
        ]}
        actions={(p, reload) => {
          if (p.status === "requested") return (<>
            <Button size="sm" onClick={async () => {
              if (!(await confirmAction({ title: `Approve ${naira(p.amount)} payout?`, message: "Confirm the bank account name matches the seller's verified business or owner name. The payout partner will send the money after approval.", confirmLabel: "Approve payout" }))) return;
              try { await http.post(`/admin/payouts/${p.id}/approve`); toast("Payout approved for processing"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
            }}>Approve</Button>
            <Button size="sm" variant="danger" onClick={async () => {
              const reason = await askReason("Reason for rejecting this withdrawal:", 5);
              if (!reason) return;
              try { await http.post(`/admin/payouts/${p.id}/reject`, { reason }); toast("Withdrawal rejected"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
            }}>Reject</Button>
          </>);
          if (p.status === "failed") {
            return <Button size="sm" variant="outline" onClick={async () => {
              try { await http.post(`/admin/payouts/${p.id}/retry`); toast("Payout queued for retry"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
            }}>Retry</Button>;
          }
          return null;
        }}
      />
    </>
  );
}
