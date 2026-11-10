"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, Button, Input, PageLoader, Select, Stat, useToast } from "@/components/ui";
import { errorMessage, http } from "@/lib/api";
import { date, naira } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import { BANK_GROUPS, findBank, NG_BANKS } from "@/lib/ng-banks";
import type { Money } from "@/lib/types";

type BankAccount = { id: string; bank_code: string; bank_name: string; account_last4: string; account_name: string; is_default: boolean; is_verified: boolean };
type Payout = { id: string; amount: Money; fee: Money; status: string; provider_reference: string | null; requested_at: string; paid_at: string | null; failed_at: string | null; failure_reason: string | null; bank_account: { bank_name: string; account_last4: string } | null };
type Hold = { id: string; order_id: string | null; amount: Money; reason: string; note: string | null; created_at: string };
type Wallet = {
  available: Money; clearing: Money; in_escrow: Money; on_hold: Money; pending_payouts: Money; withdrawn: Money;
  payouts_frozen: boolean; hold_hours: number; min_payout: Money; note: string;
  bank_accounts: BankAccount[]; holds: Hold[]; payouts: Payout[];
};

const PAYOUT_STATUS: Record<string, string> = { requested: "Awaiting review", approved: "Approved", processing: "Processing", paid: "Paid", failed: "Failed", rejected: "Rejected", cancelled: "Cancelled" };

