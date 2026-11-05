import type { Condition, OrderStatus, VerificationLevel } from "./types";

/** Format a decimal money string as Naira without float arithmetic on the value. */
export function naira(value: string | number | null | undefined, opts: { kobo?: boolean } = {}): string {
  if (value === null || value === undefined || value === "") return "—";
  const s = String(value);
  const negative = s.startsWith("-");
  const [whole, frac = "00"] = s.replace("-", "").split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const kobo = opts.kobo && frac !== "00" ? `.${frac.padEnd(2, "0").slice(0, 2)}` : "";
  return `${negative ? "-" : ""}₦${grouped}${kobo}`;
}

/** Compact Naira for tight spaces: ₦1.5M, ₦350k. Display only. */
export function nairaCompact(value: string): string {
  const n = Number(value);
  if (n >= 1_000_000_000) return `₦${trim(n / 1_000_000_000)}B`;
  if (n >= 1_000_000) return `₦${trim(n / 1_000_000)}M`;
  if (n >= 10_000) return `₦${trim(n / 1000)}k`;
  return naira(value);
}

function trim(n: number) {
  return n.toFixed(n < 10 ? 2 : 1).replace(/\.?0+$/, "");
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Deterministic formatting (no Intl): server (Node ICU) and browser output must match for hydration.
// Times are shown in West Africa Time (UTC+1, no DST).
function wat(iso: string) {
  return new Date(new Date(iso).getTime() + 3600_000);
}

export function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d ago`;
  const d = wat(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}

export function date(iso: string | null | undefined, withTime = false): string {
  if (!iso) return "—";
  const d = wat(iso);
  const base = `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  if (!withTime) return base;
  return `${base}, ${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
}

export const CONDITION_LABEL: Record<Condition, string> = {
  brand_new: "Brand New",
  foreign_used: "Foreign Used",
  nigerian_used: "Nigerian Used",
  refurbished: "Refurbished",
};

export const VERIFICATION_LABEL: Record<VerificationLevel, string> = {
  unverified: "Unverified",
  phone_verified: "Phone verified",
  identity_verified: "ID verified",
  business_verified: "Business verified",
};

export function isVerified(level: VerificationLevel) {
  return level === "identity_verified" || level === "business_verified";
}

export const ORDER_STATUS: Record<OrderStatus, { label: string; tone: "neutral" | "info" | "warn" | "good" | "bad" }> = {
  pending_payment: { label: "Awaiting payment", tone: "warn" },
  payment_confirmed: { label: "Payment confirmed", tone: "info" },
  funds_safeguarded: { label: "Funds safeguarded", tone: "info" },
  awaiting_seller: { label: "Awaiting seller", tone: "info" },
  processing: { label: "Processing", tone: "info" },
  dispatched: { label: "Dispatched", tone: "info" },
  delivered: { label: "Delivered", tone: "info" },
  awaiting_buyer_confirmation: { label: "Awaiting confirmation", tone: "warn" },
  completed: { label: "Completed", tone: "good" },
  disputed: { label: "Disputed", tone: "bad" },
  refund_pending: { label: "Refund pending", tone: "warn" },
  refunded: { label: "Refunded", tone: "neutral" },
  cancelled: { label: "Cancelled", tone: "neutral" },
};

export function titleCase(s: string) {
  return s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export const NG_STATES = [
  "Abia", "Abuja", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno", "Cross River",
  "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "Gombe", "Imo", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi",
  "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto",
  "Taraba", "Yobe", "Zamfara",
];

/** Normalise user-typed money to a 2dp decimal string (no floats). Returns null if invalid. */
export function toMoneyString(input: string): string | null {
  const clean = input.replace(/[₦,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const [w, f = ""] = clean.split(".");
  return `${BigInt(w).toString()}.${f.padEnd(2, "0")}`;
}
