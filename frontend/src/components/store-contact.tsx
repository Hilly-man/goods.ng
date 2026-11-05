"use client";

import { useState } from "react";
import { MessageCircle, Phone } from "lucide-react";
import type { Storefront } from "@/lib/types";
import { http, errorMessage } from "@/lib/api";
import { Alert, Button, Checkbox, Modal } from "./ui";

const WARNING =
  "You are contacting this seller directly. Transactions completed outside Goods.ng Protected Checkout are not covered by our escrow protection or transaction dispute resolution process. For safer transactions, use Goods.ng Protected Checkout.";

export function StoreContact({ seller }: { seller: Storefront }) {
  const [channel, setChannel] = useState<"whatsapp" | "phone" | null>(null);
  const [ack, setAck] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  if (!seller.whatsapp_available && !seller.phone_available) return null;
  async function go() {
    setBusy(true);
    try {
      const r = await http.post<{ link: string }>(`/sellers/${seller.id}/contact`, { channel, acknowledged_warning: true });
      window.location.href = r.link;
      setChannel(null);
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex gap-2">
      {seller.whatsapp_available && <Button variant="whatsapp" onClick={() => { setAck(false); setChannel("whatsapp"); }}><MessageCircle className="size-4" />WhatsApp</Button>}
      {seller.phone_available && <Button variant="outline" onClick={() => { setAck(false); setChannel("phone"); }}><Phone className="size-4" />Call</Button>}
      <Modal open={!!channel} onClose={() => setChannel(null)} title="Contact seller directly" size="sm"
        footer={<><Button variant="ghost" onClick={() => setChannel(null)}>Cancel</Button><Button disabled={!ack} loading={busy} onClick={go}>Continue</Button></>}>
        <Alert tone="warn">{WARNING}</Alert>
        <div className="mt-4"><Checkbox checked={ack} onChange={(e) => setAck(e.target.checked)} label="I understand and want to continue." /></div>
        {err && <Alert tone="bad" className="mt-3">{err}</Alert>}
      </Modal>
    </div>
  );
}