function View() {
  const { data, error, reload } = useApi<Wallet>("/seller/wallet");
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [acct, setAcct] = useState({ bank_code: "", account_name: "", account_number: "" });
  const [amount, setAmount] = useState("");
  const [bankId, setBankId] = useState("");

  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!data) return <PageLoader />;

  const defaultAccount = data.bank_accounts.find((a) => a.is_default) ?? data.bank_accounts[0];
  const selectedBank = bankId || defaultAccount?.id || "";

  async function addAccount(e: React.FormEvent) {
    e.preventDefault();
    const bank = findBank(acct.bank_code);
    if (!bank) return toast("Choose your bank from the list", "bad");
    setBusy(true);
    try {
      await http.post("/seller/bank-accounts", { bank_name: bank.name, bank_code: bank.code,
        account_name: acct.account_name, account_number: acct.account_number,
        is_default: !data!.bank_accounts.length });
      toast("Bank account saved");
      setAcct({ bank_code: "", account_name: "", account_number: "" });
      reload();
    } catch (err) {
      toast(errorMessage(err), "bad");
    } finally {
      setBusy(false);
    }
  }

  async function removeAccount(id: string) {
    if (!confirm("Remove this bank account?")) return;
    setBusy(true);
    try {
      await http.del(`/seller/bank-accounts/${id}`);
      toast("Bank account removed");
      setBankId("");
      reload();
    } catch (err) {
      toast(errorMessage(err), "bad");
    } finally {
      setBusy(false);
    }
  }

  async function withdraw(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedBank) return toast("Add a bank account first", "bad");
    if (!confirm("Your withdrawal will be sent to your bank. Please allow at least 24 hours for the money to land in your account. Continue?")) return;
    setBusy(true);
    try {
      await http.post("/seller/payouts", { amount, bank_account_id: selectedBank },
        { "Idempotency-Key": crypto.randomUUID() });
      toast("Withdrawal requested — an administrator will review it before payment");
      setAmount("");
      reload();
    } catch (err) {
      toast(errorMessage(err), "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-5">
      {data.payouts_frozen && (
        <Alert tone="warn" title="Withdrawals paused">
          A buyer complaint is under review. Your released funds are safe; payouts resume once support resolves the complaint.
        </Alert>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Available to withdraw" value={naira(data.available)} hint={`Cleared after ${data.hold_hours}h`} />
        <Stat label="Clearing" value={naira(data.clearing)} hint="Buyer complaint window" />
        <Stat label="Held in escrow" value={naira(data.in_escrow)} hint="Until buyers confirm delivery" />
        <Stat label="On hold" value={naira(data.on_hold)} hint="Open complaints or reserves" />
      </div>

      <p className="text-sm text-muted">{data.note}</p>

      <div className="grid gap-4 lg:grid-cols-2">
        <form onSubmit={withdraw} className="card space-y-3 p-4">
          <h2 className="font-semibold">Withdraw to your bank</h2>
          <div className="rounded-lg bg-canvas p-3 text-sm">
            <span className="text-muted">Available now</span>
            <p className="text-xl font-bold">{naira(data.available)}</p>
            <p className="text-xs text-muted">Pending payouts: {naira(data.pending_payouts)} · Withdrawn: {naira(data.withdrawn)}</p>
          </div>
          {data.bank_accounts.length ? (
            <Select label="Bank account" value={selectedBank} onChange={(e) => setBankId(e.target.value)} required>
              {data.bank_accounts.map((a) => (
                <option key={a.id} value={a.id}>{a.bank_name} ·••{a.account_last4}{a.is_default ? " (default)" : ""}</option>
              ))}
            </Select>
          ) : (
            <Alert tone="info">Add a bank account to receive payouts.</Alert>
          )}
          <Input label="Amount (₦)" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value)}
            placeholder={data.min_payout} hint={`Minimum ${naira(data.min_payout)}`} />
          <Button type="submit" block loading={busy} disabled={data.payouts_frozen || !data.bank_accounts.length || !amount}>
            Request withdrawal
          </Button>
          <Alert tone="info">
            Withdrawals are paid by our licensed payout partner. After a withdrawal is initiated,
            <b> it takes at least 24 hours for the money to land in your bank account</b>. A rejected or failed transfer returns
            the funds to your available balance.
          </Alert>
        </form>

        <div className="card space-y-3 p-4">
          <h2 className="font-semibold">Bank accounts</h2>
          {data.bank_accounts.length ? (
            <ul className="space-y-2">
              {data.bank_accounts.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-2 rounded-lg border border-line p-2.5 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{a.bank_name} ·••{a.account_last4} {a.is_default && <span className="text-xs text-brand-700">Default</span>}</p>
                    <p className="truncate text-xs text-muted">{a.account_name} · {a.is_verified ? "Verified" : "Pending verification"}</p>
                  </div>
                  <Button variant="ghost" size="sm" disabled={busy} onClick={() => removeAccount(a.id)}>Remove</Button>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-muted">No bank account yet.</p>}
          <form onSubmit={addAccount} className="space-y-2 border-t border-line pt-3">
            <Select label="Bank name" value={acct.bank_code} onChange={(e) => setAcct({ ...acct, bank_code: e.target.value })} required>
              <option value="">Select your bank</option>
              {BANK_GROUPS.map((group) => (
                <optgroup key={group} label={group}>
                  {NG_BANKS.filter((b) => b.group === group).map((b) => (
                    <option key={b.code} value={b.code}>{b.name}</option>
                  ))}
                </optgroup>
              ))}
            </Select>
            <Input label="Account name" placeholder="Okafor Phones Hub" value={acct.account_name} onChange={(e) => setAcct({ ...acct, account_name: e.target.value })} required />
            <Input label="Account number" inputMode="numeric" placeholder="0123456789" value={acct.account_number} onChange={(e) => setAcct({ ...acct, account_number: e.target.value })} required />
            <p className="text-xs text-muted">The account name must be your business name, or the business owner&apos;s name exactly as shown on your verification documents.</p>
            <Button type="submit" variant="outline" block loading={busy} disabled={!acct.bank_code || !acct.account_name || acct.account_number.length < 10}>
              Add bank account
            </Button>
          </form>
        </div>
      </div>

      {data.holds.length > 0 && (
        <div className="card p-4">
          <h2 className="font-semibold">Open holds</h2>
          <ul className="mt-2 space-y-2 text-sm">
            {data.holds.map((h) => (
              <li key={h.id} className="flex items-center justify-between gap-2 rounded-lg border border-amber-200 bg-amber-50 p-2.5">
                <span>{naira(h.amount)} · {h.reason.replace(/_/g, " ")}</span>
                <span className="text-xs text-muted">{date(h.created_at, true)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card overflow-x-auto">
        <h2 className="p-4 pb-0 font-semibold">Payout history</h2>
        <table className="mt-3 w-full min-w-[560px] text-sm">
          <thead><tr className="border-b border-line text-left text-muted"><th className="p-3">Requested</th><th className="p-3">Amount</th><th className="p-3">Bank</th><th className="p-3">Status</th><th className="p-3">Paid</th></tr></thead>
          <tbody>
            {data.payouts.map((p) => (
              <tr key={p.id} className="border-b border-line/60">
                <td className="p-3">{date(p.requested_at, true)}</td>
                <td className="p-3 font-semibold">{naira(p.amount)}</td>
                <td className="p-3">{p.bank_account ? `${p.bank_account.bank_name} ·••${p.bank_account.account_last4}` : "—"}</td>
                <td className="p-3">{PAYOUT_STATUS[p.status] ?? p.status}{p.failure_reason && <span className="block text-xs text-red-600">{p.failure_reason}</span>}</td>
                <td className="p-3">{p.paid_at ? date(p.paid_at, true) : "—"}</td>
              </tr>
            ))}
            {!data.payouts.length && <tr><td colSpan={5} className="p-6 text-center text-muted">No withdrawals yet.</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Wallet</h1><View /></>}</RequireAuth>;
}
