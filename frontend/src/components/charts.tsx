"use client";

/**
 * Small, dependency-free SVG charts for the admin overview.
 * Specs (see the dataviz method): 2px lines, ~10% area wash, columns ≤24px with 4px rounded data-ends
 * square at the baseline, 2px surface gaps, hairline solid gridlines, ≥8px end markers with a 2px surface
 * ring, text in ink tokens (never the series colour), crosshair + tooltip on lines, per-mark tooltips on
 * bars, keyboard focus mirrors hover, and every chart has a table view.
 */

import { useEffect, useId, useMemo, useRef, useState } from "react";
import clsx from "clsx";
import { Table2 } from "lucide-react";

export const SERIES = { brand: "#2f7a4a", alt: "#2a78d6" } as const; // green + blue: validated CVD pair
const SURFACE = "#ffffff";
const GRID = "#e2e8e3";
const AXIS_TEXT = "#55635a";

/* ---------------- helpers ---------------- */

export type Datum = { date: string } & Record<string, string | number>;
const val = (d: Datum, k: string) => Number(d[k] ?? 0);

function useWidth<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.round(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, w] as const;
}

function niceMax(v: number) {
  if (v <= 0) return 4;
  const raw = v / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? raw;
  return step * 4;
}

export function compact(n: number) {
  const a = Math.abs(n);
  if (a >= 1e9) return `${+(n / 1e9).toFixed(1)}B`;
  if (a >= 1e6) return `${+(n / 1e6).toFixed(1)}M`;
  if (a >= 1e4) return `${+(n / 1e3).toFixed(0)}K`;
  return n.toLocaleString("en-US");
}
export const nairaCompact = (n: number) => `₦${compact(n)}`;
export const nairaFull = (n: number) => `₦${Math.round(n).toLocaleString("en-US")}`;

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function shortDate(iso: string) {
  const [, m, d] = iso.split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}

function Tooltip({ x, y, width, children }: { x: number; y: number; width: number; children: React.ReactNode }) {
  const left = Math.min(Math.max(x, 70), width - 70);
  return (
    <div role="status" className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg bg-ink px-3 py-2 text-xs text-white shadow-lg"
      style={{ left, top: y - 10 }}>
      {children}
    </div>
  );
}

/* ---------------- card with table view ---------------- */

export function ChartCard({ title, subtitle, headline, legend, table, children, className }: {
  title: string; subtitle?: string; headline?: React.ReactNode; legend?: React.ReactNode;
  table: { head: string[]; rows: (string | number)[][] }; children: React.ReactNode; className?: string;
}) {
  const [showTable, setShowTable] = useState(false);
  return (
    <section className={clsx("card flex flex-col p-4 sm:p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="font-semibold">{title}</h3>
          {subtitle && <p className="text-xs text-muted">{subtitle}</p>}
        </div>
        <button type="button" onClick={() => setShowTable(!showTable)} aria-pressed={showTable}
          className={clsx("inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs font-medium", showTable ? "bg-brand-50 text-brand-800" : "text-muted hover:bg-canvas hover:text-ink")}>
          <Table2 className="size-3.5" />{showTable ? "Chart" : "Table"}
        </button>
      </div>
      {headline && <div className="mt-2">{headline}</div>}
      {legend && <div className="mt-2">{legend}</div>}
      <div className="mt-3 flex-1">
        {showTable ? (
          <div className="max-h-64 overflow-auto rounded-lg ring-1 ring-line">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-canvas text-left text-xs text-muted"><tr>{table.head.map((h, i) => <th key={h} className={clsx("px-3 py-2 font-semibold", i > 0 && "text-right")}>{h}</th>)}</tr></thead>
              <tbody className="divide-y divide-line/70">
                {table.rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j} className={clsx("px-3 py-1.5", j > 0 && "text-right tabular-nums")}>{c}</td>)}</tr>)}
              </tbody>
            </table>
          </div>
        ) : children}
      </div>
    </section>
  );
}

