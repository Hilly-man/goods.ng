"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Crown } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, Button, Checkbox, Input, PageLoader, Textarea, useToast } from "@/components/ui";
import { http, errorMessage, ApiError } from "@/lib/api";
import { StateCitySelect } from "@/components/state-city-select";

type S = { store_name: string; description: string | null; state: string | null; city: string | null; address: string | null; business_phone: string | null; whatsapp_number: string | null; whatsapp_enabled: boolean; phone_enabled: boolean; business_hours: string | null; website: string | null; logo_url: string | null; banner_url: string | null; is_premium: boolean; slug: string };

function Form() {
  const [s, setS] = useState<S | null>(null);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  useEffect(() => { http.get<S>("/sellers/me").then(setS); }, []);
  if (!s) return <PageLoader />;
  const set = (k: keyof S) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setS({ ...s, [k]: e.target.value });
  async function upload(kind: "logo" | "banner", file: File) {
    const fd = new FormData(); fd.append("file", file);
    try { setS(await http.post<S>(`/sellers/me/${kind}`, fd)); toast("Image updated"); } catch (e) { toast(errorMessage(e), "bad"); }
  }
  async function save(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setErrs({});
    const body: Record<string, unknown> = { store_name: s!.store_name, description: s!.description || null, state: s!.state, city: s!.city, address: s!.address || null, business_phone: s!.business_phone || null };
    if (s!.is_premium) Object.assign(body, { whatsapp_number: s!.whatsapp_number || null, whatsapp_enabled: s!.whatsapp_enabled, phone_enabled: s!.phone_enabled, business_hours: s!.business_hours || null, website: s!.website || null });
    try { setS(await http.patch<S>("/sellers/me", body)); toast("Storefront saved"); }
    catch (e) { if (e instanceof ApiError && e.status === 422) setErrs(e.fieldErrors); else toast(errorMessage(e), "bad"); }
    finally { setBusy(false); }
  }
  return (
    <form onSubmit={save} className="space-y-4">
      <section className="card grid gap-4 p-5 sm:grid-cols-2">
        <div className="sm:col-span-2 flex items-center gap-4">
          <span className="size-16 overflow-hidden rounded-xl bg-canvas">{/* eslint-disable-next-line @next/next/no-img-element */}{s.logo_url && <img src={s.logo_url} alt="" className="size-full object-cover" />}</span>
          <label className="chip cursor-pointer">Upload logo<input type="file" accept="image/*" className="sr-only" onChange={(e) => e.target.files?.[0] && upload("logo", e.target.files[0])} /></label>
          <Link href={`/store/${s.slug}`} className="ml-auto text-sm font-semibold text-brand-700">View store →</Link>
        </div>
        <Input label="Store name" value={s.store_name} onChange={set("store_name")} error={errs.store_name} />
        <Input label="Business phone" value={s.business_phone ?? ""} onChange={set("business_phone")} error={errs.business_phone} />
        <div className="sm:col-span-2"><Textarea label="About your store" rows={3} value={s.description ?? ""} onChange={set("description")} /></div>
        <StateCitySelect state={s.state ?? ""} city={s.city ?? ""} errors={{ state: errs.state, city: errs.city }} onChange={(v) => setS({ ...s, ...v })} />
        <div className="sm:col-span-2"><Input label="Address (not shown publicly)" value={s.address ?? ""} onChange={set("address")} /></div>
      </section>
      <section className="card space-y-4 p-5">
        <h2 className="flex items-center gap-2 font-semibold"><Crown className="size-5 text-premium-500" />Premium features</h2>
        {!s.is_premium && <Alert tone="info">WhatsApp & call buttons, banner, business hours and website link require Premium. <Link href="/premium" className="font-semibold underline">Upgrade</Link></Alert>}
        <fieldset disabled={!s.is_premium} className="grid gap-4 disabled:opacity-60 sm:grid-cols-2">
          <Input label="WhatsApp number" value={s.whatsapp_number ?? ""} onChange={set("whatsapp_number")} error={errs.whatsapp_number} />
          <Input label="Business hours" placeholder="Mon–Sat, 9am–6pm" value={s.business_hours ?? ""} onChange={set("business_hours")} />
          <Input label="Website" placeholder="https://" value={s.website ?? ""} onChange={set("website")} error={errs.website} />
          <div className="flex items-center gap-3"><label className="chip cursor-pointer">Upload banner<input type="file" accept="image/*" className="sr-only" onChange={(e) => e.target.files?.[0] && upload("banner", e.target.files[0])} /></label></div>
          <Checkbox checked={s.whatsapp_enabled} onChange={(e) => setS({ ...s, whatsapp_enabled: e.target.checked })} label="Show WhatsApp button to buyers" />
          <Checkbox checked={s.phone_enabled} onChange={(e) => setS({ ...s, phone_enabled: e.target.checked })} label="Show call button to buyers" />
        </fieldset>
      </section>
      <div className="flex justify-end"><Button type="submit" loading={busy}>Save storefront</Button></div>
    </form>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Storefront settings</h1><Form /></>}</RequireAuth>;
}
