"use client";

import { Suspense as RouteSuspense } from "react";
import { use } from "react";
import { RequireAuth } from "@/components/require-auth";
import { ProductForm } from "@/components/product-form";
import { PageLoader } from "@/components/ui";
import { useApi } from "@/lib/hooks";
import type { SellerProductDetail } from "@/lib/types";

function Edit({ id }: { id: string }) {
  const { data } = useApi<SellerProductDetail>(`/seller/products/${id}`);
  return data ? <ProductForm existing={data} /> : <PageLoader />;
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
