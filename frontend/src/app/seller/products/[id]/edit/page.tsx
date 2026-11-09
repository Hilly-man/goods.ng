"use client";

import { Suspense as RouteSuspense, useState } from "react";
import { use } from "react";
import { Megaphone } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { ProductForm } from "@/components/product-form";
import { Button, PageLoader } from "@/components/ui";
import { PromoteDialog } from "@/components/promote-dialog";
import { date } from "@/lib/format";
import { useApi } from "@/lib/hooks";
import type { SellerProductDetail } from "@/lib/types";

function PromoteCard({ p }: { p: SellerProductDetail }) {
  const [open, setOpen] = useState(false);
  return (
    <section className="card mt-4 p-4 sm:p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="flex items-center gap-2 font-semibold"><Megaphone className="size-4 text-brand-700" />Promote this listing</h2>
          <p className="mt-1 text-sm text-muted">Buy extra visibility for this one listing from ₦3,099 — no monthly plan needed.</p>
          {p.promoted_tier && p.is_featured_until && (
            <p className="mt-1 text-xs font-semibold text-brand-700">
              {p.promoted_tier === "premium" ? "Premium" : "TOP"} until {date(p.is_featured_until)}
            </p>
          )}
        </div>
        <Button variant="accent" onClick={() => setOpen(true)}>See options</Button>
      </div>
      {open && <PromoteDialog product={p} onClose={() => setOpen(false)} />}
    </section>
  );
}

function Edit({ id }: { id: string }) {
  const { data } = useApi<SellerProductDetail>(`/seller/products/${id}`);
  return data ? <><ProductForm existing={data} /><PromoteCard p={data} /></> : <PageLoader />;
}

function Inner({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Edit listing</h1><Edit id={id} /></>}</RequireAuth>;
}

export default function Page(props: { params: Promise<{ id: string }> }) {
  return (
    <RouteSuspense fallback={<PageLoader />}>
      <Inner {...props} />
    </RouteSuspense>
  );
}
