"use client";

import clsx from "clsx";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, ChevronDown, Info, Loader2, X, XCircle } from "lucide-react";
import { createContext, forwardRef, useCallback, useContext, useEffect, useId, useRef, useState } from "react";

type Variant = "primary" | "secondary" | "outline" | "ghost" | "danger" | "accent" | "whatsapp";
const VARIANTS: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 shadow-sm",
  accent: "bg-accent-500 text-ink hover:bg-accent-400 shadow-sm",
  secondary: "bg-brand-50 text-brand-800 hover:bg-brand-100",
  outline: "border border-line bg-white text-ink hover:border-brand-600 hover:text-brand-700",
  ghost: "text-ink hover:bg-black/5",
  danger: "bg-red-600 text-white hover:bg-red-700",
  whatsapp: "bg-[#25D366] text-white hover:bg-[#1ebe5b] shadow-sm",
};
const SIZES = { sm: "h-9 px-3 text-sm", md: "h-11 px-4 text-[15px]", lg: "h-12 px-5 text-base" };

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: keyof typeof SIZES;
  loading?: boolean;
  block?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", loading, block, className, children, disabled, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-60",
        VARIANTS[variant],
        SIZES[size],
        block && "w-full",
        className,
      )}
      {...rest}
    >
      {loading && <Loader2 className="size-4 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

export function ButtonLink({
  href,
  variant = "primary",
  size = "md",
  block,
  className,
  children,
  ...rest
}: { href: string; variant?: Variant; size?: keyof typeof SIZES; block?: boolean; className?: string; children: React.ReactNode } & Omit<
  React.AnchorHTMLAttributes<HTMLAnchorElement>,
  "href"
>) {
  return (
    <Link
      href={href}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition active:scale-[.98]",
        VARIANTS[variant],
        SIZES[size],
        block && "w-full",
        className,
      )}
      {...rest}
    >
      {children}
    </Link>
  );
}

export function Field({
  label,
  error,
  hint,
  children,
  htmlFor,
}: {
  label?: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
  htmlFor?: string;
}) {
  return (
    <div>
      {label && (
        <label className="label" htmlFor={htmlFor}>
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p role="alert" className="mt-1 text-sm text-red-600">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1 text-xs text-muted">{hint}</p>
      ) : null}
    </div>
  );
}

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string; hint?: string }>(
  function Input({ label, error, hint, className, id, ...rest }, ref) {
    const gen = useId();
    const fid = id ?? gen;
    return (
      <Field label={label} error={error} hint={hint} htmlFor={fid}>
        <input ref={ref} id={fid} aria-invalid={!!error} className={clsx("input", error && "border-red-500", className)} {...rest} />
      </Field>
    );
  },
);

export function Textarea({
  label,
  error,
  hint,
  className,
  id,
  ...rest
}: React.TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; error?: string; hint?: string }) {
  const gen = useId();
  const fid = id ?? gen;
  return (
    <Field label={label} error={error} hint={hint} htmlFor={fid}>
      <textarea id={fid} aria-invalid={!!error} className={clsx("input min-h-28", error && "border-red-500", className)} {...rest} />
    </Field>
  );
}

export function Select({
  label,
  error,
  hint,
  className,
  children,
  id,
  ...rest
}: React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string; error?: string; hint?: string }) {
  const gen = useId();
  const fid = id ?? gen;
  return (
    <Field label={label} error={error} hint={hint} htmlFor={fid}>
      <div className="relative">
        <select id={fid} aria-invalid={!!error} className={clsx("input appearance-none pr-9 disabled:cursor-not-allowed", error && "border-red-500", className)} {...rest}>
          {children}
        </select>
        <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
      </div>
    </Field>
  );
}

export function Checkbox({ label, ...rest }: React.InputHTMLAttributes<HTMLInputElement> & { label: React.ReactNode }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 text-sm">
      <input type="checkbox" className="mt-0.5 size-4 shrink-0 rounded accent-brand-700" {...rest} />
      <span>{label}</span>
    </label>
  );
}

