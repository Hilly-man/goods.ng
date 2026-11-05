"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Checkbox, Input, PageLoader, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";

type FlexRules = {
  max_dti: string; tier1_max: string; tier2_max: string; lender_max: string;
  first_plan_cap: string; growth_per_completed_plan: string; assessment_valid_days: string;
  max_active_guarantees: string;
};
type S = { fees: { commission_rate: string; protection_fee_rate: string; protection_fee_cap: string }; listing_moderation_required: { enabled: boolean }; flex_rules: FlexRules };

export default function Page() {
  const [s, setS] = useState<S | null>(null);
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  useEffect(() => { http.get<S>("/admin/settings").then(setS).catch((e) => toast(errorMessage(e), "bad")); }, [toast]);
  if (!s) return <PageLoader />;
  const pct = (v: string) => String(Math.round(Number(v) * 10000) / 100);
  const frac = (v: string) => (Number(v) / 100).toFixed(4);
  const setFlex = (k: keyof FlexRules, v: string) => setS({ ...s, flex_rules: { ...s.flex_rules, [k]: v } });
  return (
    <form className="max-w-xl space-y-4" onSubmit={async (e) => {
      e.preventDefault(); setBusy(true);
      try { setS(await http.put<S>("/admin/settings", { fees: s.fees, listing_moderation_required: s.listing_moderation_required.enabled, flex_rules: s.flex_rules })); toast("Settings saved (audit logged)"); }
      catch (err) { toast(errorMessage(err), "bad"); } finally { setBusy(false); }
    }}>
      <h1 className="text-2xl font-bold">Platform settings</h1>
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
        </div>
      </section>
      <Button type="submit" loading={busy}>Save settings</Button>
    </form>
  );
}
