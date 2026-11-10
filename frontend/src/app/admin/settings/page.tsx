"use client";

import { Megaphone, Settings } from "lucide-react";
import { AdminPageHeader } from "@/components/admin-ui";
import { useEffect, useState } from "react";
import { Alert, Button, Checkbox, Input, PageLoader, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";

type FlexRules = {
  max_dti: string; tier1_max: string; tier2_max: string; lender_max: string;
  first_plan_cap: string; growth_per_completed_plan: string; assessment_valid_days: string;
  max_active_guarantees: string; first_payment_rate: string; financed_rate: string; monthly_interest_rate: string;
};
type Marketing = {
  feed_enabled: boolean; feed_excluded_categories: string[]; meta_pixel_id: string; ga4_id: string; google_ads_id: string;
  google_ads_purchase_label: string; capi_configured?: boolean; feed_token_required?: boolean;
};
type S = { fees: { commission_rate: string; protection_fee_rate: string; protection_fee_cap: string }; listing_moderation_required: { enabled: boolean }; flex_rules: FlexRules; marketing: Marketing };
type Cat = { slug: string; name: string };

export default function Page() {
  const [s, setS] = useState<S | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const [cats, setCats] = useState<Cat[]>([]);
  useEffect(() => { http.get<S>("/admin/settings").then(setS).catch((e) => toast(errorMessage(e), "bad")); }, [toast]);
  useEffect(() => { http.get<Cat[]>("/categories").then(setCats).catch(() => {}); }, []);
  if (!s) return <PageLoader />;
  const pct = (v: string) => String(Math.round(Number(v) * 10000) / 100);
  const frac = (v: string) => (Number(v) / 100).toFixed(4);
  const setFlex = (k: keyof FlexRules, v: string) => setS({ ...s, flex_rules: { ...s.flex_rules, [k]: v } });
  const m = s.marketing;
  const setM = (patch: Partial<Marketing>) => setS({ ...s, marketing: { ...m, ...patch } });
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "").replace(/\/$/, "");
  const feedUrl = (f: string) => `${site}/api/v1/feeds/${f}${m.feed_token_required ? "?token=YOUR_FEED_TOKEN" : ""}`;
  return (
    <form className="max-w-xl space-y-4" onSubmit={async (e) => {
      e.preventDefault(); setBusy(true);
      const { capi_configured: _c, feed_token_required: _t, ...marketing } = m;
      void _c; void _t;
      try { setS(await http.put<S>("/admin/settings", { fees: s.fees, listing_moderation_required: s.listing_moderation_required.enabled, flex_rules: s.flex_rules, marketing })); toast("Settings saved (audit logged)"); }
      catch (err) { toast(errorMessage(err), "bad"); } finally { setBusy(false); }
    }}>
      <AdminPageHeader icon={Settings} title="Platform settings" description="Fees, Goods Flex credit rules and ads for the whole marketplace." />
      <Alert tone="warn">Fee changes apply to new checkouts only. Existing orders keep the fees they were created with.</Alert>
      <section className="card grid gap-3 p-5 sm:grid-cols-3">
        <Input label="Seller commission (%)" inputMode="decimal" value={pct(s.fees.commission_rate)} onChange={(e) => setS({ ...s, fees: { ...s.fees, commission_rate: frac(e.target.value) } })} />
        <Input label="Protection fee (%)" inputMode="decimal" value={pct(s.fees.protection_fee_rate)} onChange={(e) => setS({ ...s, fees: { ...s.fees, protection_fee_rate: frac(e.target.value) } })} />
        <Input label="Protection fee cap (₦)" inputMode="numeric" value={s.fees.protection_fee_cap} onChange={(e) => setS({ ...s, fees: { ...s.fees, protection_fee_cap: e.target.value } })} />
      </section>
      <section className="card p-5">
        <Checkbox checked={s.listing_moderation_required.enabled} onChange={(e) => setS({ ...s, listing_moderation_required: { enabled: e.target.checked } })} label="Require admin approval before new listings go live" />
      </section>
      <section className="card space-y-3 p-5">
        <div>
          <h2 className="font-semibold">Goods Flex credit rules</h2>
          <p className="text-sm text-muted">Caps must increase: tier 1 ≤ tier 2 ≤ lender maximum. Changes apply to the next assessment or application.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Max debt-to-income (%)" inputMode="decimal" value={pct(s.flex_rules.max_dti)} onChange={(e) => setFlex("max_dti", frac(e.target.value))} />
          <Input label="Assessment valid for (days)" inputMode="numeric" value={s.flex_rules.assessment_valid_days} onChange={(e) => setFlex("assessment_valid_days", e.target.value.replace(/\D/g, ""))} />
          <Input label="Tier 1 cap (BVN + bank) ₦" inputMode="numeric" value={s.flex_rules.tier1_max} onChange={(e) => setFlex("tier1_max", e.target.value.replace(/[^\d.]/g, ""))} />
          <Input label="Tier 2 cap (+ workplace) ₦" inputMode="numeric" value={s.flex_rules.tier2_max} onChange={(e) => setFlex("tier2_max", e.target.value.replace(/[^\d.]/g, ""))} />
          <Input label="Lender maximum (+ guarantor) ₦" inputMode="numeric" value={s.flex_rules.lender_max} onChange={(e) => setFlex("lender_max", e.target.value.replace(/[^\d.]/g, ""))} />
          <Input label="First plan cap ₦" inputMode="numeric" value={s.flex_rules.first_plan_cap} onChange={(e) => setFlex("first_plan_cap", e.target.value.replace(/[^\d.]/g, ""))} />
          <Input label="Limit growth per repaid plan (%)" inputMode="decimal" value={pct(s.flex_rules.growth_per_completed_plan)} onChange={(e) => setFlex("growth_per_completed_plan", frac(e.target.value))} />
          <Input label="Max customers per guarantor" inputMode="numeric" value={s.flex_rules.max_active_guarantees} onChange={(e) => setFlex("max_active_guarantees", e.target.value.replace(/\D/g, ""))} />
          <Input label="First payment (% of price, incl. interest)" inputMode="decimal" value={pct(s.flex_rules.first_payment_rate)} onChange={(e) => setFlex("first_payment_rate", frac(e.target.value))} />
          <Input label="Financed share (% of price)" inputMode="decimal" value={pct(s.flex_rules.financed_rate)} onChange={(e) => setFlex("financed_rate", frac(e.target.value))} />
          <Input label="Interest (% of price, per month)" inputMode="decimal" value={pct(s.flex_rules.monthly_interest_rate)} onChange={(e) => setFlex("monthly_interest_rate", frac(e.target.value))} />
        </div>
      </section>
      <section className="card space-y-4 p-5">
        <div>
          <h2 className="flex items-center gap-2 font-semibold"><Megaphone className="size-4 text-accent-600" />Ads on Google & Facebook</h2>
          <p className="text-sm text-muted">Product feeds of quality-checked Premium listings, plus ad-measurement IDs. Tracking only runs for visitors who accept marketing cookies.</p>
        </div>
        <Checkbox checked={m.feed_enabled} onChange={(e) => setM({ feed_enabled: e.target.checked })} label="Publish product feeds for Google Merchant Center and Meta Commerce Manager" />
        {m.feed_enabled && (
          <div className="space-y-1.5 rounded-lg bg-canvas p-3 text-xs">
            <p className="font-semibold">Paste these into each platform as a scheduled feed:</p>
            <p>Google Merchant Center: <code className="break-all">{feedUrl("google.xml")}</code></p>
            <p>Meta Commerce Manager: <code className="break-all">{feedUrl("meta.csv")}</code></p>
          </div>
        )}
        <div>
          <p className="mb-1.5 text-sm font-medium">Keep these categories out of the feeds</p>
          <div className="flex flex-wrap gap-1.5">
            {cats.map((c) => {
              const on = m.feed_excluded_categories.includes(c.slug);
              return (
                <button key={c.slug} type="button" aria-pressed={on}
                  onClick={() => setM({ feed_excluded_categories: on ? m.feed_excluded_categories.filter((x) => x !== c.slug) : [...m.feed_excluded_categories, c.slug] })}
                  className={`rounded-full px-3 py-1 text-xs font-medium ring-1 ${on ? "bg-red-50 text-red-700 ring-red-200 line-through" : "bg-white ring-line hover:bg-canvas"}`}>
                  {c.name}
                </button>
              );
            })}
          </div>
          <p className="mt-1 text-xs text-muted">Google Shopping doesn&apos;t accept property and restricts vehicles.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input label="Meta Pixel ID" placeholder="123456789012345" value={m.meta_pixel_id} onChange={(e) => setM({ meta_pixel_id: e.target.value.trim() })} />
          <Input label="Google Analytics 4 ID" placeholder="G-XXXXXXXXXX" value={m.ga4_id} onChange={(e) => setM({ ga4_id: e.target.value.trim() })} />
          <Input label="Google Ads tag ID" placeholder="AW-123456789" value={m.google_ads_id} onChange={(e) => setM({ google_ads_id: e.target.value.trim() })} />
          <Input label="Google Ads purchase conversion label" placeholder="AbCdEfGh123" value={m.google_ads_purchase_label} onChange={(e) => setM({ google_ads_purchase_label: e.target.value.trim() })} />
        </div>
        <p className={`rounded-lg p-3 text-xs ${m.capi_configured ? "bg-brand-50 text-brand-900" : "bg-amber-50 text-amber-900"}`}>
          {m.capi_configured
            ? "Meta Conversions API is configured: purchases from consenting buyers are also reported server-side."
            : "Meta Conversions API isn't configured. Set META_CAPI_ACCESS_TOKEN on the API server (never here) to report purchases server-side."}
        </p>
      </section>
      <Button type="submit" loading={busy}>Save settings</Button>
    </form>
  );
}
