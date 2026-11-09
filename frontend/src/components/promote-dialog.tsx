"use client";

import { useState } from "react";
import { Check, ShieldCheck } from "lucide-react";
import { Alert, Button, Modal, Spinner } from "./ui";
import { errorMessage, http } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { naira } from "@/lib/format";
import type { PromotionPackage } from "@/lib/types";

/**
 * Buy visibility for one listing, without an account-level subscription.
 * The server owns the package list and prices; the client only sends a package code.
 */
export function PromoteDialog({ product, onClose }: {
  product: { id: string; title: string };
  onClose: () => void;
}) {
  const { data, error } = useApi<PromotionPackage[]>("/promotions/packages");
  const [picked, setPicked] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const selected = picked || data?.[0]?.code || "";
  const pkg = data?.find((p) => p.code === selected);

  async function pay() {
    if (!pkg) return;
    setBusy(true);
    setErr(null);
    try {
      const res = await http.post<{ authorization_url: string }>("/promotions", {
        product_id: product.id,
        package_code: pkg.code,
      });
      window.location.assign(res.authorization_url);
    } catch (e) {
      setErr(errorMessage(e));
      setBusy(false);
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Promote this listing"
      size="lg"
      footer={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs text-muted">One-off payment · no subscription</span>
          <div className="flex gap-2">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button onClick={pay} loading={busy} disabled={!pkg}>
              {pkg ? `Pay ${naira(pkg.price)}` : "Choose a package"}
            </Button>
          </div>
        </div>
      }
    >
      <p className="text-sm text-muted">
        Give <b className="text-ink">{product.title}</b> more visibility. Only this listing is promoted — your account stays on the free plan.
      </p>
      {(err || error) && <Alert tone="bad">{err || error}</Alert>}

      {!data ? (
        <div className="grid place-items-center py-8"><Spinner className="size-6" /></div>
      ) : (
        <div className="space-y-2">
          {data.map((p) => {
            const active = selected === p.code;
            return (
              <label
                key={p.code}
                className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3 transition ${
                  active ? "border-brand-600 bg-brand-50 ring-2 ring-brand-600/15" : "border-line hover:border-brand-300"
                }`}
              >
                <input type="radio" name="promotion" className="sr-only" checked={active} onChange={() => setPicked(p.code)} />
                <span className={`mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border ${
                  active ? "border-brand-600 bg-brand-600 text-white" : "border-line"
                }`}>
                  {active && <Check className="size-3" />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-2">
                    <b>{p.name}</b>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                      p.tier === "premium" ? "bg-brand-700 text-white" : "bg-accent-500 text-ink"
                    }`}>
                      {p.tier === "premium" ? "Premium" : "TOP"}
                    </span>
                    <span className="rounded bg-canvas px-1.5 py-0.5 text-[11px] text-muted">{p.days} days</span>
                  </span>
                  <span className="mt-0.5 block text-xs text-muted">{p.tagline}</span>
                </span>
                <b className="shrink-0 text-sm">{naira(p.price)}</b>
              </label>
            );
          })}
        </div>
      )}

      <p className="flex items-center gap-1.5 text-xs text-muted">
        <ShieldCheck className="size-3.5 text-brand-700" />
        The promotion starts as soon as your payment is confirmed.
      </p>
    </Modal>
  );
}
