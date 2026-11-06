import { BadgeCheck, Crown, ShieldCheck } from "lucide-react";
import clsx from "clsx";
import type { VerificationLevel } from "@/lib/types";
import { isVerified, VERIFICATION_LABEL } from "@/lib/format";

export function VerifiedBadge({ level, compact }: { level: VerificationLevel; compact?: boolean }) {
  if (!isVerified(level)) return null;
  return (
    <span
      title={VERIFICATION_LABEL[level]}
      className="relative inline-flex items-center gap-0.5 rounded-full bg-sky-50 px-1.5 py-0.5 text-[11px] font-semibold text-sky-700"
    >
      <BadgeCheck className="size-3.5" aria-hidden />
      {!compact && (level === "business_verified" ? "Verified business" : "Verified")}
      {compact && <span className="sr-only">{VERIFICATION_LABEL[level]}</span>}
    </span>
  );
}

export function PremiumBadge({ compact, className }: { compact?: boolean; className?: string }) {
  return (
    <span
      title="Premium Seller"
      className={clsx(
        "relative inline-flex items-center gap-0.5 rounded-full bg-gradient-to-r from-amber-200 to-yellow-100 px-1.5 py-0.5 text-[11px] font-bold text-premium-600 ring-1 ring-amber-300",
        className,
      )}
    >
      <Crown className="size-3" aria-hidden />
      {compact ? <span className="sr-only">Premium Seller</span> : "Premium"}
    </span>
  );
}

export function ProtectedBadge({ className }: { className?: string }) {
  return (
    <span className={clsx("inline-flex items-center gap-1 text-[11px] font-semibold text-brand-700", className)}>
      <ShieldCheck className="size-3.5" aria-hidden />
      Protected Checkout
    </span>
  );
}

export function FlexBadge() {
  return (
    <span className="inline-flex items-center rounded-full bg-violet-50 px-1.5 py-0.5 text-[11px] font-semibold text-violet-700">
      Goods Flex
    </span>
  );
}
