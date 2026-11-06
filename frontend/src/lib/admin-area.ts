"use client";

import { useSyncExternalStore } from "react";

const noop = () => () => {};
const ADMIN_HOSTNAME = (() => {
  try {
    return process.env.NEXT_PUBLIC_ADMIN_URL ? new URL(process.env.NEXT_PUBLIC_ADMIN_URL).hostname : null;
  } catch {
    return null;
  }
})();

export function isAdminHost() {
  return !!ADMIN_HOSTNAME && typeof window !== "undefined" && window.location.hostname === ADMIN_HOSTNAME;
}

/**
 * True when the browser is on the admin subdomain or under /admin. Always false on the server and during
 * hydration (pages behind the subdomain rewrite are rendered for /admin/*, while the browser URL differs),
 * so it never causes a hydration mismatch — the UI adjusts right after mount.
 */
export function useIsAdminArea() {
  return useSyncExternalStore(
    noop,
    () => isAdminHost() || window.location.pathname.startsWith("/admin"),
    () => false,
  );
}

/** Link prefix for admin pages: "" on the admin subdomain (clean URLs), "/admin" elsewhere. */
export function useAdminBase() {
  return useSyncExternalStore(noop, () => (isAdminHost() ? "" : "/admin"), () => "/admin");
}
