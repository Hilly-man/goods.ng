"use client";

import { TrackEvent } from "./consent";
import Link from "next/link";
import { useState } from "react";
import { AlertTriangle, CheckCircle2, Circle, ImagePlus, PackageCheck, ShieldCheck, Star, Truck } from "lucide-react";
import clsx from "clsx";
import type { OrderDetail } from "@/lib/types";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { date, naira, ORDER_STATUS, titleCase } from "@/lib/format";
import { Alert, Badge, Button, Input, Modal, PageLoader, Select, Textarea, useToast } from "./ui";

const FLOW = ["pending_payment", "awaiting_seller", "processing", "dispatched", "awaiting_buyer_confirmation", "completed"] as const;
const FLOW_LABEL = ["Paid", "Accepted", "Preparing", "Dispatched", "Delivered", "Completed"];

export function StatusBadge({ status }: { status: OrderDetail["status"] }) {
  const s = ORDER_STATUS[status];
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

function Progress({ status }: { status: OrderDetail["status"] }) {
  const map: Record<string, number> = { pending_payment: 0, payment_confirmed: 1, funds_safeguarded: 1, awaiting_seller: 1, processing: 2, dispatched: 3, delivered: 4, awaiting_buyer_confirmation: 4, completed: 6 };
  const idx = map[status] ?? -1;
  if (idx < 0) return null;
  const done = Math.min(idx, FLOW.length);
  return (
    <div>
      <ol className="grid grid-cols-6 gap-1" aria-label={`Order progress: ${done} of ${FLOW.length} steps done`}>
        {FLOW.map((_, i) => (
          <li key={i} className="flex flex-col items-center gap-1 text-center">
            <span className={clsx("h-1.5 w-full rounded-full", i < idx ? "bg-brand-600" : "bg-line")} />
            {/* Six labels don't fit side by side on a phone; the summary line below replaces them there. */}
            <span className={clsx("hidden text-xs sm:block", i < idx ? "font-semibold text-brand-800" : "text-muted")}>{FLOW_LABEL[i]}</span>
          </li>
        ))}
      </ol>
      <p className="mt-1.5 text-xs text-muted sm:hidden">
        {done >= FLOW.length
          ? <span className="font-semibold text-brand-800">All {FLOW.length} steps done · Completed</span>
          : <><span className="font-semibold text-brand-800">{done} of {FLOW.length} done</span> · Next: {FLOW_LABEL[done]}</>}
      </p>
    </div>
  );
}

const DISPUTE_REASONS: Record<string, [string, string][]> = {
  buyer: [["not_received", "Item not received"], ["not_as_described", "Not as described"], ["damaged", "Item damaged"], ["wrong_item", "Wrong item"], ["seller_non_fulfilment", "Seller not fulfilling"], ["delivery_issue", "Delivery problem"], ["other", "Other"]],
  seller: [["buyer_refuses_confirmation", "Buyer won't confirm valid delivery"], ["fraudulent_claim", "False buyer claim"], ["other", "Other"]],
};

export function OrderView({ id, justPaid = false }: { id: string; justPaid?: boolean }) {
  const { data: o, setData, error } = useApi<OrderDetail>(`/orders/${id}`);
  const toast = useToast();
  const [modal, setModal] = useState<null | "dispatch" | "delivered" | "dispute" | "decline" | "cancel" | "review" | "update">(null);
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState<Record<string, string>>({});
  const [evidence, setEvidence] = useState<string[]>([]);
  const [rating, setRating] = useState(5);
  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!o) return <PageLoader />;

  async function run(path: string, body?: unknown, msg?: string) {
    setBusy(true);
    try {
      setData(await http.post<OrderDetail>(`/orders/${o!.id}/${path}`, body));
      setModal(null); setF({}); setEvidence([]);
      if (msg) toast(msg);
    } catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
  }
  async function upload(file: File) {
    const fd = new FormData(); fd.append("file", file);
    try { const r = await http.post<{ url: string }>(`/orders/${o!.id}/evidence`, fd); setEvidence((x) => [...x, r.url]); }
    catch (e) { toast(errorMessage(e), "bad"); }
  }
  const has = (a: string) => o.actions.includes(a);
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  const item = o.items[0];

  const EvidenceInput = (
    <div>
      <label className="chip cursor-pointer"><ImagePlus className="size-4" />Add photo<input type="file" accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} /></label>
      {evidence.length > 0 && <div className="mt-2 flex gap-2">{evidence.map((u) => /* eslint-disable-next-line @next/next/no-img-element */ <img key={u} src={u} alt="Evidence" className="size-14 rounded object-cover" />)}</div>}
    </div>
  );

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
      <div className="space-y-4">
        <section className="card p-4 sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><p className="text-xs text-muted">Order</p><p className="font-mono font-semibold">{o.order_number}</p></div>
            <div className="flex items-center gap-2">{o.payment_method === "bnpl" && <Badge tone="info">Goods Flex</Badge>}<StatusBadge status={o.status} /></div>
          </div>
          <div className="mt-4"><Progress status={o.status} /></div>
          <div className="mt-4 flex gap-3 border-t border-line pt-4">
            <span className="size-16 shrink-0 overflow-hidden rounded-lg bg-canvas">{/* eslint-disable-next-line @next/next/no-img-element */}{item.image_url && <img src={item.image_url} alt="" className="size-full object-cover" />}</span>
            <div className="min-w-0 flex-1"><p className="font-medium">{item.title}</p><p className="text-sm text-muted">{item.quantity} × {naira(item.unit_price)}{o.negotiated && <span className="ml-1 text-brand-700">(negotiated)</span>}</p>
              <p className="text-sm text-muted">{o.role === "buyer" ? <>Seller: <Link href={`/store/${o.seller.slug}`} className="text-brand-700">{o.seller.store_name}</Link></> : <>Buyer: {o.buyer.name}</>}</p></div>
          </div>
        </section>

        {o.status === "awaiting_buyer_confirmation" && o.role === "buyer" && (
          <Alert tone="warn" title="Please inspect your item and confirm">Funds release automatically to the seller on {date(o.escrow.release_eligible_at, true)} unless you report a problem.</Alert>
        )}
        {o.status === "disputed" && <Alert tone="bad" title="Dispute in progress">Funds stay safeguarded while Goods.ng reviews the evidence. Add messages and photos below.</Alert>}

        {o.delivery && (
          <section className="card p-4 sm:p-5">
            <h2 className="flex items-center gap-2 font-semibold"><Truck className="size-5 text-brand-700" />Delivery</h2>
            <p className="mt-1 text-sm">{o.delivery_option?.label} · {Number(o.delivery_fee) ? naira(o.delivery_fee) : "Free"}</p>
            {o.delivery.tracking_reference && <p className="mt-1 text-sm">Tracking: <span className="font-mono">{o.delivery.tracking_reference}</span> {o.delivery.carrier && `(${o.delivery.carrier})`} {o.delivery.tracking_url && <a href={o.delivery.tracking_url} target="_blank" rel="noopener noreferrer" className="text-brand-700 underline">Track</a>}</p>}
            {o.delivery_address && <p className="mt-2 text-sm text-muted">{o.delivery_address.full_name}, {o.delivery_address.phone} — {o.delivery_address.street}, {o.delivery_address.city}, {o.delivery_address.state}{o.delivery_address.landmark ? ` (near ${o.delivery_address.landmark})` : ""}</p>}
            {!o.delivery_address && o.role === "seller" && <p className="mt-2 text-sm text-muted">The buyer&apos;s address will appear once payment is confirmed.</p>}
            {o.buyer_note && <p className="mt-2 rounded-lg bg-canvas p-2 text-sm"><span className="font-semibold">Buyer note:</span> {o.buyer_note}</p>}
            {o.delivery.updates.length > 0 && <ul className="mt-3 space-y-1 text-sm">{o.delivery.updates.map((u, i) => <li key={i}><span className="text-muted">{date(u.at, true)}</span> — {titleCase(u.status)}{u.note && `: ${u.note}`}</li>)}</ul>}
            {o.delivery.evidence_urls.length > 0 && <div className="mt-2 flex gap-2">{o.delivery.evidence_urls.map((u) => <a key={u} href={u} target="_blank" rel="noopener noreferrer">{/* eslint-disable-next-line @next/next/no-img-element */}<img src={u} alt="Delivery evidence" className="size-16 rounded object-cover" /></a>)}</div>}
          </section>
        )}

        {o.disputes.map((d) => (
          <section key={d.id} className="card p-4 sm:p-5">
            <div className="flex items-center justify-between"><h2 className="font-semibold">Dispute · {titleCase(d.reason)}</h2><Badge tone={d.status.startsWith("resolved") ? "good" : "bad"}>{titleCase(d.status)}</Badge></div>
            <ul className="mt-3 space-y-2">
              {d.messages.map((m, i) => (
                <li key={i} className="rounded-lg bg-canvas p-3 text-sm"><p className="text-xs font-semibold capitalize text-muted">{m.author_role} · {date(m.created_at, true)}</p><p className="mt-1">{m.body}</p>
                  {m.evidence_urls.length > 0 && <div className="mt-2 flex gap-2">{m.evidence_urls.map((u) => <a key={u} href={u} target="_blank" rel="noopener noreferrer">{/* eslint-disable-next-line @next/next/no-img-element */}<img src={u} alt="Evidence" className="size-14 rounded object-cover" /></a>)}</div>}</li>
              ))}
            </ul>
            {d.resolution_notes && <Alert tone="info" className="mt-3" title="Resolution">{d.resolution_notes}</Alert>}
            {["open", "under_review"].includes(d.status) && o.role !== "admin" && (
              <form className="mt-3 space-y-2" onSubmit={async (e) => {
                e.preventDefault(); setBusy(true);
                try { await http.post(`/disputes/${d.id}/messages`, { body: f.dmsg, evidence_urls: evidence }); setData(await http.get<OrderDetail>(`/orders/${o.id}`)); setF({}); setEvidence([]); }
                catch (err) { toast(errorMessage(err), "bad"); } finally { setBusy(false); }
              }}>
                <Textarea aria-label="Add to dispute" rows={2} placeholder="Add information or evidence…" value={f.dmsg ?? ""} onChange={set("dmsg")} />
                <div className="flex items-center justify-between">{EvidenceInput}<Button size="sm" type="submit" loading={busy} disabled={!f.dmsg}>Send</Button></div>
              </form>
            )}
          </section>
        ))}

        <section className="card p-4 sm:p-5">
          <h2 className="flex items-center gap-2 font-semibold"><ShieldCheck className="size-5 text-brand-700" />Escrow timeline</h2>
          <ol className="mt-3 space-y-3">
            {o.escrow.timeline.map((e, i) => (
              <li key={i} className="flex gap-3 text-sm">
                {i === o.escrow.timeline.length - 1 ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-brand-600" /> : <Circle className="mt-0.5 size-4 shrink-0 text-line" />}
                <div><p className="font-medium">{ORDER_STATUS[e.to as OrderDetail["status"]]?.label ?? titleCase(e.to)}</p><p className="text-xs text-muted">{date(e.at, true)} · {e.actor}{e.note ? ` · ${e.note}` : ""}</p></div>
              </li>
            ))}
          </ol>
        </section>
      </div>

      {justPaid && o.role === "buyer" && (
        <TrackEvent name="purchase" orderId={o.id} value={Number(o.total)}
          items={o.items.map((i) => ({ id: i.product_id, price: i.unit_price, name: i.title }))} />
      )}
      <aside className="space-y-3 lg:sticky lg:top-20 lg:self-start">
        <div className="card p-4 sm:p-5">
          <dl className="space-y-1.5 text-sm">
            <div className="flex justify-between"><dt>Item</dt><dd>{naira(o.subtotal)}</dd></div>
            <div className="flex justify-between"><dt>Delivery</dt><dd>{naira(o.delivery_fee)}</dd></div>
            <div className="flex justify-between"><dt>Protection fee</dt><dd>{naira(o.protection_fee)}</dd></div>
            <div className="flex justify-between border-t border-line pt-1.5 font-bold"><dt>Total</dt><dd>{naira(o.total)}</dd></div>
            {o.role === "seller" && <><div className="flex justify-between text-muted"><dt>Commission</dt><dd>-{naira(o.platform_fees)}</dd></div><div className="flex justify-between font-bold text-brand-800"><dt>Your earnings</dt><dd>{naira(o.seller_earnings)}</dd></div></>}
          </dl>
          {o.financing && <p className="mt-3 rounded-lg bg-violet-50 p-2.5 text-xs text-violet-900">Goods Flex · {o.financing.status}{o.financing.settlement ? ` · ${o.financing.settlement}` : ""}{o.financing.outstanding_balance ? ` · outstanding ${naira(o.financing.outstanding_balance)}` : ""}</p>}
          <div className="mt-4 space-y-2">
            {has("pay") && o.payment?.authorization_url && <Button block onClick={() => (window.location.href = o.payment!.authorization_url!)}>Complete payment</Button>}
            {has("pay") && !o.payment?.authorization_url && o.payment_method === "full" && <Button block onClick={async () => { try { const r = await http.post<{ authorization_url: string }>(`/orders/${o.id}/retry-payment`); window.location.href = r.authorization_url; } catch (e) { toast(errorMessage(e), "bad"); } }}>Retry payment</Button>}
            {has("accept") && <Button block loading={busy} onClick={() => run("accept", undefined, "Order accepted")}><PackageCheck className="size-4" />Accept order</Button>}
            {has("dispatch") && <Button block onClick={() => setModal("dispatch")}><Truck className="size-4" />Mark as dispatched</Button>}
            {has("delivery_update") && <Button block variant="outline" onClick={() => setModal("update")}>Post delivery update</Button>}
            {has("mark_delivered") && <Button block onClick={() => setModal("delivered")}>Mark as delivered</Button>}
            {has("confirm") && <Button block size="lg" onClick={() => { if (confirm("Confirm you received the item as described? This releases payment to the seller.")) run("confirm", undefined, "Thanks! Payment released to the seller."); }}><CheckCircle2 className="size-5" />Confirm receipt</Button>}
            {has("review") && <Button block variant="accent" onClick={() => setModal("review")}><Star className="size-4" />Rate this seller</Button>}
            {has("dispute") && <Button block variant="ghost" className="text-red-600" onClick={() => setModal("dispute")}><AlertTriangle className="size-4" />Report a problem</Button>}
            {has("decline") && <Button block variant="ghost" className="text-red-600" onClick={() => setModal("decline")}>Decline & refund buyer</Button>}
            {has("cancel") && <Button block variant="ghost" onClick={() => setModal("cancel")}>Cancel order</Button>}
          </div>
          {o.refunds.map((r) => <p key={r.id} className="mt-3 rounded-lg bg-canvas p-2.5 text-xs">Refund {naira(r.amount)} · {titleCase(r.status)}</p>)}
        </div>
      </aside>

      <Modal open={modal === "dispatch"} onClose={() => setModal(null)} title="Dispatch order" footer={<Button loading={busy} onClick={() => run("dispatch", { carrier: f.carrier || undefined, tracking_reference: f.tracking || undefined, tracking_url: f.url || undefined, notes: f.notes || undefined }, "Marked as dispatched")}>Confirm dispatch</Button>}>
        <div className="space-y-3">
          <Input label="Carrier / rider" placeholder="e.g. GIG Logistics, Kwik, own rider" value={f.carrier ?? ""} onChange={set("carrier")} />
          <Input label={`Tracking / waybill number${o.delivery?.method === "courier" ? " (required)" : ""}`} value={f.tracking ?? ""} onChange={set("tracking")} />
          <Input label="Tracking link (optional)" placeholder="https://" value={f.url ?? ""} onChange={set("url")} />
          <Textarea label="Notes" rows={2} value={f.notes ?? ""} onChange={set("notes")} />
        </div>
      </Modal>
      <Modal open={modal === "update"} onClose={() => setModal(null)} title="Delivery update" footer={<Button loading={busy} onClick={() => run("delivery-update", { note: f.note }, "Update posted")}>Post update</Button>}>
        <Input label="Update" placeholder="e.g. Arrived at Ikeja hub" value={f.note ?? ""} onChange={set("note")} />
      </Modal>
      <Modal open={modal === "delivered"} onClose={() => setModal(null)} title="Mark as delivered" footer={<Button loading={busy} onClick={() => run("delivered", { evidence_urls: evidence, notes: f.notes || undefined }, "Marked as delivered")}>Confirm delivery</Button>}>
        <p className="text-sm text-muted">Add proof of delivery (signed waybill, photo of handover). It protects you if the buyer disputes.</p>
        <div className="mt-3 space-y-3">{EvidenceInput}<Textarea label="Notes" rows={2} value={f.notes ?? ""} onChange={set("notes")} /></div>
      </Modal>
      <Modal open={modal === "dispute"} onClose={() => setModal(null)} title="Report a problem" footer={<Button variant="danger" loading={busy} disabled={(f.desc ?? "").length < 20 || !f.reason} onClick={() => run("disputes", { reason: f.reason, description: f.desc, evidence_urls: evidence }, "Dispute opened — funds stay safeguarded")}>Open dispute</Button>}>
        <div className="space-y-3">
          <Select label="What went wrong?" value={f.reason ?? ""} onChange={set("reason")}><option value="">Select a reason</option>{(DISPUTE_REASONS[o.role] ?? []).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
          <Textarea label="Describe the problem (min. 20 characters)" rows={4} value={f.desc ?? ""} onChange={set("desc")} />
          {EvidenceInput}
        </div>
      </Modal>
      <Modal open={modal === "decline"} onClose={() => setModal(null)} title="Decline order" footer={<Button variant="danger" loading={busy} onClick={() => run("decline", { reason: f.reason || "Unable to fulfil" }, "Order declined and buyer refunded")}>Decline & refund</Button>}>
        <p className="text-sm text-muted">The buyer will receive a full refund automatically.</p>
        <div className="mt-3"><Input label="Reason" value={f.reason ?? ""} onChange={set("reason")} /></div>
      </Modal>
      <Modal open={modal === "cancel"} onClose={() => setModal(null)} title="Cancel order" footer={<Button variant="danger" loading={busy} onClick={() => run("cancel", { reason: f.reason || undefined }, "Order cancelled")}>Cancel order</Button>}>
        <p className="text-sm text-muted">{o.status === "pending_payment" ? "This order hasn't been paid, so nothing will be charged." : "You'll get a full refund to your original payment method."}</p>
        <div className="mt-3"><Input label="Reason (optional)" value={f.reason ?? ""} onChange={set("reason")} /></div>
      </Modal>
      <Modal open={modal === "review"} onClose={() => setModal(null)} title="Rate your purchase" footer={<Button loading={busy} onClick={async () => {
        setBusy(true);
        try { await http.post("/reviews", { order_id: o.id, rating, title: f.title || undefined, comment: f.comment || undefined }); toast("Thanks for your review!"); setModal(null); setData({ ...o, actions: o.actions.filter((a) => a !== "review") }); }
        catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
      }}>Submit review</Button>}>
        <div className="flex gap-1" role="radiogroup" aria-label="Rating">{[1, 2, 3, 4, 5].map((n) => <button key={n} role="radio" aria-checked={rating === n} aria-label={`${n} stars`} onClick={() => setRating(n)}><Star className={clsx("size-8", n <= rating ? "fill-accent-500 text-accent-500" : "text-line")} /></button>)}</div>
        <div className="mt-3 space-y-3"><Input label="Title" value={f.title ?? ""} onChange={set("title")} /><Textarea label="Your review" rows={3} value={f.comment ?? ""} onChange={set("comment")} /></div>
      </Modal>
    </div>
  );
}
