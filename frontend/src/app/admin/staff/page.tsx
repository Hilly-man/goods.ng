"use client";

import { confirmAction, AdminPageHeader } from "@/components/admin-ui";
import { useState } from "react";
import { Copy, MailPlus, ShieldCheck, UserCog, UserPlus } from "lucide-react";
import { Alert, Badge, Button, Input, Modal, PageLoader, Select, useToast } from "@/components/ui";
import { http, errorMessage, ApiError } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { date } from "@/lib/format";
import { useAuth } from "@/components/auth-provider";

type Role = { id: string; code: string; name: string; description: string | null; permissions: string[]; is_system: boolean; members?: number };
type Staff = {
  id: string; full_name: string; email: string; status: "active" | "invited" | "deactivated";
  role: { id?: string; code: string; name: string } | null; is_super_admin: boolean; two_factor_enabled: boolean;
  last_login_at: string | null; created_at: string; invite_expires_at: string | null; dev_invite_link?: string;
};

const STATUS_TONE = { active: "good", invited: "warn", deactivated: "neutral" } as const;

export default function StaffPage() {
  const { user } = useAuth();
  const toast = useToast();
  const { data: staff, setData, error } = useApi<Staff[]>("/admin/staff");
  const { data: roles } = useApi<Role[]>("/admin/roles");
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ full_name: "", email: "", role_id: "" });
  const [errs, setErrs] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [link, setLink] = useState<string | null>(null);

  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!staff || !roles) return <PageLoader />;

  const replace = (u: Staff) => setData(staff.map((s) => (s.id === u.id ? u : s)));
  async function act(key: string, fn: () => Promise<Staff>, msg: string) {
    setBusy(key);
    try {
      const u = await fn();
      replace(u);
      if (u.dev_invite_link) setLink(u.dev_invite_link);
      toast(msg);
    } catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(null); }
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setBusy("create"); setErrs({});
    try {
      const u = await http.post<Staff>("/admin/staff", f);
      setData([...staff!, u]);
      setLink(u.dev_invite_link ?? null);
      setOpen(false);
      setF({ full_name: "", email: "", role_id: "" });
      toast(`Invitation sent to ${u.email}`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) setErrs(e.fieldErrors);
      else toast(errorMessage(e), "bad");
    } finally { setBusy(null); }
  }

  return (
    <div className="space-y-4">
      <AdminPageHeader icon={UserCog} title="Admin team" description="Staff accounts are separate from customer accounts and can only be created here."
        actions={<Button onClick={() => { setOpen(true); setF((x) => ({ ...x, role_id: x.role_id || roles.find((r) => r.code === "customer_support")?.id || "" })); }}>
          <UserPlus className="size-4" />Invite staff
        </Button>} />

      {link && (
        <Alert tone="info" title="Development mode — invitation link">
          Email isn&apos;t connected, so share this link with the new staff member:
          <span className="mt-1 flex items-center gap-2"><code className="break-all text-xs">{link}</code>
            <button aria-label="Copy link" onClick={() => { navigator.clipboard.writeText(link); toast("Link copied", "info"); }}><Copy className="size-4" /></button></span>
        </Alert>
      )}

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[820px] text-sm">
          <thead><tr className="border-b border-line bg-canvas/60 text-left text-xs uppercase tracking-wide text-muted">
            <th className="p-3">Staff member</th><th className="p-3">Role</th><th className="p-3">Status</th><th className="p-3">2FA</th><th className="p-3">Last sign-in</th><th className="p-3" />
          </tr></thead>
          <tbody>
            {staff.map((s) => {
              const self = s.id === user?.id;
              return (
                <tr key={s.id} className="border-b border-line/60 align-middle">
                  <td className="p-3"><p className="font-medium">{s.full_name}{self && <span className="ml-1.5 text-xs text-muted">(you)</span>}</p><p className="text-xs text-muted">{s.email}</p></td>
                  <td className="p-3">
                    <select aria-label={`Role for ${s.full_name}`} className="input h-9 w-48 py-1 text-sm" disabled={self || busy === s.id}
                      value={roles.find((r) => r.code === s.role?.code)?.id ?? ""}
                      onChange={async (e) => {
                        const r = roles.find((x) => x.id === e.target.value);
                        if (r && await confirmAction({ title: `Make ${s.full_name} ${r.name}?`, message: "They'll be signed out and get the new permissions when they sign back in.", confirmLabel: "Change role" }))
                          act(s.id, () => http.patch(`/admin/staff/${s.id}`, { role_id: r.id }), "Role updated");
                      }}>
                      {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  </td>
                  <td className="p-3"><Badge tone={STATUS_TONE[s.status]} className="capitalize">{s.status}</Badge>
                    {s.status === "invited" && s.invite_expires_at && <p className="mt-0.5 text-[11px] text-muted">expires {date(s.invite_expires_at, true)}</p>}</td>
                  <td className="p-3">{s.two_factor_enabled ? <span className="inline-flex items-center gap-1 text-brand-700"><ShieldCheck className="size-4" />On</span> : <span className="text-muted">Off</span>}</td>
                  <td className="p-3 text-muted">{date(s.last_login_at, true)}</td>
                  <td className="p-3 text-right">
                    <div className="flex justify-end gap-1.5">
                      {s.status === "invited" && <Button size="sm" variant="ghost" loading={busy === `r${s.id}`} onClick={() => act(`r${s.id}`, () => http.post(`/admin/staff/${s.id}/resend-invite`), "Invitation re-sent")}><MailPlus className="size-4" />Resend</Button>}
                      {!self && (s.status === "deactivated"
                        ? <Button size="sm" variant="secondary" onClick={() => act(s.id, () => http.patch(`/admin/staff/${s.id}`, { is_active: true }), "Reactivated")}>Reactivate</Button>
                        : <Button size="sm" variant="outline" className="text-red-600" onClick={async () => { if (await confirmAction({ title: `Deactivate ${s.full_name}?`, message: "They'll be signed out immediately and can't sign in until reactivated.", confirmLabel: "Deactivate", tone: "danger" })) act(s.id, () => http.patch(`/admin/staff/${s.id}`, { is_active: false }), "Deactivated"); }}>Deactivate</Button>)}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="Invite a staff member"
        footer={<><Button variant="ghost" onClick={() => setOpen(false)}>Cancel</Button><Button type="submit" form="invite-form" loading={busy === "create"}>Send invitation</Button></>}>
        <form id="invite-form" onSubmit={create} className="space-y-3">
          <Input label="Full name" required value={f.full_name} onChange={(e) => setF({ ...f, full_name: e.target.value })} error={errs.full_name} />
          <Input label="Work email" type="email" required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} error={errs.email}
            hint="Must not already be used by a customer account. They'll get a link to set their own password." />
          <Select label="Role" value={f.role_id} onChange={(e) => setF({ ...f, role_id: e.target.value })}>
            {roles.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          </Select>
          {(() => {
            const r = roles.find((x) => x.id === f.role_id);
            return r ? <p className="rounded-lg bg-canvas p-3 text-xs text-muted">{r.description} <b className="text-ink">{r.permissions.length} permission{r.permissions.length === 1 ? "" : "s"}.</b></p> : null;
          })()}
        </form>
      </Modal>
    </div>
  );
}
