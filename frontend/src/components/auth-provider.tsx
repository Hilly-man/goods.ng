"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { http, refreshSession, setAccessToken, CSRF } from "@/lib/api";
import type { User } from "@/lib/types";

export type LoginResult = { user: User } | { mfaRequired: true; ticket: string };

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, captchaToken?: string | null) => Promise<LoginResult>;
  verifyMfa: (ticket: string, code: string) => Promise<User>;
  register: (data: { full_name: string; email: string; phone?: string; password: string }) => Promise<User>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
  setUser: (u: User | null) => void;
}

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    refreshSession()
      .then((b) => alive && setUser((b?.user as User) ?? null))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string, captchaToken?: string | null): Promise<LoginResult> => {
    const r = await http.post<{ access_token?: string; user?: User; mfa_required?: boolean; mfa_ticket?: string }>(
      "/auth/login", { email, password, captcha_token: captchaToken || undefined });
    if (r.mfa_required && r.mfa_ticket) return { mfaRequired: true, ticket: r.mfa_ticket };
    setAccessToken(r.access_token!);
    setUser(r.user!);
    return { user: r.user! };
  }, []);

  const verifyMfa = useCallback(async (ticket: string, code: string) => {
    const r = await http.post<{ access_token: string; user: User }>("/auth/mfa/verify", { mfa_ticket: ticket, code });
    setAccessToken(r.access_token);
    setUser(r.user);
    return r.user;
  }, []);

  const register = useCallback(async (data: { full_name: string; email: string; phone?: string; password: string }) => {
    const r = await http.post<{ access_token: string; user: User }>("/auth/register", data);
    setAccessToken(r.access_token);
    setUser(r.user);
    return r.user;
  }, []);

  const logout = useCallback(async () => {
    await fetch("/api/v1/auth/logout", { method: "POST", headers: CSRF, credentials: "same-origin" }).catch(() => {});
    setAccessToken(null);
    setUser(null);
  }, []);

  const reload = useCallback(async () => {
    setUser(await http.get<User>("/auth/me"));
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, verifyMfa, register, logout, reload, setUser }),
    [user, loading, login, verifyMfa, register, logout, reload],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

const noopSubscribe = () => () => {};

/**
 * false on the server and during this component's hydration pass, true afterwards.
 * Streamed boundaries can hydrate after the session refresh has finished; without this, they would
 * hydrate with "signed in/out" UI that differs from the server HTML (React hydration error #418).
 */
function useHydrated() {
  return useSyncExternalStore(noopSubscribe, () => true, () => false);
}

export function useAuth() {
  const v = useContext(Ctx);
  const hydrated = useHydrated();
  if (!v) throw new Error("useAuth must be used inside AuthProvider");
  return hydrated ? v : { ...v, user: null, loading: true };
}
