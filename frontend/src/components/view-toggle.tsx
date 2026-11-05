"use client";

import { LayoutGrid, List } from "lucide-react";
import clsx from "clsx";
import { useSyncExternalStore } from "react";

export type ListingView = "grid" | "list";
const KEY = "gng_view";
const listeners = new Set<() => void>();

function subscribe(cb: () => void) {
  listeners.add(cb);
  window.addEventListener("storage", cb);
  return () => {
    listeners.delete(cb);
    window.removeEventListener("storage", cb);
  };
}

/** Grid/list preference, remembered per device. Server and first client render use "grid" (hydration-safe). */
export function useListingView(): [ListingView, (v: ListingView) => void] {
  const view = useSyncExternalStore(
    subscribe,
    () => (localStorage.getItem(KEY) === "list" ? "list" : "grid"),
    () => "grid",
  ) as ListingView;
  const set = (v: ListingView) => {
    localStorage.setItem(KEY, v);
    listeners.forEach((l) => l());
  };
  return [view, set];
}

/** Single toggle button: shows the icon of the layout you'll switch to. */
export function ViewToggle({ className }: { className?: string }) {
  const [view, setView] = useListingView();
  const next: ListingView = view === "grid" ? "list" : "grid";
  const Icon = next === "list" ? List : LayoutGrid;
  const label = next === "list" ? "Switch to list view" : "Switch to grid view";
  return (
    <button
      type="button"
      onClick={() => setView(next)}
      aria-label={label}
      title={label}
      className={clsx(
        "grid size-10 shrink-0 place-items-center rounded-lg border border-line bg-white text-ink shadow-sm transition hover:border-brand-600 hover:text-brand-700",
        className,
      )}
    >
      <Icon className="size-5" />
    </button>
  );
}
