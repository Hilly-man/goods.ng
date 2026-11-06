"use client";

import Link from "next/link";
import { Crown, Eye, Handshake, Image as ImageIcon, MessageCircle, MousePointerClick, Package, PlusCircle, ShieldCheck, ShoppingBag, Wallet } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, ButtonLink, PageLoader, Stat } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import { naira, VERIFICATION_LABEL } from "@/lib/format";
import type { VerificationLevel } from "@/lib/types";

type Dash = { total_listings: number; active_listings: number; product_views: number; enquiries: number; contact_clicks: number; pending_orders: number; orders_in_transit: number; completed_orders: number; protected_sales: number; revenue_completed: string; open_negotiations: number; images_used: number; images_limit: number; is_premium: boolean; verification_level: VerificationLevel };

function Overview() {
  const { data: d } = useApi<Dash>("/sellers/me/dashboard");
  if (!d) return <PageLoader />;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">Seller overview</h1>
        <ButtonLink href="/seller/products/new"><PlusCircle className="size-4" />Add product</ButtonLink>
      </div>
      {d.pending_orders > 0 && <Alert tone="warn" title={`${d.pending_orders} order${d.pending_orders > 1 ? "s" : ""} need your action`}><Link href="/seller/orders" className="underline">Accept and dispatch now</Link> — buyers are waiting and funds are safeguarded.</Alert>}
      {d.open_negotiations > 0 && <Alert tone="info" title={`${d.open_negotiations} open offer${d.open_negotiations > 1 ? "s" : ""}`}><Link href="/seller/offers" className="underline">Respond to offers</Link></Alert>}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Active listings" value={d.active_listings} hint={`${d.total_listings} total`} icon={<Package className="size-4" />} />
        <Stat label="Product views" value={d.product_views.toLocaleString()} icon={<Eye className="size-4" />} />
        <Stat label="Enquiries" value={d.enquiries} icon={<MessageCircle className="size-4" />} />
        <Stat label="Contact clicks" value={d.contact_clicks} icon={<MousePointerClick className="size-4" />} />
        <Stat label="Pending orders" value={d.pending_orders} icon={<ShoppingBag className="size-4" />} />
        <Stat label="In transit" value={d.orders_in_transit} />
        <Stat label="Completed orders" value={d.completed_orders} hint={`${d.protected_sales} protected sales`} icon={<ShieldCheck className="size-4" />} />
        <Stat label="Revenue (completed)" value={naira(d.revenue_completed)} icon={<Wallet className="size-4" />} />
        <Stat label="Photo slots" value={`${d.images_used}/${d.images_limit}`} hint="Delete photos to free space" icon={<ImageIcon className="size-4" />} />
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {!d.is_premium && (
          <Link href="/premium" className="card flex items-center gap-3 bg-gradient-to-r from-amber-50 to-yellow-50 p-4 ring-amber-200">
            <Crown className="size-8 text-premium-500" />
            <span><span className="block font-semibold">Go Premium</span><span className="text-sm text-muted">WhatsApp & call buttons, featured listings, advanced analytics.</span></span>
          </Link>
        )}
        <Link href="/seller/verification" className="card flex items-center gap-3 p-4">
          <ShieldCheck className="size-8 text-sky-600" />
          <span><span className="block font-semibold">Verification: {VERIFICATION_LABEL[d.verification_level]}</span><span className="text-sm text-muted">Verified sellers earn more buyer trust.</span></span>
        </Link>
        <Link href="/seller/offers" className="card flex items-center gap-3 p-4"><Handshake className="size-8 text-brand-700" /><span className="font-semibold">Manage offers & negotiations</span></Link>
      </div>
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <Overview />}</RequireAuth>;
}