const TONES = {
  neutral: "bg-black/5 text-ink/80",
  info: "bg-sky-50 text-sky-800 ring-sky-200",
  warn: "bg-amber-50 text-amber-800 ring-amber-200",
  good: "bg-brand-50 text-brand-800 ring-brand-200",
  bad: "bg-red-50 text-red-700 ring-red-200",
  premium: "bg-gradient-to-r from-amber-100 to-yellow-50 text-premium-600 ring-amber-300",
  dark: "bg-ink text-white",
};
export function Badge({
  tone = "neutral",
  children,
  className,
}: {
  tone?: keyof typeof TONES;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={clsx("inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ring-1 ring-transparent", TONES[tone], className)}>
      {children}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return <Loader2 className={clsx("size-5 animate-spin text-brand-700", className)} aria-label="Loading" />;
}

export function PageLoader() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner className="size-7" />
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("skeleton rounded-md", className)} />;
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  body?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-14 text-center">
      {icon && <div className="mb-3 grid size-14 place-items-center rounded-full bg-brand-50 text-brand-700">{icon}</div>}
      <h3 className="text-base font-semibold">{title}</h3>
      {body && <p className="mt-1 max-w-sm text-sm text-muted">{body}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Alert({
  tone = "info",
  title,
  children,
  className,
}: {
  tone?: "info" | "warn" | "good" | "bad";
  title?: string;
  children?: React.ReactNode;
  className?: string;
}) {
  const Icon = { info: Info, warn: AlertTriangle, good: CheckCircle2, bad: XCircle }[tone];
  const cls = {
    info: "bg-sky-50 text-sky-900 ring-sky-200",
    warn: "bg-amber-50 text-amber-900 ring-amber-200",
    good: "bg-brand-50 text-brand-900 ring-brand-200",
    bad: "bg-red-50 text-red-900 ring-red-200",
  }[tone];
  return (
    <div role={tone === "bad" ? "alert" : "status"} className={clsx("flex gap-3 rounded-xl p-3.5 text-sm ring-1", cls, className)}>
      <Icon className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        {children && <div className={clsx(title && "mt-0.5", "opacity-90")}>{children}</div>}
      </div>
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
  size = "md",
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  size?: "sm" | "md" | "lg";
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      className={clsx(
        "m-0 mt-auto w-full max-w-none rounded-t-2xl p-0 shadow-[var(--shadow-pop)] backdrop:bg-black/50 sm:m-auto sm:rounded-2xl",
        { sm: "sm:max-w-sm", md: "sm:max-w-lg", lg: "sm:max-w-2xl" }[size],
      )}
      aria-labelledby="modal-title"
    >
      {open && (
        <div className="flex max-h-[90dvh] flex-col">
          <div className="flex items-center justify-between border-b border-line px-5 py-4">
            <h2 id="modal-title" className="text-lg font-semibold">
              {title}
            </h2>
            <button onClick={onClose} className="rounded-full p-1.5 hover:bg-black/5" aria-label="Close">
              <X className="size-5" />
            </button>
          </div>
          <div className="overflow-y-auto px-5 py-4">{children}</div>
          {footer && <div className="flex justify-end gap-2 border-t border-line px-5 py-3">{footer}</div>}
        </div>
      )}
    </dialog>
  );
}

export function Tabs<T extends string>({
  tabs,
  value,
  onChange,
}: {
  tabs: { value: T; label: string; count?: number }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div role="tablist" className="scrollbar-none flex gap-1 overflow-x-auto border-b border-line">
      {tabs.map((t) => (
        <button
          key={t.value}
          role="tab"
          aria-selected={value === t.value}
          onClick={() => onChange(t.value)}
          className={clsx(
            "-mb-px shrink-0 border-b-2 px-3 py-2.5 text-sm font-medium transition",
            value === t.value ? "border-brand-700 text-brand-800" : "border-transparent text-muted hover:text-ink",
          )}
        >
          {t.label}
          {t.count !== undefined && t.count > 0 && (
            <span className="ml-1.5 rounded-full bg-brand-700 px-1.5 text-[11px] text-white">{t.count}</span>
          )}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value, hint, icon }: { label: string; value: React.ReactNode; hint?: string; icon?: React.ReactNode }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between text-sm text-muted">
        <span>{label}</span>
        {icon}
      </div>
      <div className="mt-1.5 text-2xl font-bold tracking-tight">{value}</div>
      {hint && <div className="mt-0.5 text-xs text-muted">{hint}</div>}
    </div>
  );
}

// ---------------- toasts ----------------
type Toast = { id: number; tone: "good" | "bad" | "info"; text: string };
const ToastCtx = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "good") => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, tone, text }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4000);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" className="pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 md:bottom-6">
        {items.map((t) => (
          <div
            key={t.id}
            className={clsx(
              "pointer-events-auto flex max-w-md items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium text-white shadow-[var(--shadow-pop)]",
              t.tone === "good" ? "bg-brand-800" : t.tone === "bad" ? "bg-red-700" : "bg-ink",
            )}
          >
            {t.tone === "good" ? <CheckCircle2 className="size-4" /> : t.tone === "bad" ? <XCircle className="size-4" /> : <Info className="size-4" />}
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

export const useToast = () => useContext(ToastCtx);
