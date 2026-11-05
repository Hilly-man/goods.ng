"use client";

import { Heart } from "lucide-react";
import clsx from "clsx";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { http } from "@/lib/api";
import { useAuth } from "./auth-provider";
import { useToast } from "./ui";

export function FavouriteButton({
  productId,
  initial,
  className,
  withLabel,
}: {
  productId: string;
  initial?: boolean;
  className?: string;
  withLabel?: boolean;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [on, setOn] = useState(!!initial);
  const [busy, setBusy] = useState(false);

  async function toggle(e: React.MouseEvent) {
    e.preventDefault();
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(location.pathname)}`);
      return;
    }
    setBusy(true);
    const next = !on;
    setOn(next);
    try {
      if (next) await http.post(`/products/${productId}/favourite`);
      else await http.del(`/products/${productId}/favourite`);
      toast(next ? "Saved to your list" : "Removed from saved", "info");
    } catch {
      setOn(!next);
      toast("Could not update saved items", "bad");
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={busy}
      aria-pressed={on}
      aria-label={on ? "Remove from saved" : "Save item"}
      className={clsx(
        withLabel
          ? "inline-flex h-11 items-center gap-2 rounded-lg border border-line bg-white px-4 text-sm font-semibold hover:border-brand-600"
          : "grid size-8 place-items-center rounded-full bg-white/90 shadow-sm backdrop-blur transition hover:scale-105",
        className,
      )}
    >
      <Heart className={clsx("size-4", on ? "fill-red-500 text-red-500" : "text-ink/70")} />
      {withLabel && (on ? "Saved" : "Save")}
    </button>
  );
}
