"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";

export function SubscribeButton({ plan }: { plan: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  async function go() {
    if (!user) return router.push("/login?next=/premium");
    if (!user.seller) return router.push("/seller/onboarding?next=/premium");
    setBusy(true);
    try {
      const r = await http.post<{ authorization_url: string }>("/subscriptions", { plan_code: plan });
      window.location.href = r.authorization_url;
    } catch (e) {
      toast(errorMessage(e), "bad");
      setBusy(false);
    }
  }
  return <Button block variant={user?.seller?.is_premium ? "outline" : "primary"} loading={busy} onClick={go}>{user?.seller?.is_premium ? "Renew / extend" : "Choose plan"}</Button>;
}
