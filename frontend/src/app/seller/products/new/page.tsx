"use client";

import { RequireAuth } from "@/components/require-auth";
import { ProductForm } from "@/components/product-form";

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Post a new listing</h1><ProductForm /></>}</RequireAuth>;
}
