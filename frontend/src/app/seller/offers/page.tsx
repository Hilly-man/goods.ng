"use client";

import { RequireAuth } from "@/components/require-auth";
import { NegotiationList } from "@/components/negotiation-view";

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Offers & negotiations</h1><NegotiationList role="seller" /></>}</RequireAuth>;
}
