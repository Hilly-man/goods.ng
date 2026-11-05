"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Store } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { useAuth } from "@/components/auth-provider";
import { Alert, Button, Input, Textarea } from "@/components/ui";
import { http, errorMessage, ApiError } from "@/lib/api";
import { StateCitySelect } from "@/components/state-city-select";
import { safeNext } from "../../login/form";
import type { User } from "@/lib/types";

function Form({ user }: { user: User }) {
  const { reload } = useAuth();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"));
  const [f, setF] = useState({ store_name: "", description: "", state: user.state ?? "", city: user.city ?? "", business_phone: user.phone ?? "" });
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { if (user.seller) router.replace(next === "/" ? "/seller" : next); }, [user.seller, router, next]);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });
  return (
    <form className="card space-y-4 p-6" onSubmit={async (e) => {
      e.preventDefault(); setBusy(true); setErr(null); setErrs({});
      try {
        await http.post("/sellers", { ...f, description: f.description || undefined, business_phone: f.business_phone || undefined });
        await reload();
        router.replace(next === "/" ? "/seller/products/new" : next);
      } catch (e) {
        if (e instanceof ApiError && e.status === 422) setErrs(e.fieldErrors); else setErr(errorMessage(e));
        setBusy(false);
      }
    }}>
      {err && <Alert tone="bad">{err}</Alert>}
      <Input label="Store / seller name" required value={f.store_name} onChange={set("store_name")} error={errs.store_name} hint="This is shown to buyers on your listings." />
      <Textarea label="About your store (optional)" rows={3} value={f.description} onChange={set("description")} />
      <div className="grid gap-3 sm:grid-cols-2">
        <StateCitySelect required state={f.state} city={f.city} errors={{ state: errs.state, city: errs.city }} onChange={(v) => setF({ ...f, ...v })} />
      </div>
      <Input label="Business phone" type="tel" value={f.business_phone} onChange={set("business_phone")} error={errs.business_phone} hint="Only shown to buyers if you're a Premium Seller and enable call contact." />
      <Button type="submit" block size="lg" loading={busy}>Create my store</Button>
    </form>
  );
}

export default function Page() {
  return (
    <RequireAuth>
      {(user) => (
        <div className="container-page max-w-xl py-8">
          <div className="mb-5 flex items-center gap-3"><span className="grid size-12 place-items-center rounded-xl bg-brand-50 text-brand-700"><Store className="size-6" /></span><div><h1 className="text-2xl font-bold">Start selling</h1><p className="text-sm text-muted">Free to list. Paid safely through Protected Checkout.</p></div></div>
          <Suspense><Form user={user} /></Suspense>
        </div>
      )}
    </RequireAuth>
  );
}
