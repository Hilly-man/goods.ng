"use client";

import { useState } from "react";
import { Search } from "lucide-react";
import type { Page } from "@/lib/types";
import { useApi } from "@/lib/hooks";
import { Alert, Button, PageLoader } from "./ui";

export type Col<T> = { key: string; label: string; render: (row: T) => React.ReactNode; className?: string };

export function AdminTable<T extends { id: string }>({
  path,
  columns,
  query,
  searchable,
  filters,
  actions,
  reloadKey,
}: {
  path: string;
  columns: Col<T>[];
  query?: Record<string, unknown>;
  searchable?: boolean;
  filters?: React.ReactNode;
  actions?: (row: T, reload: () => void) => React.ReactNode;
  reloadKey?: number;
}) {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [applied, setApplied] = useState("");
  const { data, error, loading, reload } = useApi<Page<T>>(path, { ...query, q: applied || undefined, page, page_size: 25, _k: reloadKey });
  return (
    <div className="space-y-3">
      {(searchable || filters) && (
        <div className="flex flex-wrap items-center gap-2">
          {searchable && (
            <form onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(q); }} className="flex flex-1 gap-2">
              <div className="relative flex-1"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" /><input className="input pl-9" placeholder="Search…" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" /></div>
              <Button type="submit" variant="secondary">Search</Button>
            </form>
          )}
          {filters}
        </div>
      )}
      {error && <Alert tone="bad">{error}</Alert>}
      <div className="card overflow-x-auto">
        {!data && loading ? <PageLoader /> : (
          <table className="w-full min-w-[720px] text-sm">
            <thead><tr className="border-b border-line bg-canvas/60 text-left text-xs uppercase tracking-wide text-muted">{columns.map((c) => <th key={c.key} className="p-3 font-semibold">{c.label}</th>)}{actions && <th className="p-3" />}</tr></thead>
            <tbody>
              {data?.items.map((row) => (
                <tr key={row.id} className="border-b border-line/60 align-top hover:bg-canvas/40">
                  {columns.map((c) => <td key={c.key} className={c.className ?? "p-3"}>{c.render(row)}</td>)}
                  {actions && <td className="p-3 text-right"><div className="flex justify-end gap-1.5">{actions(row, reload)}</div></td>}
                </tr>
              ))}
              {data && !data.items.length && <tr><td colSpan={columns.length + 1} className="p-8 text-center text-muted">Nothing here.</td></tr>}
            </tbody>
          </table>
        )}
      </div>
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted">{data.total} total</span>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button>
            <span className="self-center">Page {page} / {data.pages}</span>
            <Button size="sm" variant="outline" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next</Button>
          </div>
        </div>
      )}
    </div>
  );
}

/** Prompt-based confirmation with a required reason; returns null if cancelled. */
export function askReason(msg: string, min = 3): string | null {
  const r = prompt(msg);
  if (r === null) return null;
  if (r.trim().length < min) { alert(`Please enter at least ${min} characters.`); return null; }
  return r.trim();
}
