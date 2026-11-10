"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { BadgeCheck, Crown, ExternalLink, Store } from "lucide-react";
import { AdminPageHeader, StatusBadge, askValue, askReason } from "@/components/admin-ui";
import { Alert, Badge, Button, PageLoader, Stat, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useAdminBase } from "@/lib/admin-area";
import { date, naira, titleCase } from "@/lib/format";
import { useApi } from "@/lib/hooks";

type Seller = {
  id: string; store_name: string; slug: string; description: string | null; logo_url: string | null;
  banner_url: string | null; state: string | null; city: string | null; address: string | null;
  business_phone: string | null; whatsapp_number: string | null; website: string | null;
  business_hours: string | null; verification_level: string; rating_avg: string; rating_count: number;
  completed_sales: number; is_suspended: boolean; payouts_frozen: boolean; created_at: string;
  owner: { full_name: string; email: string; phone: string | null; email_verified: boolean; phone_verified: boolean };
  is_premium: boolean;
};
type Wallet = {
  available: string; clearing: string; in_escrow: string; on_hold: string; pending_payouts: string;
  withdrawn: string; payouts_frozen: boolean;
  bank_accounts: { id: string; bank_name: string; account_name: string; account_last4: string; is_default: boolean }[];
  payouts: { id: string; amount: string; status: string; requested_at: string; paid_at: string | null; bank_account: { bank_name: string; account_last4: string } | null }[];
  holds: { id: string; amount: string; reason: string; created_at: string }[];
};
type D = {
  seller: Seller;
  subscription: { plan: string; plan_code: string; current_period_end: string } | null;
  stats: Record<string, number | string>;
  listings: { id: string; title: string; slug: string; price: string; status: string; quantity: number; views_count: number; thumb_url: string | null; created_at: string }[];
  orders: { id: string; order_number: string; status: string; payment_method: string; total: string; seller_amount: string; created_at: string }[];
  verifications: { id: string; level_requested: string; status: string; document_type: string; business_name: string | null; created_at: string; reviewed_at: string | null }[];
  wallet: Wallet | null;
};

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, error, reload } = useApi<D>(`/admin/sellers/${id}`);
  const toast = useToast();
  const base = useAdminBase();
  const link = (path: string) => `${base}${path}`;
  const [busy, setBusy] = useState(false);

  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!data) return <PageLoader />;
  const s = data.seller;
  const st = data.stats;

  async function suspend() {
    const reason = await askReason(s.is_suspended ? `Reinstate ${s.store_name}?` : `Suspend ${s.store_name}?`, 3, {
      message: s.is_suspended ? "Their listings become visible again." : "Their listings are hidden and they can’t sell until reinstated.",
      confirmLabel: s.is_suspended ? "Reinstate" : "Suspend seller", tone: s.is_suspended ? "default" : "danger",
    });
    if (!reason) return;
    setBusy(true);
    try { await http.post(`/admin/sellers/${s.id}/suspend`, { suspended: !s.is_suspended, reason }); toast("Updated"); reload(); }
    catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
  }

  async function grantPremium() {
    const reason = await askReason("Reason for granting premium (e.g. promotion, compensation):", 5);
    if (!reason) return;
    const days = Number(await askValue("How many days of Premium?", { label: "Days", type: "number", initial: "30" }, { confirmLabel: "Grant Premium" }));
    if (!days) return;
    setBusy(true);
    try { await http.post("/admin/subscriptions/grant", { seller_id: s.id, plan_code: "premium_monthly", days, reason }); toast("Premium granted"); reload(); }
    catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
  }

  return (
    <>
      <AdminPageHeader
        icon={Store}
        title={s.store_name}
        description={<>{s.owner.full_name} · {s.owner.email} · {s.city}, {s.state} · joined {date(s.created_at)}</>}
        actions={<>
          <Link href={`/store/${s.slug}`} className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-2 text-sm font-semibold hover:bg-canvas"><ExternalLink className="size-4" />Public store</Link>
          <Button size="sm" variant="outline" loading={busy} onClick={grantPremium}><Crown className="size-4" />Grant Premium</Button>
          <Button size="sm" variant={s.is_suspended ? "secondary" : "danger"} loading={busy} onClick={suspend}>{s.is_suspended ? "Reinstate" : "Suspend"}</Button>
        </>}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Badge tone={s.is_suspended ? "bad" : "good"}>{s.is_suspended ? "Suspended" : "Active"}</Badge>
        <Badge tone="neutral"><BadgeCheck className="mr-1 size-3.5" />{titleCase(s.verification_level)}</Badge>
        {s.is_premium && <Badge tone="premium"><Crown className="mr-1 size-3.5" />Premium</Badge>}
        {s.payouts_frozen && <Badge tone="warn">Payouts frozen</Badge>}
        {s.owner.email_verified && s.owner.phone_verified ? <Badge tone="good">Email + phone verified</Badge> : <Badge tone="warn">Verification incomplete</Badge>}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Listings" value={`${st.active_listings} active`} hint={`${st.total_listings} total · ${st.images_used}/${st.images_limit} photo slots`} />
        <Stat label="Views" value={Number(st.product_views).toLocaleString()} hint={`${st.enquiries} enquiries · ${st.contact_clicks} contact clicks`} />
        <Stat label="Orders" value={st.completed_orders} hint={`${st.pending_orders} pending · ${st.orders_in_transit} in transit`} />
        <Stat label="Completed sales" value={naira(String(st.revenue_completed))} hint={`${st.protected_sales} paid protected orders`} />
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-3">
        <section className="card p-4 lg:col-span-2">
          <h2 className="font-semibold">Store profile</h2>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-2">
            <div><dt className="text-xs text-muted">Owner</dt><dd className="font-medium">{s.owner.full_name}</dd></div>
            <div><dt className="text-xs text-muted">Contact</dt><dd>{s.owner.phone ?? "—"} · {s.owner.email}</dd></div>
            <div><dt className="text-xs text-muted">Location</dt><dd>{s.address ? `${s.address}, ` : ""}{s.city}, {s.state}</dd></div>
            <div><dt className="text-xs text-muted">Rating</dt><dd>{Number(s.rating_avg).toFixed(1)} ({s.rating_count}) · {s.completed_sales} completed sales</dd></div>
            <div><dt className="text-xs text-muted">Business hours</dt><dd>{s.business_hours ?? "—"}</dd></div>
            <div><dt className="text-xs text-muted">Website</dt><dd>{s.website ? <a className="text-brand-700 underline" href={s.website} target="_blank" rel="noopener noreferrer">{s.website}</a> : "—"}</dd></div>
            <div><dt className="text-xs text-muted">Subscription</dt><dd>{data.subscription ? `${data.subscription.plan} · until ${date(data.subscription.current_period_end)}` : "No active plan"}</dd></div>
            <div><dt className="text-xs text-muted">Open negotiations</dt><dd>{st.open_negotiations} · {st.conversations} conversations</dd></div>
          </dl>
          {s.description && <p className="mt-3 text-sm text-ink/80">{s.description}</p>}
        </section>

        <section className="card p-4">
          <h2 className="font-semibold">Verification history</h2>
          {data.verifications.length ? (
            <ul className="mt-3 space-y-2 text-sm">
              {data.verifications.map((v) => (
                <li key={v.id} className="rounded-lg border border-line p-2.5">
                  <div className="flex items-center justify-between gap-2"><b>{titleCase(v.level_requested)}</b><StatusBadge status={v.status} /></div>
                  <p className="mt-1 text-xs text-muted">{titleCase(v.document_type)} · {date(v.created_at, true)}</p>
                </li>
              ))}
            </ul>
          ) : <p className="mt-3 text-sm text-muted">No verification requests yet.</p>}
          <Link href={link("/verifications")} className="mt-3 inline-block text-sm font-semibold text-brand-700 hover:underline">Open verification queue</Link>
        </section>
      </div>

      {data.wallet && (
        <section className="card mt-5 p-4">
          <h2 className="font-semibold">Wallet &amp; payouts</h2>
          <div className="mt-3 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <Stat label="Available" value={naira(data.wallet.available)} />
            <Stat label="Clearing" value={naira(data.wallet.clearing)} />
            <Stat label="In escrow" value={naira(data.wallet.in_escrow)} />
            <Stat label="On hold" value={naira(data.wallet.on_hold)} />
            <Stat label="Pending payouts" value={naira(data.wallet.pending_payouts)} />
            <Stat label="Withdrawn" value={naira(data.wallet.withdrawn)} />
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <div>
              <h3 className="text-sm font-semibold">Bank accounts</h3>
              {data.wallet.bank_accounts.length ? (
                <ul className="mt-2 space-y-1.5 text-sm">
                  {data.wallet.bank_accounts.map((a) => <li key={a.id}>{a.bank_name} ·••{a.account_last4} — {a.account_name}{a.is_default ? " (default)" : ""}</li>)}
                </ul>
              ) : <p className="mt-2 text-sm text-muted">No bank account saved.</p>}
            </div>
            <div>
              <h3 className="text-sm font-semibold">Open holds</h3>
              {data.wallet.holds.length ? (
                <ul className="mt-2 space-y-1.5 text-sm">
                  {data.wallet.holds.map((h) => <li key={h.id}>{naira(h.amount)} · {h.reason === "bnpl_instalment" ? "Goods Flex instalment" : h.reason.replace(/_/g, " ")}</li>)}
                </ul>
              ) : <p className="mt-2 text-sm text-muted">No open holds.</p>}
            </div>
          </div>
          {data.wallet.payouts.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <h3 className="text-sm font-semibold">Recent payouts</h3>
              <table className="mt-2 w-full min-w-[520px] text-sm">
                <thead><tr className="border-b border-line text-left text-muted"><th className="p-2">Requested</th><th className="p-2">Amount</th><th className="p-2">Bank</th><th className="p-2">Status</th><th className="p-2">Paid</th></tr></thead>
                <tbody>{data.wallet.payouts.map((p) => (
                  <tr key={p.id} className="border-b border-line/60">
                    <td className="p-2">{date(p.requested_at, true)}</td><td className="p-2">{naira(p.amount)}</td>
                    <td className="p-2">{p.bank_account ? `${p.bank_account.bank_name} ·••${p.bank_account.account_last4}` : "—"}</td>
                    <td className="p-2">{titleCase(p.status)}</td><td className="p-2">{p.paid_at ? date(p.paid_at, true) : "—"}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
          <Link href={link("/payouts")} className="mt-3 inline-block text-sm font-semibold text-brand-700 hover:underline">Open payout queue</Link>
        </section>
      )}

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <section className="card overflow-x-auto p-4">
          <h2 className="font-semibold">Recent listings</h2>
          <table className="mt-2 w-full min-w-[420px] text-sm">
            <thead><tr className="border-b border-line text-left text-muted"><th className="p-2">Listing</th><th className="p-2">Price</th><th className="p-2">Status</th><th className="p-2">Views</th></tr></thead>
            <tbody>{data.listings.map((p) => (
              <tr key={p.id} className="border-b border-line/60">
                <td className="max-w-[240px] p-2"><Link href={`/item/${p.slug}`} className="block truncate text-brand-700 hover:underline">{p.title}</Link></td>
                <td className="p-2">{naira(p.price)}</td><td className="p-2"><StatusBadge status={p.status} /></td><td className="p-2">{p.views_count}</td>
              </tr>
            ))}</tbody>
          </table>
        </section>

        <section className="card overflow-x-auto p-4">
          <h2 className="font-semibold">Recent orders</h2>
          <table className="mt-2 w-full min-w-[420px] text-sm">
            <thead><tr className="border-b border-line text-left text-muted"><th className="p-2">Order</th><th className="p-2">Total</th><th className="p-2">Seller net</th><th className="p-2">Status</th></tr></thead>
            <tbody>{data.orders.map((o) => (
              <tr key={o.id} className="border-b border-line/60">
                <td className="p-2"><span className="font-mono text-brand-700">{o.order_number}</span>{o.payment_method === "bnpl" && <Badge tone="info" className="ml-1">Flex</Badge>}</td>
                <td className="p-2">{naira(o.total)}</td><td className="p-2">{naira(o.seller_amount)}</td><td className="p-2"><StatusBadge status={o.status} /></td>
              </tr>
            ))}</tbody>
          </table>
        </section>
      </div>
    </>
  );
}
