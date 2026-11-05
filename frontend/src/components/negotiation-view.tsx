"use client";

import Link from "next/link";
import { useState } from "react";
import { CalendarClock, Clock, MessageCircle, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import type { Negotiation } from "@/lib/types";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { date, naira, toMoneyString } from "@/lib/format";
import { Alert, Badge, Button, ButtonLink, Input, PageLoader, useToast } from "./ui";

const STATUS_TONE = { open: "info", accepted: "good", converted: "good", rejected: "bad", cancelled: "neutral", expired: "neutral" } as const;

export function NegotiationView({ id }: { id: string }) {
  const { data: n, setData, error } = useApi<Negotiation>(`/negotiations/${id}`);
  const [counter, setCounter] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const toast = useToast();
  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!n) return <PageLoader />;
  const pending = n.offers.find((o) => o.status === "pending");

  async function act(action: "accept" | "reject" | "counter") {
    if (!pending) return;
    let amount: string | undefined;
    if (action === "counter") {
      const m = toMoneyString(counter);
      if (!m) return toast("Enter a valid amount", "bad");
      amount = m;
    }
    setBusy(action);
    try {
      setData(await http.post<Negotiation>(`/negotiations/${n!.id}/respond`, { offer_id: pending.id, action, amount }));
      setCounter("");
      toast(action === "accept" ? "Offer accepted" : action === "reject" ? "Offer declined" : "Counteroffer sent");
    } catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(null); }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <div className="card p-4 sm:p-5">
        <div className="flex gap-3">
          <Link href={`/item/${n.product.slug}`} className="size-20 shrink-0 overflow-hidden rounded-lg bg-canvas">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {n.product.thumb_url && <img src={n.product.thumb_url} alt="" className="size-full object-cover" />}
          </Link>
          <div className="min-w-0">
            <Link href={`/item/${n.product.slug}`} className="font-semibold hover:text-brand-700">{n.product.title}</Link>
            <p className="text-sm text-muted">Listed at {naira(n.listed_price)} · {n.role === "buyer" ? n.seller.store_name : "Your listing"}</p>
            <Badge tone={STATUS_TONE[n.status]} className="mt-1.5 capitalize">{n.status}</Badge>
          </div>
        </div>
        <ol className="mt-5 space-y-3">
          {n.offers.map((o) => {
            const mine = o.made_by === n.role;
            return (
              <li key={o.id} className={clsx("flex", mine ? "justify-end" : "justify-start")}>
                <div className={clsx("rounded-2xl px-4 py-2.5", mine ? "bg-brand-700 text-white" : "bg-canvas")}>
                  <p className="text-xs opacity-80">{mine ? "You" : o.made_by === "buyer" ? "Buyer" : "Seller"} offered</p>
                  <p className="text-xl font-bold">{naira(o.amount)}</p>
                  {o.note && <p className="text-sm opacity-90">{o.note}</p>}
                  <p className="mt-0.5 text-[11px] capitalize opacity-75">{o.status}{o.status === "pending" && ` · expires ${date(o.expires_at, true)}`}</p>
                </div>
              </li>
            );
          })}
        </ol>
        {n.conversation_id && <Link href={`/messages/${n.conversation_id}`} className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-brand-700"><MessageCircle className="size-4" />Open chat</Link>}
      </div>
      <aside className="card h-fit space-y-3 p-4 sm:p-5">
        {n.status === "open" && pending && n.your_turn && (
          <>
            <p className="text-sm">The {pending.made_by} offered <strong>{naira(pending.amount)}</strong>.</p>
            <Button block loading={busy === "accept"} onClick={() => act("accept")}>Accept {naira(pending.amount)}</Button>
            <div className="flex gap-2">
              <div className="flex-1"><Input aria-label="Counteroffer amount" inputMode="numeric" placeholder="Counter (₦)" value={counter} onChange={(e) => setCounter(e.target.value)} /></div>
              <Button variant="secondary" loading={busy === "counter"} onClick={() => act("counter")}>Counter</Button>
            </div>
            <Button block variant="ghost" className="text-red-600" loading={busy === "reject"} onClick={() => act("reject")}>Decline</Button>
          </>
        )}
        {n.status === "open" && !n.your_turn && (
          <Alert tone="info" title={`Waiting for the ${n.awaiting}`}><Clock className="mr-1 inline size-4" />They have until the offer expires to respond.</Alert>
        )}
        {n.status === "open" && n.role === "buyer" && (
          <Button block variant="ghost" size="sm" onClick={async () => { try { setData(await http.post<Negotiation>(`/negotiations/${n.id}/withdraw`)); } catch (e) { toast(errorMessage(e), "bad"); } }}>Withdraw offer</Button>
        )}
        {n.status === "accepted" && n.role === "buyer" && (
          <>
            <Alert tone="good" title={`Agreed price: ${naira(n.agreed_price)}`}>Complete checkout by {date(n.checkout_expires_at, true)} to keep this price.</Alert>
            <ButtonLink href={`/checkout/${n.product.slug}?negotiation=${n.id}`} block size="lg"><ShieldCheck className="size-5" />Checkout at {naira(n.agreed_price)}</ButtonLink>
            {n.product.bnpl_enabled && <ButtonLink href={`/checkout/${n.product.slug}?negotiation=${n.id}&flex=1`} block variant="outline"><CalendarClock className="size-5" />Use Goods Flex</ButtonLink>}
          </>
        )}
        {n.status === "accepted" && n.role === "seller" && <Alert tone="good" title={`You accepted ${naira(n.agreed_price)}`}>Waiting for the buyer to pay through Protected Checkout. You&apos;ll be notified when it&apos;s funded.</Alert>}
        {n.status === "converted" && <Alert tone="good" title="Order placed">This offer was used for a protected order.</Alert>}
        {["rejected", "cancelled", "expired"].includes(n.status) && <Alert tone="info" title={`This negotiation is ${n.status}`}>{n.role === "buyer" ? "You can make a new offer from the listing page." : "The buyer can send a new offer."}</Alert>}
      </aside>
    </div>
  );
}

export function NegotiationList({ role }: { role: "buyer" | "seller" }) {
  const { data } = useApi<Negotiation[]>("/negotiations", { role });
  if (!data) return <PageLoader />;
  if (!data.length) return <p className="card p-8 text-center text-sm text-muted">No offers yet.</p>;
  const base = role === "buyer" ? "/offers" : "/seller/offers";
  return (
    <ul className="card divide-y divide-line">
      {data.map((n) => {
        const last = n.offers.at(-1);
        return (
          <li key={n.id}>
            <Link href={`${base}/${n.id}`} className="flex items-center gap-3 p-3 hover:bg-canvas">
              <span className="size-12 shrink-0 overflow-hidden rounded-lg bg-canvas">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {n.product.thumb_url && <img src={n.product.thumb_url} alt="" className="size-full object-cover" />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{n.product.title}</span>
                <span className="text-sm text-muted">Latest: {last ? naira(last.amount) : "—"} · listed {naira(n.listed_price)}</span>
              </span>
              <span className="flex flex-col items-end gap-1">
                <Badge tone={STATUS_TONE[n.status]} className="capitalize">{n.status}</Badge>
                {n.your_turn && <span className="text-xs font-semibold text-accent-600">Your turn</span>}
              </span>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
