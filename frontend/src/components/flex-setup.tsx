"use client";

import Link from "next/link";
import { useState } from "react";
import clsx from "clsx";
import { BadgeCheck, Briefcase, Building2, CheckCircle2, Circle, Clock, Landmark, Lock, ShieldCheck, UserCheck } from "lucide-react";
import { http, errorMessage, ApiError } from "@/lib/api";
import { naira, date, titleCase } from "@/lib/format";
import { Alert, Badge, Button, Input, Modal, Select, useToast } from "./ui";

declare global {
  interface Window {
    MonoConnect?: { setup: (config: Record<string, unknown>) => void; open: () => void };
  }
}

type BankOpts = {
  provider: string; mock_personas?: Record<string, string>; mock_banks?: string[]; notice?: string;
  public_key?: string; customer?: { name: string; email: string };
};

export type FlexStatus = {
  credit_limit: string;
  available_to_spend: string;
  binding_cap: "statement" | "verification" | "history" | "lender" | "guarantee" | null;
  caps: Record<"statement" | "verification" | "history" | "lender" | "guarantee", string>;
  tips: string[];
  steps: { phone: boolean; bvn: boolean; bank: boolean; employment: boolean; guarantor: string | null };
  completed_plans: number;
  running_plan: { application_id: string; status: string; order_id: string | null } | null;
  can_apply: boolean;
  profile: {
    bvn_last4: string | null; bvn_verified_at: string | null; employment_type: string | null; employer_name: string | null;
    work_email: string | null; cac_number: string | null; employment_verified_at: string | null; employment_method: string | null;
    employment_pending: boolean;
  };
  guarantor: { full_name: string; phone: string; relationship: string; status: string; consented_at: string | null; amount_guaranteed: string } | null;
  assessment: {
    created_at: string; expires_at: string; months_analysed: number; monthly_income: string; income_source: string;
    monthly_debt: string; affordable_instalment: string; statement_limit: string; score: number; reasons: string[];
    monthly_inflows: { month: string; eligible_inflow: string; salary: string }[];
    bank: { name: string; account_last4: string };
  } | null;
  rules: { tier1_max: string; tier2_max: string; lender_max: string; max_dti: string };
  dev_link?: string;
};

const CAP_LABEL = {
  statement: "your income & existing loans",
  verification: "your verification level",
  history: "your Goods Flex repayment history",
  lender: "the lender's maximum",
  guarantee: "the amount your guarantor agreed to",
};

export function FlexLimitCard({ s }: { s: FlexStatus }) {
  const limit = Number(s.credit_limit);
  return (
    <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-accent-400 to-accent-500 p-5 text-ink shadow-[var(--shadow-pop)] sm:p-6">
      <p className="text-sm font-medium text-brand-800">Your Goods Flex limit</p>
      <p className="mt-1 text-4xl font-extrabold tracking-tight">{limit > 0 ? naira(s.credit_limit) : "Not set up"}</p>
      {limit > 0 && s.binding_cap && <p className="mt-1 text-sm text-ink/75">Limited by {CAP_LABEL[s.binding_cap]}</p>}
      {s.running_plan ? (
        <div className="mt-4 rounded-xl bg-ink/5 p-3 text-sm ring-1 ring-ink/10">
          <p className="font-semibold">You have a Goods Flex plan running</p>
          <p className="text-ink/75">You can start a new plan once it&apos;s fully paid. Only one plan can run at a time.</p>
          {s.running_plan.order_id && <Link href={`/orders/${s.running_plan.order_id}`} className="mt-1 inline-block font-semibold underline">View plan order</Link>}
        </div>
      ) : limit > 0 ? (
        <p className="mt-4 text-sm text-ink/75">Look for the <b>Goods Flex</b> option on eligible items up to this amount.</p>
      ) : (
        <p className="mt-4 text-sm text-ink/75">Complete the steps below to see how much you can buy now and pay later.</p>
      )}
      {s.tips.map((t) => <p key={t} className="mt-2 text-sm font-medium text-brand-800">→ {t}</p>)}
    </section>
  );
}

