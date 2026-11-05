"use client";

import { useCallback, useEffect, useEffectEvent, useState } from "react";
import { api, errorMessage } from "./api";

type State<T> = { loadedKey: string | null; data: T | undefined; error: string | null };

/**
 * Minimal data hook: fetch on mount / key change, expose reload + local setter.
 * Previous data stays visible while a reload is in flight (no flicker on slow networks).
 */
export function useApi<T>(path: string | null, query?: Record<string, unknown>) {
  const qs = JSON.stringify(query ?? {});
  const [nonce, setNonce] = useState(0);
  const key = path ? `${path}?${qs}#${nonce}` : null;
  const [state, setState] = useState<State<T>>({ loadedKey: null, data: undefined, error: null });

  useEffect(() => {
    if (!path || !key) return;
    let alive = true;
    api<T>(path, { query: JSON.parse(qs) })
      .then((data) => alive && setState({ loadedKey: key, data, error: null }))
      .catch((e) => alive && setState((s) => ({ loadedKey: key, data: s.data, error: errorMessage(e) })));
    return () => {
      alive = false;
    };
  }, [path, qs, key]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  const setData = useCallback((data: T) => setState((s) => ({ ...s, data })), []);
  return { data: state.data, error: state.error, loading: !!key && state.loadedKey !== key, reload, setData };
}

/** Poll a function while the document is visible (near-real-time messaging, counters). */
export function usePolling(fn: () => void, ms: number, enabled = true) {
  const onTick = useEffectEvent(() => {
    if (document.visibilityState === "visible") fn();
  });
  useEffect(() => {
    if (!enabled) return;
    const id = setInterval(onTick, ms);
    document.addEventListener("visibilitychange", onTick);
    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onTick);
    };
  }, [ms, enabled]);
}
