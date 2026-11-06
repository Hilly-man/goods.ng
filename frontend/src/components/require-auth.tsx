"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "./auth-provider";
import { PageLoader } from "./ui";
import type { User } from "@/lib/types";

/**
 * Client-side route guard for UX only. Every API call is independently authorised server-side,
 * so bypassing this guard exposes nothing.
 */
export function RequireAuth({
  children,
  seller,
  admin,
}: {
  children: (user: User) => React.ReactNode;
  seller?: boolean;
  admin?: boolean;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const blocked = !loading && (!user || (seller && !user.seller) || (admin && user.role === "user"));
  useEffect(() => {
    if (loading) return;
    if (!user) router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    else if (seller && !user.seller) router.replace(`/seller/onboarding?next=${encodeURIComponent(pathname)}`);
    // Non-admins in the admin area see an access-denied card (redirecting to "/" would loop on the admin host).
  }, [loading, user, seller, admin, router, pathname]);
  if (!loading && user && admin && user.role === "user") {
    const site = process.env.NEXT_PUBLIC_SITE_URL || "/";
    return (
      <div className="container-page grid min-h-[50vh] place-items-center py-12 text-center">
        <div className="card max-w-md p-8">
          <h1 className="text-xl font-bold">Admin access only</h1>
          <p className="mt-2 text-sm text-muted">You&apos;re signed in as {user.email}, which isn&apos;t an administrator account.</p>
          <a href={site} className="mt-5 inline-block rounded-lg bg-brand-700 px-5 py-2.5 font-semibold text-white">Go to Goods.ng</a>
        </div>
      </div>
    );
  }
  if (loading || blocked || !user) return <PageLoader />;
  return <>{children(user)}</>;
}
