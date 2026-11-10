"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { Suspense } from "react";
import { PageLoader } from "@/components/ui";
import { BadgeCheck, BarChart3, Crown, Handshake, LayoutDashboard, MessageCircle, Package, PlusCircle, Settings, ShoppingBag, Store, Wallet } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { PremiumBadge } from "@/components/badges";

const NAV = [
  { href: "/seller", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/seller/products", label: "My products", icon: Package, exact: true },
  { href: "/seller/products/new", label: "Add product", icon: PlusCircle },
  { href: "/seller/orders", label: "Orders", icon: ShoppingBag },
  { href: "/messages", label: "Messages", icon: MessageCircle },
  { href: "/seller/offers", label: "Offers", icon: Handshake },
  { href: "/seller/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/seller/earnings", label: "Wallet", icon: Wallet },
  { href: "/seller/storefront", label: "Storefront", icon: Store },
  { href: "/seller/verification", label: "Verification", icon: BadgeCheck },
  { href: "/seller/subscription", label: "Subscription", icon: Crown },
  { href: "/account", label: "Account settings", icon: Settings },
];

function SellerShell({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const pathname = usePathname();
  if (!user?.seller || pathname.startsWith("/seller/onboarding")) return <>{children}</>;
  const active = (n: (typeof NAV)[number]) => (n.exact ? pathname === n.href : pathname.startsWith(n.href));
  return (
    <div className="container-page grid grid-cols-[minmax(0,1fr)] gap-5 py-5 lg:grid-cols-[230px_minmax(0,1fr)]">
      <aside className="min-w-0 lg:sticky lg:top-20 lg:self-start">
        <div className="card mb-3 hidden p-4 lg:block">
          <p className="truncate font-semibold">{user.seller.store_name}</p>
          <div className="mt-1 flex items-center gap-2 text-xs">
            {user.seller.is_premium && <PremiumBadge />}
            <Link href={`/store/${user.seller.slug}`} className="text-brand-700 hover:underline">View store</Link>
          </div>
        </div>
        <nav aria-label="Seller dashboard" className="scrollbar-none -mx-3 flex gap-1 overflow-x-auto px-3 lg:card lg:mx-0 lg:flex-col lg:p-2">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} aria-current={active(n) ? "page" : undefined}
              className={clsx("flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium", active(n) ? "bg-brand-700 text-white" : "bg-white text-ink hover:bg-canvas lg:bg-transparent")}>
              <n.icon className="size-4" />{n.label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export default function SellerLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<PageLoader />}>
      <SellerShell>{children}</SellerShell>
    </Suspense>
  );
}
