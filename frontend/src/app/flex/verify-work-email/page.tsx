"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, ButtonLink, Spinner } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";

function Verify() {
  const token = useSearchParams().get("token") ?? "";
  const [state, setState] = useState<{ ok: boolean; msg: string } | null>(null);
  const sent = useRef(false);
  useEffect(() => {
    if (sent.current) return;
    sent.current = true;
    http.post("/bnpl/profile/employment/verify-email", { token })
      .then(() => setState({ ok: true, msg: "Your workplace is verified. Your Goods Flex cap has been raised." }))
      .catch((e) => setState({ ok: false, msg: errorMessage(e) }));
  }, [token]);
  if (!state) return <div className="flex justify-center py-10"><Spinner className="size-8" /></div>;
  return (
    <div className="space-y-3">
      <Alert tone={state.ok ? "good" : "bad"} title={state.ok ? "Work email confirmed" : "Couldn't confirm"}>{state.msg}</Alert>
      <ButtonLink href="/flex">Back to Goods Flex</ButtonLink>
    </div>
  );
}

export default function Page() {
  return <RequireAuth>{() => <div className="container-page max-w-lg py-10"><Suspense><Verify /></Suspense></div>}</RequireAuth>;
}
