import Link from "next/link";
import clsx from "clsx";

/** Goods.ng wordmark: a shield-tag mark (trust + price tag) and the name. */
export function Logo({ light, className }: { light?: boolean; className?: string }) {
  return (
    <Link href="/" className={clsx("inline-flex items-center gap-1.5 font-extrabold tracking-tight", className)} aria-label="Goods.ng home">
      <svg viewBox="0 0 32 32" className="size-7 shrink-0" aria-hidden>
        <path d="M16 2 4 6.5v8.2C4 22.4 9.2 28.6 16 30c6.8-1.4 12-7.6 12-15.3V6.5L16 2Z" fill={light ? "#fff" : "#057a48"} />
        <path d="m10.5 16.2 3.6 3.6 7.6-7.6" fill="none" stroke={light ? "#057a48" : "#fbbf24"} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className={clsx("text-xl", light ? "text-white" : "text-ink")}>
        Goods<span className={light ? "text-accent-400" : "text-brand-700"}>.ng</span>
      </span>
    </Link>
  );
}
