"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Heart, Home, MessageCircle, Plus, User } from "lucide-react";
import { useAuth } from "./auth-provider";
import { useCounts } from "./header";
import { useIsAdminArea } from "@/lib/admin-area";

/** Thumb-reachable bottom navigation for phones — the primary way most Nigerian users browse. */
export function MobileNav() {
  const pathname = usePathname();
  const { user } = useAuth();
  const counts = useCounts();
  const adminArea = useIsAdminArea();
  if (adminArea || pathname.startsWith("/messages/") || pathname.startsWith("/item/")) return null;
  const items = [
    { href: "/", label: "Home", icon: Home, active: pathname === "/" },
    { href: "/saved", label: "Saved", icon: Heart, active: pathname.startsWith("/saved") },
    null,
    { href: "/messages", label: "Messages", icon: MessageCircle, active: pathname.startsWith("/messages"), badge: counts.messages },
    { href: user ? "/account" : "/login", label: user ? "Account" : "Sign in", icon: User, active: pathname.startsWith("/account") },
  ];
  return (
    <nav
      aria-label="Primary"
      className="site-mobile-nav fixed inset-x-0 bottom-0 z-40 border-t border-line bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
    >
      <ul className="grid h-16 grid-cols-5">
        {items.map((it, i) =>
          it === null ? (
            <li key="sell" className="flex items-start justify-center">
              <Link
                href={user?.seller ? "/seller/products/new" : "/seller/onboarding"}
                className="-mt-5 flex flex-col items-center gap-0.5 text-[11px] font-semibold text-ink"
              >
                <span className="grid size-13 place-items-center rounded-full bg-accent-500 shadow-lg ring-4 ring-white">
                  <Plus className="size-6" />
                </span>
                Sell
              </Link>
            </li>
          ) : (
            <li key={i}>
              <Link
                href={it.href}
                aria-current={it.active ? "page" : undefined}
                className={clsx("relative flex h-full flex-col items-center justify-center gap-0.5 text-[11px] font-medium", it.active ? "text-brand-700" : "text-muted")}
              >
                <it.icon className={clsx("size-5", it.active && "fill-brand-100")} />
                {it.label}
                {!!it.badge && (
                  <span className="absolute right-[22%] top-2 grid min-w-4 place-items-center rounded-full bg-red-500 px-1 text-[10px] font-bold leading-4 text-white">
                    {it.badge}
                  </span>
                )}
              </Link>
            </li>
          ),
        )}
      </ul>
    </nav>
  );
}
