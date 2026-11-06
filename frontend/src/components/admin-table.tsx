"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Inbox, RefreshCw, Search, X } from "lucide-react";
import clsx from "clsx";
import type { Page } from "@/lib/types";
import { useApi } from "@/lib/hooks";
import { Alert, Button } from "./ui";

export { askReason } from "./admin-ui";

export type Col<T> = { key: string; label: string; render: (row: T) => React.ReactNode; className?: string };

const PAGE_SIZE = 25;

/**
 * Admin list: live search, filter slot, loading skeleton, friendly empty state and pagination.
 * Desktop/tablet renders a table; phones get one card per row (first column as the title).
 */
export function AdminTable<T extends { id: string }>({
  path,
  columns,
  query,
  searchable,
  searchPlaceholder = "Search…",
  filters,
  actions,
  reloadKey,
  emptyText = "Nothing here yet.",
}: {
  path: string;
  columns: Col<T>[];
  query?: Record<string, unknown>;
  searchable?: boolean;
  searchPlaceholder?: string;
  filters?: React.ReactNode;
  actions?: (row: T, reload: () => void) => React.ReactNode;
  reloadKey?: number;
  emptyText?: string;
}) {
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");
  const [applied, setApplied] = useState("");
  const qs = JSON.stringify(query ?? {});

  // Live search: apply 350ms after typing stops.
  useEffect(() => {
    const t = setTimeout(() => { setApplied(q.trim()); setPage(1); }, 350);
    return () => clearTimeout(t);
  }, [q]);
  // Changing a filter returns to the first page.
  useEffect(() => { void Promise.resolve().then(() => setPage(1)); }, [qs]);

  const { data, error, loading, reload } = useApi<Page<T>>(path, { ...query, q: applied || undefined, page, page_size: PAGE_SIZE, _k: reloadKey });
  const [title, ...rest] = columns;
  const from = data && data.total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const to = data ? Math.min(page * PAGE_SIZE, data.total) : 0;

  return (
    <div className="space-y-3">
      {(searchable || filters) && (
        <div className="flex flex-col gap-2 lg:flex-row lg:items-center">
          {searchable && (
            <div className="relative lg:w-80">
              <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
              <input className="input pl-9 pr-9" placeholder={searchPlaceholder} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
              {q && <button type="button" aria-label="Clear search" onClick={() => setQ("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full p-1 text-muted hover:bg-canvas"><X className="size-4" /></button>}
            </div>
          )}
          {filters && <div className="min-w-0 flex-1">{filters}</div>}
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-muted">
        <span aria-live="polite">{data ? (data.total ? `Showing ${from}–${to} of ${data.total.toLocaleString()}` : "No results") : "Loading…"}{applied && <> for “{applied}”</>}</span>
        <button type="button" onClick={reload} className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-white hover:text-ink" aria-label="Refresh">
          <RefreshCw className={clsx("size-3.5", loading && "animate-spin")} />Refresh
        </button>
      </div>

      {error && <Alert tone="bad">{error}</Alert>}

      {!data && loading ? <SkeletonRows cols={columns.length} /> : data && !data.items.length ? (
        <div className="card grid place-items-center gap-2 px-6 py-14 text-center">
          <span className="grid size-12 place-items-center rounded-2xl bg-canvas text-muted"><Inbox className="size-6" /></span>
          <p className="font-semibold">{applied ? "No matches" : emptyText}</p>
          <p className="text-sm text-muted">{applied ? "Try a different search or filter." : "When there's something to review it will show up here."}</p>
        </div>
      ) : data ? (
        <>
          {/* Tablet & desktop */}
          <div className={clsx("card hidden overflow-x-auto md:block", loading && "opacity-70")}>
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-[1]">
                <tr className="border-b border-line bg-canvas/80 text-left text-[11px] uppercase tracking-wider text-muted backdrop-blur">
                  {columns.map((c) => <th key={c.key} className="whitespace-nowrap px-4 py-3 font-semibold">{c.label}</th>)}
                  {actions && <th className="px-4 py-3 text-right font-semibold">Actions</th>}
                </tr>
              </thead>
              <tbody className="divide-y divide-line/70">
                {data.items.map((row) => (
                  <tr key={row.id} className="align-top transition-colors hover:bg-brand-50/40">
                    {columns.map((c) => <td key={c.key} className={c.className ?? "px-4 py-3"}>{c.render(row)}</td>)}
                    {actions && <td className="px-4 py-3"><div className="flex flex-wrap justify-end gap-1.5">{actions(row, reload)}</div></td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {/* Phones */}
          <ul className={clsx("space-y-2 md:hidden", loading && "opacity-70")}>
            {data.items.map((row) => (
              <li key={row.id} className="card p-4">
                <div className="text-sm">{title.render(row)}</div>
                {rest.length > 0 && (
                  <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2.5 border-t border-line/70 pt-3 text-sm">
                    {rest.map((c) => (
                      <div key={c.key} className="min-w-0">
                        <dt className="text-[11px] font-semibold uppercase tracking-wider text-muted">{c.label}</dt>
                        <dd className="mt-0.5 break-words">{c.render(row)}</dd>
                      </div>
                    ))}
                  </dl>
                )}
                {actions && <div className="mt-3 flex flex-wrap gap-1.5 border-t border-line/70 pt-3 empty:hidden">{actions(row, reload)}</div>}
              </li>
            ))}
          </ul>
        </>
      ) : null}

      {data && data.pages > 1 && (
        <nav className="flex items-center justify-between gap-2 text-sm" aria-label="Pagination">
          <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft className="size-4" />Previous</Button>
          <span className="text-muted">Page <b className="text-ink">{page}</b> of {data.pages}</span>
          <Button size="sm" variant="outline" disabled={page >= data.pages} onClick={() => setPage(page + 1)}>Next<ChevronRight className="size-4" /></Button>
        </nav>
      )}
    </div>
  );
}

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <div className="card divide-y divide-line/70" aria-busy="true" aria-label="Loading">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="flex items-center gap-4 px-4 py-4">
          {Array.from({ length: Math.min(cols, 4) }, (_, j) => (
            <span key={j} className={clsx("skeleton h-4 rounded", j === 0 ? "w-1/3" : "hidden flex-1 md:block")} />
          ))}
        </div>
      ))}
    </div>
  );
}
