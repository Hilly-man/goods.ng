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
    else if (admin && user.role === "user") router.replace("/");
  }, [loading, user, seller, admin, router, pathname]);
  if (loading || blocked || !user) return <PageLoader />;
  return <>{children(user)}</>;
}
