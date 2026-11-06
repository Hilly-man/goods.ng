"use client";

import { PageLoader as RouteLoader } from "@/components/ui";
import { Suspense as RouteSuspense } from "react";
import { use } from "react";
import { useSearchParams } from "next/navigation";
import { RequireAuth } from "@/components/require-auth";
import { OrderView } from "@/components/order-view";

function Inner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const justPaid = useSearchParams().get("paid") === "1"; // arrived straight from a confirmed payment
  return <RequireAuth>{() => <div className="container-page max-w-5xl py-6"><h1 className="mb-4 text-2xl font-bold">Order details</h1><OrderView id={id} justPaid={justPaid} /></div>}</RequireAuth>;
}

export default function Page(props: { params: Promise<{ id: string }> }) {
  return (
    <RouteSuspense fallback={<RouteLoader />}>
      <Inner {...props} />
    </RouteSuspense>
  );
}