export function Legend({ items, kind = "line" }: { items: { label: string; color: string }[]; kind?: "line" | "rect" }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink/80">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          {kind === "line"
            ? <span className="h-0.5 w-3.5 rounded-full" style={{ background: i.color }} />
            : <span className="size-2.5 rounded-sm" style={{ background: i.color }} />}
          {i.label}
        </li>
      ))}
    </ul>
  );
}

/* ---------------- line / area ---------------- */

type LineSeries = { key: string; label: string; color: string };

export function LineChart({ data, series, area, height = 220, format = compact, tooltipFormat }: {
  data: Datum[];
  series: LineSeries[];
  area?: boolean;
  height?: number;
  format?: (n: number) => string;
  tooltipFormat?: (n: number) => string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const gid = useId().replace(/:/g, "");
  const pad = { t: 12, r: series.length === 1 ? 16 : 12, b: 26, l: 44 };
  const max = useMemo(() => niceMax(Math.max(0, ...data.flatMap((d) => series.map((s) => val(d, s.key))))), [data, series]);
  const iw = Math.max(0, width - pad.l - pad.r);
  const ih = height - pad.t - pad.b;
  const x = (i: number) => pad.l + (data.length <= 1 ? iw / 2 : (i / (data.length - 1)) * iw);
  const y = (v: number) => pad.t + ih - (v / max) * ih;
  const ticks = [0, 1, 2, 3, 4].map((i) => (max / 4) * i);
  const labelEvery = Math.ceil(data.length / Math.max(2, Math.floor(iw / 64)));
  const tf = tooltipFormat ?? format;

  const pick = (clientX: number, el: SVGSVGElement) => {
    const r = el.getBoundingClientRect();
    const px = clientX - r.left - pad.l;
    setHover(Math.max(0, Math.min(data.length - 1, Math.round((px / iw) * (data.length - 1)))));
  };

  return (
    <div ref={ref} className="relative">
      {width > 0 && (
        <svg width={width} height={height} role="img" tabIndex={0}
          aria-label={`${series.map((s) => s.label).join(" and ")} over ${data.length} days. Use arrow keys to read values.`}
          className="block outline-none focus-visible:ring-2 focus-visible:ring-brand-400 rounded-md"
          onPointerMove={(e) => pick(e.clientX, e.currentTarget)} onPointerLeave={() => setHover(null)}
          onFocus={() => setHover(data.length - 1)} onBlur={() => setHover(null)}
          onKeyDown={(e) => {
            if (e.key === "ArrowLeft") setHover((h) => Math.max(0, (h ?? data.length - 1) - 1));
            if (e.key === "ArrowRight") setHover((h) => Math.min(data.length - 1, (h ?? 0) + 1));
          }}>
          <defs>
            {series.map((s) => (
              <linearGradient key={s.key} id={`${gid}-${s.key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor={s.color} stopOpacity="0.14" />
                <stop offset="1" stopColor={s.color} stopOpacity="0.02" />
              </linearGradient>
            ))}
          </defs>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth={1} />
              <text x={pad.l - 8} y={y(t)} textAnchor="end" dominantBaseline="middle" fontSize={11} fill={AXIS_TEXT}>{format(t)}</text>
            </g>
          ))}
          {data.map((d, i) => (i % labelEvery === 0 || i === data.length - 1) && (i === data.length - 1 || data.length - 1 - i >= labelEvery / 2) ? (
            <text key={d.date} x={x(i)} y={height - 8} textAnchor={i === 0 ? "start" : i === data.length - 1 ? "end" : "middle"} fontSize={11} fill={AXIS_TEXT}>{shortDate(d.date)}</text>
          ) : null)}
          {series.map((s) => {
            const pts = data.map((d, i) => `${x(i)},${y(val(d, s.key))}`);
            return (
              <g key={s.key}>
                {area && <path d={`M${x(0)},${y(0)} L${pts.join(" L")} L${x(data.length - 1)},${y(0)} Z`} fill={`url(#${gid}-${s.key})`} />}
                <polyline points={pts.join(" ")} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
                {/* end marker: ≥8px with a 2px surface ring */}
                <circle cx={x(data.length - 1)} cy={y(data.length ? val(data[data.length - 1], s.key) : 0)} r={4} fill={s.color} stroke={SURFACE} strokeWidth={2} />
              </g>
            );
          })}
          {hover !== null && (
            <g>
              <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={pad.t + ih} stroke="#9ca3af" strokeWidth={1} />
              {series.map((s) => <circle key={s.key} cx={x(hover)} cy={y(val(data[hover], s.key))} r={4.5} fill={s.color} stroke={SURFACE} strokeWidth={2} />)}
            </g>
          )}
        </svg>
      )}
      {hover !== null && width > 0 && (
        <Tooltip x={x(hover)} y={Math.min(...series.map((s) => y(val(data[hover], s.key))))} width={width}>
          <p className="mb-1 text-[11px] text-white/70">{shortDate(data[hover].date)}</p>
          {series.map((s) => (
            <p key={s.key} className="flex items-center gap-2 whitespace-nowrap">
              <span className="h-0.5 w-3 rounded-full" style={{ background: s.color }} />
              <b className="tabular-nums">{tf(val(data[hover], s.key))}</b>
              {series.length > 1 && <span className="text-white/70">{s.label}</span>}
            </p>
          ))}
        </Tooltip>
      )}
    </div>
  );
}

/* ---------------- columns ---------------- */

export function ColumnChart({ data, valueKey, color = SERIES.brand, height = 200, format = compact, label }: {
  data: Datum[]; valueKey: string; color?: string; height?: number; format?: (n: number) => string; label: string;
}) {
  const [ref, width] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const pad = { t: 12, r: 8, b: 26, l: 36 };
  const max = niceMax(Math.max(0, ...data.map((d) => val(d, valueKey))));
  const iw = Math.max(0, width - pad.l - pad.r);
  const ih = height - pad.t - pad.b;
  const slot = data.length ? iw / data.length : 0;
  const bw = Math.max(2, Math.min(24, slot - 2)); // ≤24px, 2px surface gap between neighbours
  const y = (v: number) => pad.t + ih - (v / max) * ih;
  const labelEvery = Math.ceil(data.length / Math.max(2, Math.floor(iw / 64)));
  const r = Math.min(4, bw / 2);

  return (
    <div ref={ref} className="relative">
      {width > 0 && (
        <svg width={width} height={height} role="img" aria-label={`${label} per day`} className="block" onPointerLeave={() => setHover(null)}>
          {[0, 1, 2, 3, 4].map((i) => (max / 4) * i).map((t) => (
            <g key={t}>
              <line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} stroke={GRID} strokeWidth={1} />
              <text x={pad.l - 8} y={y(t)} textAnchor="end" dominantBaseline="middle" fontSize={11} fill={AXIS_TEXT}>{format(t)}</text>
            </g>
          ))}
          {data.map((d, i) => {
            const v = val(d, valueKey);
            const cx = pad.l + slot * i + slot / 2;
            const top = y(v);
            const h = pad.t + ih - top;
            const x0 = cx - bw / 2;
            const path = h <= 0 ? "" : h < r
              ? `M${x0},${pad.t + ih} V${top} H${x0 + bw} V${pad.t + ih} Z`
              : `M${x0},${pad.t + ih} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + bw - r} Q${x0 + bw},${top} ${x0 + bw},${top + r} V${pad.t + ih} Z`;
            return (
              <g key={d.date}>
                {path && <path d={path} fill={color} opacity={hover === null || hover === i ? 1 : 0.45} />}
                {/* hit target: the whole slot, taller than the mark */}
                <rect x={pad.l + slot * i} y={pad.t} width={slot} height={ih} fill="transparent" tabIndex={0}
                  aria-label={`${shortDate(d.date)}: ${format(v)} ${label.toLowerCase()}`}
                  onPointerEnter={() => setHover(i)} onFocus={() => setHover(i)} onBlur={() => setHover(null)} className="outline-none" />
                {(i % labelEvery === 0 || i === data.length - 1) && (i === data.length - 1 || data.length - 1 - i >= labelEvery / 2) && (
                  <text x={i === data.length - 1 ? Math.min(cx + bw / 2, width - 2) : i === 0 ? Math.max(cx - bw / 2, pad.l) : cx} y={height - 8} textAnchor={i === 0 ? "start" : i === data.length - 1 ? "end" : "middle"} fontSize={11} fill={AXIS_TEXT}>{shortDate(d.date)}</text>
                )}
              </g>
            );
          })}
        </svg>
      )}
      {hover !== null && width > 0 && (
        <Tooltip x={pad.l + slot * hover + slot / 2} y={y(val(data[hover], valueKey))} width={width}>
          <p className="text-[11px] text-white/70">{shortDate(data[hover].date)}</p>
          <p className="whitespace-nowrap"><b className="tabular-nums">{format(val(data[hover], valueKey))}</b> <span className="text-white/70">{label.toLowerCase()}</span></p>
        </Tooltip>
      )}
    </div>
  );
}

/* ---------------- horizontal bars (ranked categories) ---------------- */

export function BarList({ items, color = SERIES.brand, format = (n: number) => n.toLocaleString("en-US") }: {
  items: { label: string; value: number }[]; color?: string; format?: (n: number) => string;
}) {
  const max = Math.max(1, ...items.map((i) => i.value));
  if (!items.length) return <p className="py-8 text-center text-sm text-muted">No data in this period yet.</p>;
  return (
    <ul className="space-y-2.5">
      {items.map((i) => (
        <li key={i.label} className="group" title={`${i.label}: ${format(i.value)}`}>
          <div className="mb-1 flex items-baseline justify-between gap-3 text-sm">
            <span className="truncate text-ink/80">{i.label}</span>
            <span className="shrink-0 font-semibold tabular-nums">{format(i.value)}</span>
          </div>
          <div className="h-2.5 rounded-full bg-canvas">
            <div className="h-full rounded-full transition-[width] duration-500 group-hover:opacity-80" style={{ width: `${Math.max(2, (i.value / max) * 100)}%`, background: color }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/* ---------------- one whole split into parts ---------------- */

export function SegmentBar({ parts }: { parts: { label: string; value: number; color: string }[] }) {
  const total = parts.reduce((n, p) => n + p.value, 0);
  if (!total) return <p className="py-6 text-center text-sm text-muted">No paid orders in this period yet.</p>;
  return (
    <div>
      <div className="flex h-4 gap-0.5 overflow-hidden rounded-full" role="img" aria-label={parts.map((p) => `${p.label} ${p.value}`).join(", ")}>
        {parts.filter((p) => p.value > 0).map((p) => (
          <div key={p.label} title={`${p.label}: ${p.value} (${Math.round((p.value / total) * 100)}%)`} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} />
        ))}
      </div>
      <ul className="mt-3 grid grid-cols-2 gap-3">
        {parts.map((p) => (
          <li key={p.label} className="rounded-lg bg-canvas p-3">
            <p className="flex items-center gap-1.5 text-xs text-muted"><span className="size-2.5 rounded-sm" style={{ background: p.color }} />{p.label}</p>
            <p className="mt-1 text-lg font-bold tabular-nums">{Math.round((p.value / total) * 100)}%</p>
            <p className="text-xs text-muted">{p.value.toLocaleString("en-US")} order{p.value === 1 ? "" : "s"}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
