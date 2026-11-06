"use client";

import { useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { AlertTriangle } from "lucide-react";
import { Badge, Button, Modal } from "./ui";
import { titleCase } from "@/lib/format";

/* ------------------------------------------------------------------------------------------------
 * Dialogs — promise-based replacements for window.prompt / confirm, rendered by <AdminDialogHost/>.
 *   if (!(await confirmAction({ title: "Approve refund?", ... }))) return;
 *   const reason = await askReason("Reason for suspension"); if (!reason) return;
 * ---------------------------------------------------------------------------------------------- */

type Req = {
  title: string;
  message?: React.ReactNode;
  confirmLabel?: string;
  tone?: "default" | "danger";
  input?: { label: string; min?: number; placeholder?: string; multiline?: boolean; type?: "text" | "number"; initial?: string };
  resolve: (v: string | boolean | null) => void;
};

let push: ((r: Req) => void) | null = null;

function open(r: Omit<Req, "resolve">): Promise<string | boolean | null> {
  return new Promise((resolve) => {
    if (!push) {
      // Host not mounted (shouldn't happen inside the admin shell): fall back to the browser dialogs.
      if (r.input) resolve(window.prompt(r.title, r.input.initial ?? ""));
      else resolve(window.confirm(r.title));
      return;
    }
    push({ ...r, resolve });
  });
}

/** Ask for a required written reason (audit-logged by the API). Resolves to null when cancelled. */
export async function askReason(title: string, min = 3, opts: { message?: React.ReactNode; confirmLabel?: string; tone?: "default" | "danger" } = {}) {
  const v = await open({ title: title.replace(/:\s*$/, ""), ...opts, input: { label: "Reason", min, multiline: true, placeholder: "Be specific — this is saved to the audit log." } });
  return typeof v === "string" ? v.trim() : null;
}

/** Ask for a single value (e.g. a new name or a number of days). */
export async function askValue(title: string, input: Req["input"] & object, opts: { message?: React.ReactNode; confirmLabel?: string } = {}) {
  const v = await open({ title, ...opts, input });
  return typeof v === "string" ? v.trim() : null;
}

export async function confirmAction(opts: { title: string; message?: React.ReactNode; confirmLabel?: string; tone?: "default" | "danger" }) {
  return (await open(opts)) === true;
}

export function AdminDialogHost() {
  const [req, setReq] = useState<Req | null>(null);
  const [value, setValue] = useState("");
  const [touched, setTouched] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement & HTMLInputElement>(null);

  useEffect(() => {
    push = (r) => { setReq(r); setValue(r.input?.initial ?? ""); setTouched(false); };
    return () => { push = null; };
  }, []);
  useEffect(() => { if (req?.input) setTimeout(() => inputRef.current?.focus(), 50); }, [req]);

  if (!req) return null;
  const min = req.input?.min ?? 1;
  const invalid = !!req.input && (req.input.type === "number" ? !(Number(value) > 0) : value.trim().length < min);
  const close = (v: string | boolean | null) => { req.resolve(v); setReq(null); };
  const submit = () => {
    setTouched(true);
    if (invalid) return;
    close(req.input ? value : true);
  };

  return (
    <Modal open onClose={() => close(null)} title={req.title} size="sm"
      footer={<>
        <Button variant="ghost" onClick={() => close(null)}>Cancel</Button>
        <Button variant={req.tone === "danger" ? "danger" : "primary"} onClick={submit}>{req.confirmLabel ?? (req.input ? "Continue" : "Confirm")}</Button>
      </>}>
      <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="space-y-3">
        {req.tone === "danger" && !req.input && (
          <p className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-800"><AlertTriangle className="mt-0.5 size-4 shrink-0" />This can affect real customers. Double-check before continuing.</p>
        )}
        {req.message && <div className="text-sm text-ink/80">{req.message}</div>}
        {req.input && (
          <label className="block">
            <span className="mb-1 block text-sm font-medium">{req.input.label}</span>
            {req.input.multiline ? (
              <textarea ref={inputRef} rows={3} className="input min-h-24 py-2" placeholder={req.input.placeholder} value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit(); }} />
            ) : (
              <input ref={inputRef} className="input" type={req.input.type ?? "text"} placeholder={req.input.placeholder} value={value}
                onChange={(e) => setValue(e.target.value)} />
            )}
            {touched && invalid
              ? <span className="mt-1 block text-xs text-red-600">{req.input.type === "number" ? "Enter a number greater than 0." : `Please enter at least ${min} characters.`}</span>
              : req.input.min && req.input.min > 1 ? <span className="mt-1 block text-xs text-muted">At least {req.input.min} characters.</span> : null}
          </label>
        )}
      </form>
    </Modal>
  );
}

/* ------------------------------------------------------------------------------------------------ */

export function AdminPageHeader({ title, description, actions, icon: Icon }: { title: string; description?: React.ReactNode; actions?: React.ReactNode; icon?: React.ElementType }) {
  return (
    <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
      <div className="flex min-w-0 items-start gap-3">
        {Icon && <span className="hidden size-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700 sm:grid"><Icon className="size-5" /></span>}
        <div className="min-w-0">
          <h1 className="text-xl font-bold tracking-tight sm:text-2xl">{title}</h1>
          {description && <p className="mt-0.5 max-w-2xl text-sm text-muted">{description}</p>}
        </div>
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

/** Segmented filter chips (scroll sideways on small screens). */
export function FilterChips<T extends string>({ value, onChange, options, label = "Filter" }: {
  value: T; onChange: (v: T) => void; options: { value: T; label: string }[]; label?: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="scrollbar-none -mx-1 flex max-w-full gap-1.5 overflow-x-auto px-1 py-0.5">
      {options.map((o) => (
        <button key={o.value || "_all"} type="button" role="radio" aria-checked={value === o.value} onClick={() => onChange(o.value)}
          className={clsx("shrink-0 rounded-full px-3 py-1.5 text-sm font-medium ring-1 transition",
            value === o.value ? "bg-brand-700 text-white ring-brand-700" : "bg-white text-ink/80 ring-line hover:bg-canvas")}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

const GOOD = new Set(["active", "success", "completed", "published", "approved", "accepted", "resolved_buyer", "resolved_seller", "actioned", "consented"]);
const WARN = new Set(["pending", "pending_review", "pending_payment", "pending_approval", "awaiting_seller", "awaiting_buyer_confirmation", "processing", "initialized", "under_review", "open", "refund_pending", "dispatched", "delivered"]);
const BAD = new Set(["rejected", "failed", "declined", "defaulted", "disputed", "hidden", "suspended", "cancelled", "abandoned", "expired"]);

/** Colour-coded status pill used across admin lists. */
export function StatusBadge({ status }: { status: string }) {
  const tone = GOOD.has(status) ? "good" : WARN.has(status) ? "warn" : BAD.has(status) ? "bad" : "neutral";
  return <Badge tone={tone}>{titleCase(status)}</Badge>;
}
