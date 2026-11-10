"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { getAccessToken } from "@/lib/api";
import { anonId } from "@/lib/interest";

const LAST_PING = "gng_ping";

function optedOut() {
  if (typeof navigator === "undefined") return true;
  const gpc = (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl;
  return navigator.doNotTrack === "1" || gpc === true;
}

function visitorId(): string | null {
  try {
    const id = anonId();
    if (id) return id;
  } catch {
    /* storage blocked */
  }
  try {
    let id = sessionStorage.getItem("gng_vid");
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem("gng_vid", id);
    }
    return id;
  } catch {
    return null;
  }
}

async function ping(path: string, heartbeat = false) {
  if (optedOut()) return;
  const id = visitorId();
  if (!id) return;
  if (!heartbeat) {
    try {
      const last = sessionStorage.getItem(LAST_PING);
      if (last) {
        const prev = JSON.parse(last) as { path: string; at: number };
        if (prev.path === path && Date.now() - prev.at < 10 * 60_000) return;
      }
      sessionStorage.setItem(LAST_PING, JSON.stringify({ path, at: Date.now() }));
    } catch {
      /* storage blocked — still record the page view */
    }
  }
  const token = getAccessToken();
  await fetch("/api/v1/stats/visit", {
    method: "POST",
    keepalive: true,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-Anon-Id": id,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ path }),
  }).catch(() => undefined);
}

/** First-party page-view + heartbeat pings for the admin live-traffic counters. */
export function VisitorPing() {
  const pathname = usePathname();

  useEffect(() => {
    if (!pathname || pathname.startsWith("/admin")) return;
    void ping(pathname);
    const id = setInterval(() => {
      if (document.visibilityState === "visible") void ping(pathname, true);
    }, 60_000);
    return () => clearInterval(id);
  }, [pathname]);

  return null;
}