function Step({ n, title, done, pending, icon, children, sub, locked }: {
  n: number; title: string; done: boolean; pending?: boolean; icon: React.ReactNode; children?: React.ReactNode; sub: string; locked?: string;
}) {
  return (
    <section className={clsx("card p-4 sm:p-5", locked && "opacity-60")}>
      <div className="flex items-start gap-3">
        <span className={clsx("grid size-10 shrink-0 place-items-center rounded-xl", done ? "bg-brand-50 text-brand-700" : "bg-accent-500/25 text-brand-800")}>{icon}</span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-semibold">{n}. {title}</h3>
            {done ? <Badge tone="good"><CheckCircle2 className="size-3.5" />Done</Badge> : pending ? <Badge tone="warn"><Clock className="size-3.5" />Pending</Badge> : <Badge><Circle className="size-3" />To do</Badge>}
          </div>
          <p className="mt-0.5 text-sm text-muted">{sub}</p>
          {locked ? <p className="mt-2 flex items-center gap-1.5 text-sm text-muted"><Lock className="size-4" />{locked}</p> : children && <div className="mt-3">{children}</div>}
        </div>
      </div>
    </section>
  );
}

export function FlexSteps({ s, onChange }: { s: FlexStatus; onChange: (s: FlexStatus) => void }) {
  const toast = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [bvn, setBvn] = useState("");
  const [dob, setDob] = useState("");
  const [bankOpen, setBankOpen] = useState(false);
  const [bankOpts, setBankOpts] = useState<BankOpts | null>(null);
  const [persona, setPersona] = useState("salary_earner");
  const [bank, setBank] = useState("GTBank");
  const [emp, setEmp] = useState({ employment_type: s.profile.employment_type ?? "employed", employer_name: s.profile.employer_name ?? "", job_title: "", work_email: s.profile.work_email ?? "", cac_number: s.profile.cac_number ?? "", monthly_income_declared: "" });
  const [g, setG] = useState({ full_name: "", phone: "", relationship: "", bvn: "" });
  const [devLink, setDevLink] = useState<string | null>(null);

  async function run(key: string, fn: () => Promise<FlexStatus>, msg: string) {
    setBusy(key);
    setErrs({});
    try {
      const r = await fn();
      onChange(r);
      setDevLink(r.dev_link ?? null);
      toast(msg);
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) setErrs(e.fieldErrors);
      toast(errorMessage(e), "bad");
      return false;
    } finally {
      setBusy(null);
    }
  }

  function openMono() {
    if (!bankOpts?.public_key) {
      toast("Bank linking is not configured on this environment", "bad");
      return;
    }
    const start = () => {
      if (!window.MonoConnect) {
        toast("Could not load the bank widget. Please try again.", "bad");
        return;
      }
      window.MonoConnect.setup({
        key: bankOpts.public_key,
        scope: "auth",
        data: { customer: bankOpts.customer },
        onSuccess: ({ code }: { code: string }) => {
          setBankOpen(false);
          run("bank", () => http.post("/bnpl/profile/bank/connect", { code }), "Bank statement analysed");
        },
        onClose: () => {},
      });
      window.MonoConnect.open();
    };
    if (window.MonoConnect) return start();
    const script = document.createElement("script");
    script.src = "https://connect.mono.co/connect.js";
    script.onload = start;
    script.onerror = () => toast("Could not load the bank widget. Check your connection.", "bad");
    document.body.appendChild(script);
  }

  const a = s.assessment;
  return (
    <div className="space-y-3">
      {!s.steps.phone && <Alert tone="warn" title="Verify your phone number first"><Link href="/account" className="underline">Go to your account</Link> to verify by SMS code.</Alert>}

      <Step n={1} title="Verify your BVN" done={s.steps.bvn} icon={<BadgeCheck className="size-5" />}
        sub="Confirms your identity. Your BVN is encrypted and never shown in full." locked={!s.steps.phone ? "Verify your phone first" : undefined}>
        {s.steps.bvn ? (
          <p className="text-sm">BVN ••••••{s.profile.bvn_last4} verified {date(s.profile.bvn_verified_at)}</p>
        ) : (
          <form className="grid gap-3 sm:grid-cols-[1fr_200px_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); run("bvn", () => http.post("/bnpl/profile/bvn", { bvn, date_of_birth: dob || undefined }), "BVN verified"); }}>
            <Input label="BVN (11 digits)" inputMode="numeric" maxLength={11} value={bvn} onChange={(e) => setBvn(e.target.value.replace(/\D/g, ""))} error={errs.bvn} hint="Dial *565*0# to get your BVN" />
            <Input label="Date of birth" type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
            <Button type="submit" loading={busy === "bvn"} disabled={bvn.length !== 11}>Verify</Button>
          </form>
        )}
      </Step>

      <Step n={2} title="Connect your bank account" done={s.steps.bank} icon={<Landmark className="size-5" />}
        sub="We read 6 months of transactions (read-only) to work out what you can comfortably afford." locked={!s.steps.bvn ? "Verify your BVN first" : undefined}>
        {a && (
          <div className="mb-3 grid gap-2 rounded-xl bg-canvas p-3 text-sm sm:grid-cols-4">
            <div><p className="text-xs text-muted">Monthly income</p><p className="font-semibold">{naira(a.monthly_income)}</p><p className="text-[11px] text-muted">{a.income_source === "salary" ? "Salary detected" : "From account inflows"}</p></div>
            <div><p className="text-xs text-muted">Existing loan repayments</p><p className="font-semibold">{naira(a.monthly_debt)}/mo</p></div>
            <div><p className="text-xs text-muted">Affordable instalment</p><p className="font-semibold">{naira(a.affordable_instalment)}/mo</p></div>
            <div><p className="text-xs text-muted">Bank</p><p className="font-semibold">{a.bank.name} ••{a.bank.account_last4}</p><p className="text-[11px] text-muted">Valid until {date(a.expires_at)}</p></div>
            {a.reasons.length > 0 && <ul className="list-disc pl-4 text-xs text-muted sm:col-span-4">{a.reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
          </div>
        )}
        <Button variant={s.steps.bank ? "outline" : "primary"} size="sm" onClick={async () => {
          try {
            setBankOpts(await http.get<BankOpts>("/bnpl/profile/bank/link-session"));
            setBankOpen(true);
          } catch (e) { toast(errorMessage(e), "bad"); }
        }}>{s.steps.bank ? "Refresh with latest statement" : "Connect bank account"}</Button>
      </Step>

      <Step n={3} title="Verify your workplace (optional)" done={s.steps.employment} pending={s.profile.employment_pending} icon={<Briefcase className="size-5" />}
        sub={`Raises your cap to ${naira(s.rules.tier2_max)}. Employees confirm a work email; business owners add their CAC number.`}
        locked={!s.steps.bvn ? "Verify your BVN first" : undefined}>
        {s.steps.employment ? (
          <p className="text-sm">{s.profile.employment_method === "work_email" ? `Work email ${s.profile.work_email} confirmed` : `CAC ${s.profile.cac_number} with business inflows confirmed`}{s.profile.employer_name ? ` · ${s.profile.employer_name}` : ""}</p>
        ) : (
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => {
            e.preventDefault();
            run("emp", () => http.post("/bnpl/profile/employment", { ...emp, monthly_income_declared: emp.monthly_income_declared.replace(/[^\d]/g, "") || undefined }),
              emp.employment_type === "employed" ? "Check your work email for a confirmation link" : "Business details saved");
          }}>
            <Select label="I am" value={emp.employment_type} onChange={(e) => setEmp({ ...emp, employment_type: e.target.value })}>
              <option value="employed">Employed (salary earner)</option><option value="self_employed">Self-employed</option><option value="business_owner">Business owner</option>
            </Select>
            <Input label={emp.employment_type === "employed" ? "Employer name" : "Business name"} value={emp.employer_name} onChange={(e) => setEmp({ ...emp, employer_name: e.target.value })} error={errs.employer_name} />
            {emp.employment_type === "employed" ? (
              <>
                <Input label="Job title" value={emp.job_title} onChange={(e) => setEmp({ ...emp, job_title: e.target.value })} />
                <Input label="Work email" type="email" placeholder="you@company.com" value={emp.work_email} onChange={(e) => setEmp({ ...emp, work_email: e.target.value })} error={errs.work_email} hint="Not Gmail/Yahoo — we send a confirmation link" />
              </>
            ) : (
              <Input label="CAC registration number" placeholder="RC123456 or BN1234567" value={emp.cac_number} onChange={(e) => setEmp({ ...emp, cac_number: e.target.value })} error={errs.cac_number} hint="Verified together with business inflows in your bank statement" />
            )}
            <div className="sm:col-span-2"><Button type="submit" size="sm" loading={busy === "emp"}>{s.profile.employment_pending ? "Update & resend" : "Save workplace"}</Button></div>
            {s.profile.employment_pending && s.profile.work_email && <p className="text-sm text-amber-700 sm:col-span-2">Waiting for you to click the link sent to {s.profile.work_email}.</p>}
          </form>
        )}
      </Step>

      <Step n={4} title="Add a guarantor" done={s.steps.guarantor === "consented"} pending={s.steps.guarantor === "pending_consent"}
        icon={<UserCheck className="size-5" />} sub="Required before you can use Goods Flex. Your guarantor confirms by SMS link."
        locked={!s.steps.bank ? "Connect your bank account first" : undefined}>
        {s.guarantor && (
          <div className="mb-3 space-y-2 text-sm">
            <p>{s.guarantor.full_name} ({s.guarantor.relationship}, {s.guarantor.phone}) — <b>{titleCase(s.guarantor.status)}</b>
              {Number(s.guarantor.amount_guaranteed) > 0 && <> · guaranteeing up to {naira(s.guarantor.amount_guaranteed)}</>}
            </p>
            <div className="flex flex-wrap gap-2">
              {s.steps.guarantor === "pending_consent" && (
                <Button type="button" variant="outline" size="sm" loading={busy === "gresend"}
                  onClick={() => run("gresend", () => http.post("/bnpl/profile/guarantor/resend"), "Request resent")}>Resend SMS</Button>
              )}
              <Button type="button" variant="ghost" size="sm" loading={busy === "gcancel"}
                onClick={async () => {
                  if (!window.confirm("Cancel this guarantor request? Your Goods Flex limit will drop to zero until another guarantor consents.")) return;
                  await run("gcancel", () => http.del("/bnpl/profile/guarantor"), "Guarantor request cancelled");
                }}>Cancel guarantor</Button>
            </div>
          </div>
        )}
        {s.steps.guarantor !== "consented" && (
          <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => { e.preventDefault(); run("g", () => http.post("/bnpl/profile/guarantor", g), "Request sent to your guarantor"); }}>
            <Input label="Guarantor's full name (as on BVN)" value={g.full_name} onChange={(e) => setG({ ...g, full_name: e.target.value })} />
            <Input label="Guarantor's phone" type="tel" value={g.phone} onChange={(e) => setG({ ...g, phone: e.target.value })} error={errs.phone} />
            <Input label="Relationship" placeholder="e.g. Brother, Employer" value={g.relationship} onChange={(e) => setG({ ...g, relationship: e.target.value })} />
            <Input label="Guarantor's BVN" inputMode="numeric" maxLength={11} value={g.bvn} onChange={(e) => setG({ ...g, bvn: e.target.value.replace(/\D/g, "") })} error={errs.bvn} />
            <div className="sm:col-span-2"><Button type="submit" size="sm" loading={busy === "g"}>{s.guarantor ? "Send to a different guarantor" : "Send request"}</Button></div>
          </form>
        )}
      </Step>

      {devLink && (
        <Alert tone="info" title="Development mode">
          Email/SMS isn&apos;t connected, so here is the link that would be sent: <a href={devLink} className="break-all font-semibold underline">{devLink}</a>
        </Alert>
      )}

      <Modal open={bankOpen} onClose={() => setBankOpen(false)} title="Connect your bank" footer={
        bankOpts?.provider === "mono" ? (
          <Button onClick={openMono} disabled={!bankOpts.public_key}>Continue to bank login</Button>
        ) : (
          <Button loading={busy === "bank"} disabled={bankOpts?.provider !== "mock"} onClick={async () => {
            if (await run("bank", () => http.post("/bnpl/profile/bank/connect", { code: `mock:${persona}:${bank}` }), "Bank statement analysed")) setBankOpen(false);
          }}>Connect</Button>
        )}>
        {bankOpts?.provider === "mock" ? (
          <div className="space-y-3">
            <Alert tone="warn">{bankOpts.notice}</Alert>
            <Select label="Bank" value={bank} onChange={(e) => setBank(e.target.value)}>{bankOpts.mock_banks?.map((b) => <option key={b}>{b}</option>)}</Select>
            <fieldset className="space-y-2">
              <legend className="label">Test customer profile</legend>
              {Object.entries(bankOpts.mock_personas ?? {}).map(([k, v]) => (
                <label key={k} className={clsx("flex cursor-pointer gap-2.5 rounded-lg border p-3 text-sm", persona === k ? "border-brand-600 bg-brand-50" : "border-line")}>
                  <input type="radio" name="persona" checked={persona === k} onChange={() => setPersona(k)} className="mt-0.5 accent-brand-700" />{v}
                </label>
              ))}
            </fieldset>
          </div>
        ) : bankOpts?.provider === "mono" ? (
          <Alert tone="info" title="Secure bank linking">{bankOpts.notice}</Alert>
        ) : (
          <p className="text-sm">Bank linking is not configured on this environment.</p>
        )}
        <p className="mt-3 flex gap-2 text-xs text-muted"><ShieldCheck className="size-4 shrink-0 text-brand-700" />Read-only access. We can&apos;t move money from your account. We only use your transactions to calculate your limit and prevent fraud. By continuing you consent to this processing under the Nigeria Data Protection Act 2023; you can withdraw consent by contacting privacy@goods.ng.</p>
      </Modal>
    </div>
  );
}

export const FlexIcons = { Building2 };
