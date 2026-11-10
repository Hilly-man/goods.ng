"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ImagePlus, Plus, Sparkles, Trash2, X } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { http, errorMessage, ApiError } from "@/lib/api";
import { CONDITION_LABEL, toMoneyString } from "@/lib/format";
import { StateCitySelect } from "./state-city-select";
import type { Category, DeliveryOption, SellerProductDetail } from "@/lib/types";
import { Alert, Button, Checkbox, Input, Select, Textarea, useToast } from "./ui";

const MAX_PREMIUM_IMAGES = 10;
const MAX_FREE_IMAGES = 5;

export function ProductForm({ existing }: { existing?: SellerProductDetail }) {
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();
  const maxImages = user?.seller?.is_premium ? MAX_PREMIUM_IMAGES : MAX_FREE_IMAGES;
  const [cats, setCats] = useState<Category[]>([]);
  const [root, setRoot] = useState(existing?.category.id ?? "");
  const [f, setF] = useState({
    title: existing?.title ?? "", description: existing?.description ?? "", category_id: existing?.subcategory?.id ?? existing?.category.id ?? "",
    brand: existing?.brand ?? "", model: existing?.model ?? "", condition: existing?.condition ?? "brand_new",
    price: existing ? Number(existing.price).toLocaleString() : "", negotiable: existing?.negotiable ?? true, quantity: String(existing?.quantity ?? 1),
    state: existing?.state ?? "", city: existing?.city ?? "", protected_checkout_enabled: existing?.protected_checkout_enabled ?? true, bnpl_enabled: existing?.bnpl_enabled ?? false,
  });
  const [delivery, setDelivery] = useState<DeliveryOption[]>(existing?.delivery_options ?? [{ type: "pickup", label: "Pickup from my location", fee: "0", eta_days: 0 }]);
  const [images, setImages] = useState(existing?.images ?? []);
  const [files, setFiles] = useState<File[]>([]);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [titleIdeas, setTitleIdeas] = useState<string[]>([]);
  const [titleBusy, setTitleBusy] = useState(false);

  useEffect(() => { http.get<Category[]>("/categories").then(setCats); }, []);
  const rootCat = cats.find((c) => c.id === root);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF({ ...f, [k]: e.target.value });

  function addFiles(list: FileList | null) {
    if (!list) return;
    const ok = Array.from(list).filter((x) => /^image\/(jpeg|png|webp)$/.test(x.type) && x.size <= 8 * 1024 * 1024);
    if (ok.length < list.length) toast("Some files were skipped (JPEG/PNG/WebP up to 8MB only)", "bad");
    setFiles((cur) => [...cur, ...ok].slice(0, maxImages - images.length));
  }

  async function autoTitle() {
    setTitleBusy(true);
    try {
      const r = await http.post<{ suggestions: string[] }>("/seller/products/title-suggestions", {
        category_id: f.category_id || undefined,
        brand: f.brand || undefined,
        model: f.model || undefined,
        condition: f.condition,
        description: f.description || undefined,
        title: f.title || undefined,
      });
      setTitleIdeas(r.suggestions);
      if (!f.title.trim() && r.suggestions[0]) setF((prev) => ({ ...prev, title: r.suggestions[0] }));
      if (!r.suggestions.length) toast("Add a brand, model or description first", "bad");
    } catch (e) {
      toast(errorMessage(e), "bad");
    } finally {
      setTitleBusy(false);
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null); setErrs({});
    const price = toMoneyString(f.price);
    if (!price) return setErrs({ price: "Enter a valid price" });
    if (!root) return setErrs({ category_id: "Choose a category" });
    if (!f.category_id) return setErrs({ subcategory: "Choose a subcategory" });
    if (!f.state) return setErrs({ state: "Select a state" });
    if (!f.city) return setErrs({ city: "Select a city / area" });
    const body = {
      ...f, price, quantity: Number(f.quantity || 0), brand: f.brand || null, model: f.model || null,
      delivery_options: delivery.map((d) => ({ ...d, fee: toMoneyString(String(d.fee)) ?? "0.00" })),
    };
    setBusy(true);
    try {
      const p = existing
        ? await http.patch<SellerProductDetail>(`/seller/products/${existing.id}`, body)
        : await http.post<SellerProductDetail>("/seller/products", body);
      if (files.length) {
        const fd = new FormData();
        files.forEach((x) => fd.append("files", x));
        await http.post(`/seller/products/${p.id}/images`, fd);
      }
      toast(existing ? "Listing updated" : p.status === "pending_review" ? "Listing submitted for review" : "Your listing is live!");
      router.push("/seller/products");
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) { setErrs(e.fieldErrors); setErr("Please fix the highlighted fields."); }
      else setErr(errorMessage(e));
      setBusy(false);
    }
  }

  async function removeImage(id: string) {
    if (!existing) return;
    try { const p = await http.del<SellerProductDetail>(`/seller/products/${existing.id}/images/${id}`); setImages(p.images); }
    catch (e) { toast(errorMessage(e), "bad"); }
  }

  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      {err && <Alert tone="bad">{err}</Alert>}
      {existing?.rejection_reason && <Alert tone="warn" title="Moderation note">{existing.rejection_reason}</Alert>}
      <section className="card space-y-4 p-4 sm:p-5">
        <h2 className="font-semibold">Photos</h2>
        <div className="flex flex-wrap gap-2">
          {images.map((im, i) => (
            <div key={im.id} className="relative size-24 overflow-hidden rounded-lg">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={im.thumb_url} alt="" className="size-full object-cover" />
              {i === 0 && <span className="absolute bottom-0 inset-x-0 bg-black/60 text-center text-[10px] text-white">Cover</span>}
              <button type="button" onClick={() => removeImage(im.id)} aria-label="Remove photo" className="absolute right-1 top-1 rounded-full bg-white/90 p-0.5"><X className="size-3.5" /></button>
            </div>
          ))}
          {files.map((file, i) => (
            <div key={i} className="relative size-24 overflow-hidden rounded-lg ring-2 ring-brand-300">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={URL.createObjectURL(file)} alt="" className="size-full object-cover" />
              <button type="button" onClick={() => setFiles(files.filter((_, j) => j !== i))} aria-label="Remove photo" className="absolute right-1 top-1 rounded-full bg-white/90 p-0.5"><X className="size-3.5" /></button>
            </div>
          ))}
          {images.length + files.length < maxImages && (
            <label className="grid size-24 cursor-pointer place-items-center rounded-lg border-2 border-dashed border-line text-muted hover:border-brand-600 hover:text-brand-700">
              <span className="flex flex-col items-center text-xs"><ImagePlus className="size-6" />Add photos</span>
              <input type="file" multiple accept="image/jpeg,image/png,image/webp" className="sr-only" onChange={(e) => addFiles(e.target.files)} />
            </label>
          )}
        </div>
        <p className="text-xs text-muted">
          Up to {maxImages} photos{user?.seller?.is_premium ? "" : " on the free plan (Premium allows 10)"}. Clear, well-lit photos sell faster. Photos are compressed for fast loading.
        </p>
      </section>
      <section className="card grid gap-4 p-4 sm:grid-cols-2 sm:p-5">
        <div className="sm:col-span-2">
          <Input label="Title" required maxLength={140} placeholder="e.g. iPhone 13 Pro 256GB — UK Used" value={f.title} onChange={set("title")} error={errs.title} />
          <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
            <button type="button" onClick={autoTitle} disabled={titleBusy}
              className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 hover:underline disabled:opacity-60">
              <Sparkles className="size-3.5" />{titleBusy ? "Creating title…" : "Auto-create title from details"}
            </button>
            <span className="text-xs text-muted">We use your brand, model, condition and description.</span>
          </div>
          {titleIdeas.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {titleIdeas.map((t) => (
                <button type="button" key={t} title="Use this title"
                  onClick={() => { setF((prev) => ({ ...prev, title: t })); setTitleIdeas([]); }}
                  className="max-w-full rounded-lg border border-line bg-white px-2.5 py-1.5 text-left text-xs text-ink transition hover:border-brand-600 hover:text-brand-700">
                  {t}
                </button>
              ))}
            </div>
          )}
        </div>
        <Select label="Category" required value={root} error={errs.category_id} onChange={(e) => {
          const next = cats.find((c) => c.id === e.target.value);
          setRoot(e.target.value);
          // Categories with subcategories require one to be chosen; leaf categories are used directly.
          setF({ ...f, category_id: next && next.children.length === 0 ? next.id : "" });
          setErrs({ ...errs, category_id: "", subcategory: "" });
        }}>
          <option value="">Choose category</option>{cats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
        <Select label="Subcategory" required={!!rootCat?.children.length} value={rootCat?.children.length ? f.category_id : ""}
          onChange={(e) => { setF({ ...f, category_id: e.target.value }); setErrs({ ...errs, subcategory: "" }); }}
          disabled={!rootCat || rootCat.children.length === 0} error={errs.subcategory}
          hint={!rootCat ? "Choose a category first" : rootCat.children.length === 0 ? "No subcategories" : undefined}>
          <option value="">{!rootCat ? "Choose a category first" : "Select subcategory"}</option>
          {rootCat?.children.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </Select>
        <Input label="Brand" value={f.brand} onChange={set("brand")} />
        <Input label="Model" value={f.model} onChange={set("model")} />
        <Select label="Condition" value={f.condition} onChange={set("condition")}>{Object.entries(CONDITION_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
        <Input label="Quantity in stock" type="number" min={0} value={f.quantity} onChange={set("quantity")} error={errs.quantity} />
        <Input label="Price (₦)" inputMode="numeric" required placeholder="1,500,000" value={f.price} onChange={set("price")} error={errs.price} />
        <div className="flex items-end pb-2.5"><Checkbox checked={f.negotiable} onChange={(e) => setF({ ...f, negotiable: e.target.checked })} label="Price is negotiable (accept offers)" /></div>
        <div className="sm:col-span-2"><Textarea label="Description" required rows={6} maxLength={8000} placeholder="Describe condition, specs, what's included, warranty…" value={f.description} onChange={set("description")} error={errs.description} hint="At least 20 characters." /></div>
        <StateCitySelect required state={f.state} city={f.city} errors={{ state: errs.state, city: errs.city }}
          onChange={(v) => { setF({ ...f, ...v }); setErrs({ ...errs, state: "", city: "" }); }} />
      </section>
      <section className="card space-y-3 p-4 sm:p-5">
        <div className="flex items-center justify-between"><h2 className="font-semibold">Delivery options</h2>
          {delivery.length < 5 && <Button type="button" size="sm" variant="secondary" onClick={() => setDelivery([...delivery, { type: "seller_delivery", label: "I deliver", fee: "1500", eta_days: 2 }])}><Plus className="size-4" />Add option</Button>}
        </div>
        <Alert tone="info" title="Courier partnerships coming soon">
          Integrated carriers (GIG, Fez, Shipbubble) are coming soon. Until then choose Pickup or I deliver; if you use a private courier,
          enter the waybill/tracking reference when you dispatch the order.
        </Alert>
        {delivery.map((d, i) => (
          <div key={i} className="grid grid-cols-2 gap-2 rounded-xl border border-line p-3 sm:grid-cols-[140px_1fr_120px_90px_auto]">
            <select aria-label="Delivery type" className="input" value={d.type} onChange={(e) => setDelivery(delivery.map((x, j) => (j === i ? { ...x, type: e.target.value as DeliveryOption["type"] } : x)))}>
              <option value="pickup">Pickup</option><option value="seller_delivery">I deliver</option><option value="courier">Courier (seller-arranged)</option><option value="arrange">Arrange delivery with buyer (outside app)</option>
            </select>
            <input aria-label="Label" className="input" value={d.label} onChange={(e) => setDelivery(delivery.map((x, j) => (j === i ? { ...x, label: e.target.value } : x)))} />
            <input aria-label="Fee" className="input" inputMode="numeric" placeholder="Fee ₦" value={d.fee} onChange={(e) => setDelivery(delivery.map((x, j) => (j === i ? { ...x, fee: e.target.value.replace(/[^\d.]/g, "") } : x)))} />
            <input aria-label="Days" className="input" type="number" min={0} value={d.eta_days} onChange={(e) => setDelivery(delivery.map((x, j) => (j === i ? { ...x, eta_days: Number(e.target.value) } : x)))} />
            {delivery.length > 1 && <button type="button" aria-label="Remove option" onClick={() => setDelivery(delivery.filter((_, j) => j !== i))} className="justify-self-end p-2 text-muted hover:text-red-600"><Trash2 className="size-4" /></button>}
          </div>
        ))}
      </section>
      <section className="card space-y-3 p-4 sm:p-5">
        <h2 className="font-semibold">Payment options</h2>
        <Checkbox checked={f.protected_checkout_enabled} onChange={(e) => setF({ ...f, protected_checkout_enabled: e.target.checked })} label={<><strong>Protected Checkout</strong> — buyers pay through escrow; you&apos;re paid after delivery (5% commission).</>} />
        <Checkbox checked={f.bnpl_enabled} onChange={(e) => setF({ ...f, bnpl_enabled: e.target.checked })} label={<><strong>Goods Flex</strong> — let buyers pay in instalments. You&apos;re still paid in full via escrow.</>} />
      </section>
      <div className="flex justify-end gap-2"><Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button><Button type="submit" size="lg" loading={busy}>{existing ? "Save changes" : "Post listing"}</Button></div>
    </form>
  );
}
