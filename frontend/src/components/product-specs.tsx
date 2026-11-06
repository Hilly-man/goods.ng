"use client";

import { useState, type ReactNode } from "react";
import { ChevronUp } from "lucide-react";

export type Spec = { label: string; value: ReactNode };

export function ProductSpecs({ items }: { items: Spec[] }) {
  const [open, setOpen] = useState(true);
  return (
    <div>
      {open && (
        <dl className="grid grid-cols-2 gap-x-8 gap-y-4">
          {items.map((item) => (
            <div key={item.label} className="min-w-0">
              <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{item.label}</dt>
              <dd className="mt-0.5 whitespace-pre-line break-words text-sm font-medium text-ink">{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
      <div className="mt-3 text-right">
        <button type="button" onClick={() => setOpen((v) => !v)}
          className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">
          {open ? "Hide details" : "Show details"}
          <ChevronUp className={open ? "size-4" : "size-4 rotate-180"} />
        </button>
      </div>
    </div>
  );
}
