import { NextResponse, type NextRequest } from "next/server";

/**
 * Admin console on its own subdomain (e.g. https://admin.goods.ng), configured by ADMIN_URL.
 *
 *   admin host  /            → rewrite to /admin
 *   admin host  /<section>   → rewrite to /admin/<section>       (users, disputes, refunds, …)
 *   admin host  /admin/...   → redirect to the clean URL without the /admin prefix
 *   admin host  anything else (login, /orders/<id>, /item/…, /store/…) → served as-is
 *   main host   /admin/...   → redirect to the admin subdomain
 *
 * Browsers keep cookies per host, so an admin's session on the subdomain is separate from the shop.
 * If ADMIN_URL is unset, nothing changes and the console stays at /admin.
 */

const ADMIN_URL = process.env.ADMIN_URL ? new URL(process.env.ADMIN_URL) : null;
const ADMIN_HOSTNAME = ADMIN_URL?.hostname.toLowerCase() ?? null;

// Every admin page is a single segment under /admin.
const SELLER_DETAIL = /^\/sellers\/[0-9a-fA-F-]{36}$/;
const PRODUCT_DETAIL = /^\/products\/[0-9a-fA-F-]{36}$/;

const SECTIONS = new Set([
  "users", "sellers", "verifications", "products", "categories", "orders", "payments", "escrow", "disputes",
  "refunds", "bnpl", "subscriptions", "promotions", "reviews", "reports", "settings", "audit", "staff", "roles",
  "live", "payouts", "wallets",
]);

function stripAdmin(pathname: string) {
  return pathname.replace(/^\/admin(?=\/|$)/, "") || "/";
}

export function proxy(request: NextRequest) {
  if (!ADMIN_URL || !ADMIN_HOSTNAME) return NextResponse.next();
  const host = (request.headers.get("host") ?? "").split(":")[0].toLowerCase();
  const { pathname, search } = request.nextUrl;
  const isAdminPath = pathname === "/admin" || pathname.startsWith("/admin/");

  if (host === ADMIN_HOSTNAME) {
    let res: NextResponse;
    if (isAdminPath) {
      // Build from ADMIN_URL: behind proxies request.nextUrl may carry the internal host, not the public one.
      res = NextResponse.redirect(new URL(`${stripAdmin(pathname)}${search}`, ADMIN_URL), 308);
    } else if (pathname === "/") {
      res = NextResponse.rewrite(new URL(`/admin${search}`, request.url));
    } else if ((/^\/[a-z-]+$/.test(pathname) && SECTIONS.has(pathname.slice(1))) || SELLER_DETAIL.test(pathname) || PRODUCT_DETAIL.test(pathname)) {
      res = NextResponse.rewrite(new URL(`/admin${pathname}${search}`, request.url));
    } else {
      res = NextResponse.next();
    }
    res.headers.set("X-Robots-Tag", "noindex, nofollow");
    return res;
  }

  if (isAdminPath) {
    return NextResponse.redirect(new URL(`${stripAdmin(pathname)}${search}`, ADMIN_URL), 308);
  }
  return NextResponse.next();
}

export const config = {
  // Skip API proxying, Next internals, uploaded media and well-known static files.
  matcher: ["/((?!api/|_next/|media/|favicon.ico|robots.txt|sitemap.xml).*)"],
};
