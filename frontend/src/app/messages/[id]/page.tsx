"use client";

import { Suspense as RouteSuspense } from "react";
import Link from "next/link";
import { use, useEffect, useRef, useState } from "react";
import { ArrowLeft, CheckCheck, Flag, Handshake, Send, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import { RequireAuth } from "@/components/require-auth";
import { PageLoader, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { usePolling } from "@/lib/hooks";
import { naira } from "@/lib/format";
import type { User } from "@/lib/types";

type Msg = { id: string; sender_id: string; body: string; kind: string; offer_id: string | null; read_at: string | null; created_at: string };
type Conv = {
  id: string; role: "buyer" | "seller"; negotiation_id: string | null;
  other_party: { name: string; seller_slug: string | null };
  product: { id: string; title: string; slug: string; price: string; negotiable: boolean; status: string; protected_checkout_enabled: boolean; thumb_url: string | null } | null;
  messages: Msg[];
};

function Thread({ id, user }: { id: string; user: User }) {
  const [conv, setConv] = useState<Conv | null>(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const toast = useToast();
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => { http.get<Conv>(`/conversations/${id}`).then(setConv).catch((e) => toast(errorMessage(e), "bad")); }, [id, toast]);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [conv?.messages.length]);

  usePolling(async () => {
    // Refresh the latest page of the thread so new messages and read receipts both update.
    const fresh = await http.get<Conv>(`/conversations/${id}`).catch(() => null);
    if (fresh) setConv(fresh);
  }, 5000, !!conv);

  if (!conv) return <PageLoader />;
  const p = conv.product;

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setSending(true);
    try {
      const m = await http.post<Msg>(`/conversations/${id}/messages`, { body: text });
      setConv((c) => c && { ...c, messages: [...c.messages, m] });
      setText("");
    } catch (err) { toast(errorMessage(err), "bad"); } finally { setSending(false); }
  }

  async function report(m: Msg) {
    const reason = prompt("Why are you reporting this message?");
    if (!reason) return;
    try { await http.post(`/messages/${m.id}/report`, { reason }); toast("Message reported"); } catch (e) { toast(errorMessage(e), "bad"); }
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-7rem)] max-w-3xl flex-col md:h-[calc(100dvh-8rem)]">
      <div className="flex items-center gap-3 border-b border-line bg-white px-3 py-2.5">
        <Link href="/messages" aria-label="Back to messages" className="rounded-full p-1.5 hover:bg-black/5"><ArrowLeft className="size-5" /></Link>
        <div className="min-w-0 flex-1">
          <p className="truncate font-semibold">{conv.other_party.seller_slug ? <Link href={`/store/${conv.other_party.seller_slug}`} className="hover:underline">{conv.other_party.name}</Link> : conv.other_party.name}</p>
          {p && <Link href={`/item/${p.slug}`} className="block truncate text-xs text-brand-700">{p.title} · {naira(p.price)}</Link>}
        </div>
      </div>
      {p && conv.role === "buyer" && p.status === "active" && (
        <div className="flex gap-2 border-b border-line bg-brand-50/60 px-3 py-2 text-sm">
          {p.protected_checkout_enabled && <Link href={`/checkout/${p.slug}${conv.negotiation_id ? `?negotiation=${conv.negotiation_id}` : ""}`} className="inline-flex items-center gap-1 rounded-lg bg-brand-700 px-3 py-1.5 font-semibold text-white"><ShieldCheck className="size-4" />Buy safely</Link>}
          {conv.negotiation_id ? <Link href={`/offers/${conv.negotiation_id}`} className="inline-flex items-center gap-1 rounded-lg border border-line bg-white px-3 py-1.5 font-semibold"><Handshake className="size-4" />View offer</Link>
            : p.negotiable && <Link href={`/item/${p.slug}`} className="inline-flex items-center gap-1 rounded-lg border border-line bg-white px-3 py-1.5 font-semibold"><Handshake className="size-4" />Make offer</Link>}
        </div>
      )}
      {conv.negotiation_id && conv.role === "seller" && (
        <div className="border-b border-line bg-amber-50 px-3 py-2 text-sm"><Link href={`/seller/offers/${conv.negotiation_id}`} className="font-semibold text-amber-900">This buyer made an offer — respond →</Link></div>
      )}
      <div className="flex-1 space-y-2 overflow-y-auto bg-canvas p-3">
        {conv.messages.map((m) => {
          const mine = m.sender_id === user.id;
          if (m.kind === "system") return <p key={m.id} className="mx-auto max-w-sm rounded-full bg-white px-3 py-1 text-center text-xs text-muted">{m.body}</p>;
          return (
            <div key={m.id} className={clsx("group flex", mine ? "justify-end" : "justify-start")}>
              <div className={clsx("max-w-[80%] rounded-2xl px-3.5 py-2 text-[15px] shadow-sm", mine ? "rounded-br-sm bg-brand-700 text-white" : "rounded-bl-sm bg-white", m.kind === "offer" && "ring-2 ring-accent-400")}>
                {m.kind === "offer" && <p className={clsx("text-[11px] font-bold uppercase", mine ? "text-accent-400" : "text-accent-600")}>Offer</p>}
                <p className="whitespace-pre-wrap break-words">{m.body}</p>
                <p className={clsx("mt-0.5 flex items-center justify-end gap-1 text-[10px]", mine ? "text-white/70" : "text-muted")}>
                  {new Date(m.created_at).toLocaleTimeString("en-NG", { hour: "2-digit", minute: "2-digit" })}
                  {mine && <CheckCheck className={clsx("size-3.5", m.read_at ? "text-accent-400" : "")} aria-label={m.read_at ? "Read" : "Sent"} />}
                </p>
              </div>
              {!mine && <button onClick={() => report(m)} className="ml-1 self-center rounded p-1 text-muted opacity-0 hover:text-red-600 group-hover:opacity-100" aria-label="Report message"><Flag className="size-3.5" /></button>}
            </div>
          );
        })}
        <div ref={end} />
      </div>
      <p className="bg-amber-50 px-3 py-1.5 text-center text-[11px] text-amber-900">Never send money outside Goods.ng Protected Checkout. Staff will never ask for your OTP.</p>
      <form onSubmit={send} className="flex gap-2 border-t border-line bg-white p-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))]">
        <input value={text} onChange={(e) => setText(e.target.value)} maxLength={2000} placeholder="Write a message…" aria-label="Message" className="input flex-1 rounded-full" />
        <button type="submit" disabled={sending || !text.trim()} aria-label="Send" className="grid size-11 shrink-0 place-items-center rounded-full bg-brand-700 text-white disabled:opacity-50"><Send className="size-5" /></button>
      </form>
    </div>
  );
}

function Inner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RequireAuth>{(user) => <Thread id={id} user={user} />}</RequireAuth>;
}

export default function Page(props: { params: Promise<{ id: string }> }) {
  return (
    <RouteSuspense fallback={<PageLoader />}>
      <Inner {...props} />
    </RouteSuspense>
  );
}
