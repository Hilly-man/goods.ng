"use client";

import { RequireAuth } from "@/components/require-auth";
import { NegotiationList } from "@/components/negotiation-view";

export default function Page() {
  return <RequireAuth>{() => <div className="container-page max-w-3xl py-6"><h1 className="mb-4 text-2xl font-bold">My offers</h1><NegotiationList role="buyer" /></div>}</RequireAuth>;
}
