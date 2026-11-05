"use client";

import { PageLoader as RouteLoader } from "@/components/ui";
import { Suspense as RouteSuspense } from "react";
import { use } from "react";
import { RequireAuth } from "@/components/require-auth";
import { NegotiationView } from "@/components/negotiation-view";

function Inner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RequireAuth>{() => <div className="container-page max-w-5xl py-6"><h1 className="mb-4 text-2xl font-bold">Negotiation</h1><NegotiationView id={id} /></div>}</RequireAuth>;
}

export default function Page(props: { params: Promise<{ id: string }> }) {
  return (
    <RouteSuspense fallback={<RouteLoader />}>
      <Inner {...props} />
    </RouteSuspense>
  );
}
