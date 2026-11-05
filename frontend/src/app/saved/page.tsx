"use client";

import { Heart } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { ButtonLink, EmptyState } from "@/components/ui";
import { ProductGrid, ProductGridSkeleton } from "@/components/product-card";
import { useApi } from "@/lib/hooks";
import type { Page, ProductCard } from "@/lib/types";

function Saved() {
  const { data } = useApi<Page<ProductCard>>("/users/me/favourites", { page_size: 60 });
  if (!data) return <ProductGridSkeleton />;
  if (!data.items.length) return <div className="card"><EmptyState icon={<Heart />} title="No saved items yet" body="Tap the heart on any listing to save it here." action={<ButtonLink href="/">Browse listings</ButtonLink>} /></div>;
  return <ProductGrid items={data.items} />;
}

export default function Page() {
  return <RequireAuth>{() => <div className="container-page py-6"><h1 className="mb-4 text-2xl font-bold">Saved items</h1><Saved /></div>}</RequireAuth>;
}
