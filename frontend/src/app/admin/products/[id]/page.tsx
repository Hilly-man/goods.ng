"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useRef, useState } from "react";
import { ExternalLink, ImagePlus, Package, Trash2 } from "lucide-react";
import { AdminPageHeader, StatusBadge, askReason } from "@/components/admin-ui";
import { StateCitySelect } from "@/components/state-city-select";
import { Alert, Button, Checkbox, Input, PageLoader, Select, Textarea, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useAdminBase } from "@/lib/admin-area";
import { CONDITION_LABEL, date, naira, toMoneyString } from "@/lib/format";
import { useApi } from "@/lib/hooks";

type Img = { id: string; url: string; thumb_url: string; width: number | null; height: number | null };
type P = {
  id: string; title: string; slug: string; description: string; brand: string | null; model: string | null;
  condition: string; price: string; quantity: number; negotiable: boolean; state: string; city: string;
  category: { id: string; name: string; slug: string };
  subcategory: { id: string; name: string; slug: string } | null;
  seller: { id: string; store_name: string; slug: string };
  images: Img[]; status: string; rejection_reason: string | null; is_featured: boolean;
  views_count: number; enquiries_count: number; favourites_count: number;
  created_at: string; updated_at: string;
};

export default function Page() {
  const { id } = useParams<{ id: string }>();
  const { data, setData, error } = useApi<P>(`/admin/products/${id}`);
  const toast = useToast();
  const base = useAdminBase();
  const fileInput = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [f, setF] = useState<Record<string, string | boolean> | null>(null);

  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!data) return <PageLoader />;
  const p = data;
  const form = f ?? {
    title: p.title, description: p.description, brand: p.brand ?? "", model: p.model ?? "",
    condition: p.condition, price: Number(p.price).toLocaleString(), quantity: String(p.quantity),
    negotiable: p.negotiable, state: p.state, city: p.city,
  };
  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setF({ ...form, [k]: e.target.value });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    const price = toMoneyString(String(form.price));
    if (!price) return setErr("Enter a valid price");
    setBusy(true);
    try {
      const body = {
        title: form.title, description: form.description, brand: form.brand || null, model: form.model || null,
        condition: form.condition, price, quantity: Number(form.quantity || 0), negotiable: form.negotiable,
        state: form.state, city: form.city,
      };
      setData(await http.patch<P>(`/admin/products/${p.id}`, body));
      toast("Listing updated");
    } catch (e) {
      setErr(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function moderate(action: string) {
    const body: Record<string, unknown> = { action };
    if (action === "reject" || action === "deactivate") {
      const reason = await askReason(action === "reject" ? "Reject this listing?" : "Take down this listing?", 3,
        { message: "The seller sees this reason.", confirmLabel: action === "reject" ? "Reject" : "Take down", tone: "danger" });
      if (!reason) return;
      body.reason = reason;
    }
    setBusy(true);
    try {
      await http.post(`/admin/products/${p.id}/moderate`, body);
      setData(await http.get<P>(`/admin/products/${p.id}`));
      toast("Listing updated");
    } catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
  }

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    try {
      const fd = new FormData();
      Array.from(files).forEach((x) => fd.append("files", x));
      setData(await http.post<P>(`/admin/products/${p.id}/images`, fd));
      toast("Photos added");
    } catch (e) { toast(errorMessage(e), "bad"); }
    finally { setBusy(false); if (fileInput.current) fileInput.current.value = ""; }
  }

  async function removeImage(imageId: string) {
    if (!confirm("Remove this photo?")) return;
    setBusy(true);
    try { setData(await http.del<P>(`/admin/products/${p.id}/images/${imageId}`)); toast("Photo removed"); }
    catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
  }

  return (
    <>
      <AdminPageHeader icon={Package} title={p.title} description={<>
        <Link href={`${base}/sellers/${p.seller.id}`} className="font-semibold text-brand-700 hover:underline">{p.seller.store_name}</Link>
        {" · "}{p.category.name}{p.subcategory ? ` / ${p.subcategory.name}` : ""} · {p.views_count} views · {p.enquiries_count} enquiries · listed {date(p.created_at)}
      </>} actions={<>
        <Link href={`/item/${p.slug}`} className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-2 text-sm font-semibold hover:bg-canvas"><ExternalLink className="size-4" />View listing</Link>
        {p.status !== "active" && <Button size="sm" loading={busy} onClick={() => moderate("approve")}>Approve</Button>}
        {p.status === "pending_review" && <Button size="sm" variant="danger" loading={busy} onClick={() => moderate("reject")}>Reject</Button>}
        {p.status === "active" && <Button size="sm" variant="outline" loading={busy} onClick={() => moderate(p.is_featured ? "unfeature" : "feature")}>{p.is_featured ? "Unfeature" : "Feature"}</Button>}
        {p.status === "active" && <Button size="sm" variant="danger" loading={busy} onClick={() => moderate("deactivate")}>Take down</Button>}
      </>} />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <StatusBadge status={p.status} />
        {p.is_featured && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">Featured</span>}
        {p.rejection_reason && <span className="text-sm text-red-600">Moderation note: {p.rejection_reason}</span>}
      </div>

      <form onSubmit={save} className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          <section className="card space-y-3 p-4">
            <h2 className="font-semibold">Listing details</h2>
            <Input label="Title" required minLength={5} maxLength={140} value={String(form.title)} onChange={set("title")} />
            <Textarea label="Description" required rows={8} maxLength={8000} value={String(form.description)} onChange={set("description")} hint="At least 20 characters." />
            <div className="grid gap-3 sm:grid-cols-2">
              <Input label="Price (₦)" inputMode="numeric" required value={String(form.price)} onChange={set("price")} />
              <Input label="Quantity" type="number" min={0} value={String(form.quantity)} onChange={set("quantity")} />
              <Input label="Brand" value={String(form.brand)} onChange={set("brand")} />
              <Input label="Model" value={String(form.model)} onChange={set("model")} />
              <Select label="Condition" value={String(form.condition)} onChange={set("condition")}>
                {Object.entries(CONDITION_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </Select>
              <div className="flex items-end pb-2"><Checkbox checked={Boolean(form.negotiable)} onChange={(e) => setF({ ...form, negotiable: e.target.checked })} label="Price is negotiable" /></div>
            </div>
            <StateCitySelect required state={String(form.state)} city={String(form.city)}
              onChange={(v) => setF({ ...form, ...v })} />
          </section>

          <section className="card space-y-3 p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">Photos</h2>
              <Button type="button" size="sm" variant="secondary" loading={busy} onClick={() => fileInput.current?.click()}><ImagePlus className="size-4" />Add photos</Button>
              <input ref={fileInput} type="file" multiple accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => upload(e.target.files)} />
            </div>
            {p.images.length ? (
              <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
                {p.images.map((im) => (
                  <div key={im.id} className="relative overflow-hidden rounded-lg border border-line">
                    <img src={im.thumb_url} alt="" className="aspect-square w-full object-cover" />
                    <button type="button" aria-label="Remove photo" onClick={() => removeImage(im.id)} className="absolute right-1 top-1 rounded-full bg-white/90 p-1 text-red-600"><Trash2 className="size-3.5" /></button>
                  </div>
                ))}
              </div>
            ) : <p className="text-sm text-muted">No photos.</p>}
          </section>
        </div>

        <aside className="space-y-3">
          <section className="card space-y-2 p-4 text-sm">
            <h2 className="font-semibold">Summary</h2>
            <div className="flex justify-between"><span className="text-muted">Current price</span><b>{naira(p.price)}</b></div>
            <div className="flex justify-between"><span className="text-muted">Favourites</span><span>{p.favourites_count}</span></div>
            <div className="flex justify-between"><span className="text-muted">Updated</span><span>{date(p.updated_at, true)}</span></div>
            <Link href={`${base}/sellers/${p.seller.id}`} className="mt-2 block text-sm font-semibold text-brand-700 hover:underline">Open seller dashboard</Link>
          </section>
          {err && <Alert tone="bad">{err}</Alert>}
          <Button type="submit" block size="lg" loading={busy}>Save changes</Button>
        </aside>
      </form>
    </>
  );
}
