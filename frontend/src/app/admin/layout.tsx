"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Suspense } from "react";
import { PageLoader } from "@/components/ui";
import { BadgeCheck, BarChart3, BookOpen, CalendarClock, Crown, FileWarning, Flag, FolderTree, Gavel, Landmark, LayoutDashboard, Megaphone, Package, Receipt, RotateCcw, Settings, Star, Store, Users } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { useApi } from "@/lib/hooks";

const NAV = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, perm: "analytics.view", exact: true },
  { href: "/admin/users", label: "Users", icon: Users, perm: "users.manage" },
  { href: "/admin/sellers", label: "Sellers", icon: Store, perm: "sellers.verify" },
  { href: "/admin/verifications", label: "Seller verification", icon: BadgeCheck, perm: "sellers.verify" },
  { href: "/admin/products", label: "Products", icon: Package, perm: "listings.moderate" },
  { href: "/admin/categories", label: "Categories", icon: FolderTree, perm: "categories.manage" },
  { href: "/admin/orders", label: "Orders", icon: Receipt, perm: "orders.view" },
  { href: "/admin/payments", label: "Payments", icon: BarChart3, perm: "payments.view" },
  { href: "/admin/escrow", label: "Escrow & ledger", icon: Landmark, perm: "payments.view" },
  { href: "/admin/disputes", label: "Disputes", icon: Gavel, perm: "disputes.resolve" },
  { href: "/admin/refunds", label: "Refunds", icon: RotateCcw, perm: "refunds.approve" },
  { href: "/admin/bnpl", label: "BNPL monitoring", icon: CalendarClock, perm: "bnpl.view" },
  { href: "/admin/subscriptions", label: "Premium subscriptions", icon: Crown, perm: "subscriptions.manage" },
  { href: "/admin/promotions", label: "Promotions", icon: Megaphone, perm: "promotions.manage" },
  { href: "/admin/reviews", label: "Reviews", icon: Star, perm: "reviews.moderate" },
  { href: "/admin/reports", label: "Reports", icon: Flag, perm: "reports.manage" },
  { href: "/admin/settings", label: "Platform settings", icon: Settings, perm: "settings.manage" },
  { href: "/admin/audit", label: "Audit logs", icon: BookOpen, perm: "audit.view" },
];

function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data } = useApi<{ role: string; permissions: string[] }>("/admin/me");
  const perms = new Set(data?.permissions ?? []);
  const nav = NAV.filter((n) => perms.has(n.perm));
  return (
    <div className="grid min-h-[80vh] lg:grid-cols-[240px_1fr]">
      <aside className="border-b border-line bg-white lg:border-b-0 lg:border-r">
        <p className="hidden px-5 pt-5 text-xs font-bold uppercase tracking-wider text-muted lg:block">Admin console</p>
        <nav aria-label="Admin" className="scrollbar-none flex gap-1 overflow-x-auto p-2 lg:flex-col lg:p-3">
          {nav.map((n) => {
            const active = n.exact ? pathname === n.href : pathname.startsWith(n.href);
            return (
              <Link key={n.href} href={n.href} className={clsx("flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm", active ? "bg-brand-700 font-semibold text-white" : "hover:bg-canvas")}>
                <n.icon className="size-4" />{n.label}
              </Link>
            );
          })}
          {data && !nav.length && <p className="flex items-center gap-2 p-3 text-sm text-muted"><FileWarning className="size-4" />No admin permissions assigned.</p>}
        </nav>
      </aside>
      <div className="min-w-0 p-4 sm:p-6">{children}</div>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<PageLoader />}>
      <RequireAuth admin>{() => <Shell>{children}</Shell>}</RequireAuth>
    </Suspense>
  );
}
