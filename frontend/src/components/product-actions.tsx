"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CalendarClock, Flag, Handshake, MessageCircle, Phone, ShieldCheck, ShoppingBag } from "lucide-react";
import type { FinancingOption, ProductDetail } from "@/lib/types";
import { http, errorMessage, ApiError } from "@/lib/api";
import { naira, toMoneyString } from "@/lib/format";
import { useAuth } from "./auth-provider";
import { Alert, Button, ButtonLink, Checkbox, Input, Modal, Textarea, useToast } from "./ui";
import { FavouriteButton } from "./favourite-button";

const WARNING =
  "You are contacting this seller directly. Transactions completed outside Goods.ng Protected Checkout are not covered by our escrow protection or transaction dispute resolution process. For safer transactions, use Goods.ng Protected Checkout.";

function WhatsAppIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-5" fill="currentColor" aria-hidden>
      <path d="M17.5 14.4c-.3-.1-1.7-.8-2-.9-.3-.1-.5-.1-.7.1-.2.3-.8.9-.9 1.1-.2.2-.3.2-.6.1-.3-.1-1.2-.5-2.3-1.4-.9-.8-1.4-1.7-1.6-2-.2-.3 0-.5.1-.6l.4-.5c.2-.2.2-.3.3-.5.1-.2 0-.4 0-.5l-.9-2.2c-.2-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.1.2 2.1 3.2 5.1 4.5.7.3 1.3.5 1.7.6.7.2 1.4.2 1.9.1.6-.1 1.7-.7 1.9-1.4.2-.7.2-1.2.2-1.4-.1-.1-.3-.2-.6-.3ZM12 21.8c-1.8 0-3.5-.5-5-1.4l-.4-.2-3.7 1 1-3.6-.2-.4A9.8 9.8 0 1 1 12 21.8Zm0-21.6A11.8 11.8 0 0 0 1.9 18L.2 24l6.2-1.6A11.8 11.8 0 1 0 12 .2Z" />
    </svg>
  );
}

