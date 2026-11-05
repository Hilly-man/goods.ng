"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, use, useEffect, useMemo, useState } from "react";
import { CalendarClock, Lock, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { RequireAuth } from "@/components/require-auth";
import { Alert, Button, Checkbox, Input, PageLoader, Textarea } from "@/components/ui";
import { ProductThumb } from "@/components/product-card";
import { http, errorMessage, ApiError } from "@/lib/api";
import { naira } from "@/lib/format";
import { StateCitySelect } from "@/components/state-city-select";
import type { FlexStatus } from "@/components/flex-setup";
import type { FinancingOption, ProductDetail, User } from "@/lib/types";

type Quote = { unit_price: string; listed_price: string; quantity: number; subtotal: string; delivery_fee: string; protection_fee: string; total: string; negotiated: boolean; seller: { store_name: string } };

function Checkout({ slug, user }: { slug: string; user: User }) {
  const sp = useSearchParams();
  const router = useRouter();
  const negotiationId = sp.get("negotiation") ?? undefined;
  const [flex, setFlex] = useState(sp.get("flex") === "1");
  const [p, setP] = useState<ProductDetail | null>(null);
  const [delivery, setDelivery] = useState(0);
  const [qty, setQty] = useState(1);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [quoteErr, setQuoteErr] = useState<string | null>(null);
  const [addr, setAddr] = useState({ full_name: user.full_name, phone: user.phone ?? "", state: user.state ?? "", city: user.city ?? "", street: "", landmark: "" });
  const [note, setNote] = useState("");
  const [options, setOptions] = useState<FinancingOption[]>([]);
  const [tenor, setTenor] = useState(3);
  const [flexStatus, setFlexStatus] = useState<FlexStatus | null>(null);
  const [consent, setConsent] = useState(false);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // One idempotency key per checkout attempt: double taps / retries never create two orders.
  const idemKey = useMemo(() => crypto.randomUUID(), []);

  useEffect(() => { http.get<ProductDetail>(`/products/${slug}`).then(setP).catch((e) => setErr(errorMessage(e))); }, [slug]);
  useEffect(() => {
    if (!p) return;
    http.post<Quote>("/checkout/quote", { product_id: p.id, quantity: qty, negotiation_id: negotiationId, delivery_option_index: delivery })
      .then((q) => { setQuote(q); setQuoteErr(null); })
      .catch((e) => { setQuote(null); setQuoteErr(errorMessage(e)); });
  }, [p, qty, delivery, negotiationId]);
  useEffect(() => {
    if (!p?.bnpl_enabled || !quote) return;
    http.get<{ options: FinancingOption[] }>("/bnpl/quote", { product_id: p.id, amount: quote.total }).then((r) => setOptions(r.options)).catch(() => {});
  }, [p, quote]);
  useEffect(() => {
    if (!flex) return;
    http.get<FlexStatus>("/bnpl/profile").then(setFlexStatus).catch(() => setFlexStatus(null));
  }, [flex]);

  if (!p) return err ? <Alert tone="bad">{err}</Alert> : <PageLoader />;
  const option = options.find((o) => o.tenor_months === tenor);
  const flexLimit = flexStatus ? Number(flexStatus.credit_limit) : null;
  const flexRunning = Boolean(flexStatus?.running_plan);
  const flexNotReady = flexLimit !== null && !flexRunning && flexLimit <= 0;
  const flexOverLimit = Boolean(flexLimit !== null && quote && !flexRunning && Number(quote.total) > flexLimit);
  const flexBlocked = flexRunning || flexNotReady || flexOverLimit;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setErrs({}); setBusy(true);
    const address = { ...addr, landmark: addr.landmark || undefined };
    try {
      if (flex) {
        const a = await http.post<{ id: string; status: string }>("/bnpl/applications", {
          product_id: p!.id, quantity: qty, negotiation_id: negotiationId, delivery_option_index: delivery, address, note: note || undefined,
          tenor_months: tenor, consent,
        }, { "Idempotency-Key": idemKey });
        router.push(`/flex/applications/${a.id}`);
      } else {
        const r = await http.post<{ order_id: string; authorization_url: string | null }>("/checkout", {
          product_id: p!.id, quantity: qty, negotiation_id: negotiationId, delivery_option_index: delivery, address, note: note || undefined,
        }, { "Idempotency-Key": idemKey });
        if (r.authorization_url) window.location.href = r.authorization_url;
        else router.push(`/orders/${r.order_id}`);
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        const fe = e.fieldErrors;
        setErrs(Object.fromEntries(Object.entries(fe).map(([k, v]) => [k.replace("address.", ""), v])));
        setErr("Please check the highlighted fields.");
      } else setErr(errorMessage(e));
      setBusy(false);
    }
  }

  const set = (k: keyof typeof addr) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setAddr({ ...addr, [k]: e.target.value });
  return (
    <form onSubmit={submit} className="grid gap-5 lg:grid-cols-[1fr_380px]">
      <div className="space-y-4">
        {p.bnpl_enabled && (
          <div className="card grid grid-cols-2 gap-1 p-1">
            <button type="button" onClick={() => setFlex(false)} className={clsx("rounded-lg p-3 text-sm font-semibold", !flex ? "bg-brand-700 text-white" : "text-muted")}><ShieldCheck className="mr-1 inline size-4" />Pay in full</button>
            <button type="button" onClick={() => setFlex(true)} className={clsx("rounded-lg p-3 text-sm font-semibold", flex ? "bg-violet-700 text-white" : "text-muted")}><CalendarClock className="mr-1 inline size-4" />Goods Flex</button>
          </div>
        )}
        <section className="card p-4 sm:p-5">
          <h2 className="font-semibold">Delivery</h2>
          <div className="mt-3 space-y-2">
            {p.delivery_options.map((o, i) => (
              <label key={i} className={clsx("flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm", delivery === i ? "border-brand-600 bg-brand-50" : "border-line")}>
                <input type="radio" name="delivery" checked={delivery === i} onChange={() => setDelivery(i)} className="accent-brand-700" />
                <span className="flex-1">{o.label}<span className="block text-xs text-muted">{o.eta_days ? `~${o.eta_days} day(s)` : "Same day"}</span></span>
                <span className="font-semibold">{Number(o.fee) ? naira(o.fee) : "Free"}</span>
              </label>
            ))}
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Input label="Recipient name" required value={addr.full_name} onChange={set("full_name")} error={errs.full_name} />
            <Input label="Phone" type="tel" required value={addr.phone} onChange={set("phone")} error={errs.phone} />
            <StateCitySelect required state={addr.state} city={addr.city} errors={{ state: errs.state, city: errs.city }} onChange={(v) => setAddr({ ...addr, ...v })} />
            <div className="sm:col-span-2"><Input label="Street address" required value={addr.street} onChange={set("street")} error={errs.street} /></div>
            <div className="sm:col-span-2"><Input label="Landmark (optional)" value={addr.landmark} onChange={set("landmark")} /></div>
            <div className="sm:col-span-2"><Textarea label="Note to seller (optional)" rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} /></div>
          </div>
          <p className="mt-2 text-xs text-muted">Your address is only shared with the seller after your payment is confirmed.</p>
        </section>
        {flex && (
          <section className="card p-4 sm:p-5">
            <h2 className="font-semibold">Goods Flex plan</h2>
            {!user.phone_verified && <Alert tone="warn" className="mt-3" title="Verify your phone first">Goods Flex requires a verified phone number. <Link href="/account" className="underline">Verify now</Link></Alert>}
            {flexRunning ? (
              <Alert tone="warn" className="mt-3" title="One Goods Flex plan at a time">
                You already have a plan running. You can start another once it&apos;s fully paid.{" "}
                <Link href={flexStatus?.running_plan?.order_id ? `/orders/${flexStatus.running_plan.order_id}` : "/flex"} className="underline">View your plan</Link>
              </Alert>
            ) : flexNotReady ? (
              <Alert tone="warn" className="mt-3" title="Set up Goods Flex first">
                {!flexStatus?.steps.bank
                  ? "Connect your bank account so we can calculate your limit from your statement."
                  : flexStatus.steps.guarantor === "pending_consent"
                    ? "Your guarantor still needs to confirm by SMS."
                    : "You need a guarantor to consent before you can use Goods Flex."}{" "}
                <Link href="/flex" className="underline">Set up Goods Flex</Link>
              </Alert>
            ) : flexLimit !== null ? (
              <div className="mt-3 flex items-center justify-between rounded-xl bg-violet-50 p-3 text-sm text-violet-900">
                <span>Your Goods Flex limit</span>
                <span className="font-bold">{naira(flexStatus!.credit_limit)}</span>
              </div>
            ) : null}
            {flexOverLimit && (
              <Alert tone="bad" className="mt-3" title="Above your limit">
                This purchase ({naira(quote!.total)}) is above your limit of {naira(flexStatus!.credit_limit)}. Increase your limit on the{" "}
                <Link href="/flex" className="underline">Goods Flex page</Link>, or pay in full.
              </Alert>
            )}
            <div className="mt-3 grid grid-cols-2 gap-2">
              {options.map((o) => (
                <button type="button" key={o.tenor_months} onClick={() => setTenor(o.tenor_months)} className={clsx("rounded-xl border p-3 text-left", tenor === o.tenor_months ? "border-violet-600 bg-violet-50" : "border-line")}>
                  <span className="block text-sm font-semibold">{o.tenor_months} months</span>
                  <span className="block text-lg font-bold">{naira(o.monthly_installment)}<span className="text-xs font-normal text-muted">/mo</span></span>
                  <span className="text-xs text-muted">after {naira(o.down_payment)} today</span>
                </button>
              ))}
            </div>
            {option && <p className="mt-2 text-xs text-muted">Indicative: financing charge {naira(option.financing_charge)}, total {naira(option.total_payable)}. {option.apr_disclosure}</p>}
            <div className="mt-3"><Checkbox checked={consent} onChange={(e) => setConsent(e.target.checked)} label="I consent to Goods.ng sharing my application details with its licensed lending partner for a credit decision." /></div>
          </section>
        )}
      </div>
      <aside className="space-y-3 lg:sticky lg:top-20 lg:self-start">
        <div className="card p-4 sm:p-5">
          <div className="flex gap-3">
            <div className="size-16 shrink-0 overflow-hidden rounded-lg"><ProductThumb src={p.images[0]?.thumb_url ?? null} alt={p.title} categorySlug={p.category.slug} /></div>
            <div className="min-w-0"><p className="line-clamp-2 text-sm font-medium">{p.title}</p><p className="text-xs text-muted">Sold by {p.seller.store_name}</p></div>
          </div>
          {!negotiationId && p.quantity > 1 && (
            <label className="mt-3 flex items-center justify-between text-sm">Quantity
              <select value={qty} onChange={(e) => setQty(Number(e.target.value))} className="rounded-lg border border-line px-2 py-1">
                {Array.from({ length: Math.min(p.quantity, 10) }, (_, i) => i + 1).map((n) => <option key={n}>{n}</option>)}
              </select>
            </label>
          )}
          {quoteErr && <Alert tone="bad" className="mt-3">{quoteErr}</Alert>}
          {quote && (
            <dl className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between"><dt>Item{quote.quantity > 1 ? ` × ${quote.quantity}` : ""}</dt><dd>{naira(quote.subtotal)}</dd></div>
              {quote.negotiated && <div className="flex justify-between text-brand-700"><dt>Agreed offer price</dt><dd>was {naira(quote.listed_price)}</dd></div>}
              <div className="flex justify-between"><dt>Delivery</dt><dd>{Number(quote.delivery_fee) ? naira(quote.delivery_fee) : "Free"}</dd></div>
              <div className="flex justify-between"><dt>Buyer protection fee</dt><dd>{naira(quote.protection_fee)}</dd></div>
              <div className="flex justify-between border-t border-line pt-2 text-base font-bold"><dt>Total</dt><dd>{naira(quote.total)}</dd></div>
              {flex && option && <div className="flex justify-between rounded-lg bg-violet-50 p-2 font-semibold text-violet-900"><dt>Due today (down payment)</dt><dd>{naira(option.down_payment)}</dd></div>}
            </dl>
          )}
          {err && <Alert tone="bad" className="mt-3">{err}</Alert>}
          <Button type="submit" block size="lg" className="mt-4" loading={busy} disabled={!quote || (flex && (!consent || !user.phone_verified || flexBlocked))}>
            <Lock className="size-4" />{flex ? "Apply for Goods Flex" : quote ? `Pay ${naira(quote.total)} securely` : "Pay securely"}
          </Button>
          <p className="mt-3 flex gap-2 text-xs text-muted"><ShieldCheck className="size-4 shrink-0 text-brand-700" />Funds are held by our licensed escrow partner and released to the seller only after you confirm delivery.</p>
        </div>
      </aside>
    </form>
  );
}

function Inner({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  return (
    <RequireAuth>
      {(user) => (
        <div className="container-page max-w-5xl py-6">
          <h1 className="mb-4 text-2xl font-bold">Protected Checkout</h1>
          <Suspense fallback={<PageLoader />}><Checkout slug={slug} user={user} /></Suspense>
        </div>
      )}
    </RequireAuth>
  );
}

export default function Page(props: { params: Promise<{ slug: string }> }) {
  return (
    <Suspense fallback={<PageLoader />}>
      <Inner {...props} />
    </Suspense>
  );
}