export function ProductActions({ p }: { p: ProductDetail }) {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [modal, setModal] = useState<null | "offer" | "chat" | "contact" | "report">(null);
  const [channel, setChannel] = useState<"whatsapp" | "phone">("whatsapp");
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [offer, setOffer] = useState("");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState(`Hello, is "${p.title}" still available?`);
  const [reason, setReason] = useState("");
  const [flex, setFlex] = useState<FinancingOption | null>(null);
  const isOwn = user?.seller?.id === p.seller.id;
  const available = p.status === "active" && p.quantity > 0;

  useEffect(() => {
    fetch(`/api/v1/products/${p.slug}/view`, { method: "POST" }).catch(() => {});
    if (p.bnpl_enabled) {
      http.get<{ options: FinancingOption[] }>("/bnpl/quote", { product_id: p.id })
        .then((r) => setFlex(r.options.at(-1) ?? null))
        .catch(() => {});
    }
  }, [p.slug, p.id, p.bnpl_enabled]);

  const requireLogin = () => {
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(`/item/${p.slug}`)}`);
      return true;
    }
    return false;
  };
  const open = (m: typeof modal) => {
    if (m !== "contact" && requireLogin()) return;
    setErr(null);
    setModal(m);
  };

  async function sendOffer() {
    const amount = toMoneyString(offer);
    if (!amount) return setErr("Enter a valid amount");
    setBusy(true);
    try {
      const n = await http.post<{ id: string }>("/negotiations", { product_id: p.id, amount, note: note || undefined });
      toast("Offer sent to the seller");
      router.push(`/offers/${n.id}`);
    } catch (e) {
      if (e instanceof ApiError && e.code === "negotiation_exists") {
        const id = (e.details as { negotiation_id: string }).negotiation_id;
        router.push(`/offers/${id}`);
        return;
      }
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function sendChat() {
    setBusy(true);
    try {
      const r = await http.post<{ conversation_id: string }>("/conversations", { product_id: p.id, body: msg });
      router.push(`/messages/${r.conversation_id}`);
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(false);
    }
  }

  async function contact() {
    setBusy(true);
    try {
      const r = await http.post<{ link: string; display: string }>(`/sellers/${p.seller.id}/contact`, {
        channel,
        product_id: p.id,
        acknowledged_warning: true,
      });
      setModal(null);
      window.location.href = r.link;
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function report() {
    setBusy(true);
    try {
      await http.post("/users/reports", { target_type: "product", target_id: p.id, reason: reason || "Other" });
      toast("Thanks — our team will review this listing");
      setModal(null);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="space-y-2.5">
        {isOwn ? (
          <ButtonLink href={`/seller/products/${p.id}/edit`} variant="outline" block>Edit your listing</ButtonLink>
        ) : !available ? (
          <Alert tone="warn" title={p.status === "sold" ? "This item has been sold" : "Currently out of stock"}>
            Save it or chat with the seller to ask about availability.
          </Alert>
        ) : (
          <>
            {p.protected_checkout_enabled && (
              <ButtonLink href={`/checkout/${p.slug}`} block size="lg">
                <ShoppingBag className="size-5" /> Buy with Protected Checkout
              </ButtonLink>
            )}
            {p.bnpl_enabled && (
              <ButtonLink href={`/checkout/${p.slug}?flex=1`} variant="outline" block size="lg" className="border-violet-300 text-violet-800 hover:border-violet-500 hover:text-violet-900">
                <CalendarClock className="size-5" />
                {flex ? <>Goods Flex · from {naira(flex.monthly_installment)}/mo</> : "Pay small-small with Goods Flex"}
              </ButtonLink>
            )}
            {p.negotiable && (
              <Button variant="secondary" block size="lg" onClick={() => open("offer")}>
                <Handshake className="size-5" /> Make an offer
              </Button>
            )}
          </>
        )}
        {!isOwn && (
          <Button variant="outline" block size="lg" onClick={() => open("chat")}>
            <MessageCircle className="size-5" /> Chat with seller
          </Button>
        )}
        {!isOwn && (p.seller.whatsapp_available || p.seller.phone_available) && (
          <div className="grid grid-cols-2 gap-2">
            {p.seller.whatsapp_available && (
              <Button variant="whatsapp" onClick={() => { setChannel("whatsapp"); setAck(false); open("contact"); }}>
                <WhatsAppIcon /> WhatsApp
              </Button>
            )}
            {p.seller.phone_available && (
              <Button variant="outline" onClick={() => { setChannel("phone"); setAck(false); open("contact"); }} className={!p.seller.whatsapp_available ? "col-span-2" : ""}>
                <Phone className="size-5" /> Call seller
              </Button>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <FavouriteButton productId={p.id} initial={p.is_favourite} withLabel className="flex-1 justify-center" />
          {!isOwn && (
            <button onClick={() => open("report")} className="inline-flex h-11 items-center gap-1.5 rounded-lg border border-line bg-white px-4 text-sm text-muted hover:text-red-600">
              <Flag className="size-4" /> Report
            </button>
          )}
        </div>
        {p.protected_checkout_enabled && (
          <p className="flex items-start gap-2 rounded-lg bg-brand-50 p-3 text-xs text-brand-900">
            <ShieldCheck className="mt-0.5 size-4 shrink-0" />
            With Protected Checkout your payment is held by our licensed escrow partner and only released to the seller after you confirm delivery.{" "}
            <Link href="/buyer-protection" className="font-semibold underline">Learn more</Link>
          </p>
        )}
      </div>

      <Modal open={modal === "offer"} onClose={() => setModal(null)} title="Make an offer"
        footer={<><Button variant="ghost" onClick={() => setModal(null)}>Cancel</Button><Button loading={busy} onClick={sendOffer}>Send offer</Button></>}>
        <p className="text-sm text-muted">Listed at <span className="font-semibold text-ink">{naira(p.price)}</span>. The seller can accept, decline or counter. Offers expire after 48 hours.</p>
        <div className="mt-4 space-y-3">
          <Input label="Your offer (₦)" inputMode="numeric" placeholder="e.g. 1,350,000" value={offer} onChange={(e) => setOffer(e.target.value)} autoFocus />
          <div className="flex flex-wrap gap-2">
            {[0.95, 0.9, 0.85].map((r) => {
              const v = Math.floor((Number(p.price) * r) / 1000) * 1000;
              return <button key={r} type="button" className="chip" onClick={() => setOffer(v.toLocaleString())}>{naira(String(v))}</button>;
            })}
          </div>
          <Textarea label="Note (optional)" rows={2} value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} placeholder="e.g. I can pay today via Protected Checkout" />
          {err && <Alert tone="bad">{err}</Alert>}
        </div>
      </Modal>

      <Modal open={modal === "chat"} onClose={() => setModal(null)} title={`Message ${p.seller.store_name}`}
        footer={<><Button variant="ghost" onClick={() => setModal(null)}>Cancel</Button><Button loading={busy} onClick={sendChat}>Send message</Button></>}>
        <Textarea label="Your message" rows={3} value={msg} onChange={(e) => setMsg(e.target.value)} maxLength={2000} />
        <div className="mt-2 flex flex-wrap gap-2">
          {["Is the price negotiable?", "Where can I inspect it?", "Do you deliver to my area?"].map((t) => (
            <button key={t} className="chip" onClick={() => setMsg(t)}>{t}</button>
          ))}
        </div>
        <p className="mt-3 text-xs text-muted">Keep chats on Goods.ng. Never pay in advance outside Protected Checkout.</p>
        {err && <Alert tone="bad" className="mt-3">{err}</Alert>}
      </Modal>

      <Modal open={modal === "contact"} onClose={() => setModal(null)} title={channel === "whatsapp" ? "Chat on WhatsApp" : "Call seller"} size="sm"
        footer={<><Button variant="ghost" onClick={() => setModal(null)}>Cancel</Button>
          <Button variant={channel === "whatsapp" ? "whatsapp" : "primary"} disabled={!ack} loading={busy} onClick={contact}>
            {channel === "whatsapp" ? "Open WhatsApp" : "Show number & call"}
          </Button></>}>
        <Alert tone="warn" title="Before you continue">{WARNING}</Alert>
        <div className="mt-4">
          <Checkbox checked={ack} onChange={(e) => setAck(e.target.checked)} label="I understand that deals made outside Goods.ng Protected Checkout are not covered." />
        </div>
        {p.protected_checkout_enabled && (
          <Link href={`/checkout/${p.slug}`} className="mt-4 block text-center text-sm font-semibold text-brand-700 hover:underline">
            Use Protected Checkout instead →
          </Link>
        )}
        {err && <Alert tone="bad" className="mt-3">{err}</Alert>}
      </Modal>

      <Modal open={modal === "report"} onClose={() => setModal(null)} title="Report this listing" size="sm"
        footer={<><Button variant="ghost" onClick={() => setModal(null)}>Cancel</Button><Button variant="danger" loading={busy} onClick={report}>Submit report</Button></>}>
        <div className="space-y-2">
          {["Fraud or scam", "Counterfeit item", "Wrong category", "Item already sold", "Offensive content", "Other"].map((r) => (
            <label key={r} className="flex cursor-pointer items-center gap-2.5 rounded-lg border border-line p-3 text-sm has-[:checked]:border-brand-600 has-[:checked]:bg-brand-50">
              <input type="radio" name="reason" value={r} checked={reason === r} onChange={() => setReason(r)} className="accent-brand-700" />
              {r}
            </label>
          ))}
        </div>
        {err && <Alert tone="bad" className="mt-3">{err}</Alert>}
      </Modal>
    </>
  );
}
