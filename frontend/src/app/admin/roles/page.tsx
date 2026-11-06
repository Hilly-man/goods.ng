"use client";

import { confirmAction, AdminPageHeader } from "@/components/admin-ui";
import { useState } from "react";
import { KeyRound, Lock, Plus } from "lucide-react";
import { Alert, Badge, Button, Checkbox, Input, Modal, PageLoader, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";

type Role = { id: string; code: string; name: string; description: string | null; permissions: string[]; is_system: boolean; members?: number };
type Perm = { code: string; group: string; label: string };

export default function RolesPage() {
  const toast = useToast();
  const { data: roles, reload, error } = useApi<Role[]>("/admin/roles");
  const { data: perms } = useApi<Perm[]>("/admin/permissions");
  const [edit, setEdit] = useState<Role | "new" | null>(null);
  const [f, setF] = useState({ name: "", description: "", permissions: [] as string[] });
  const [busy, setBusy] = useState(false);

  if (error) return <Alert tone="bad">{error}</Alert>;
  if (!roles || !perms) return <PageLoader />;
  const groups = [...new Set(perms.map((p) => p.group))];
  const label = (code: string) => perms.find((p) => p.code === code)?.label ?? code;

  function openEditor(r: Role | "new") {
    setEdit(r);
    setF(r === "new" ? { name: "", description: "", permissions: [] } : { name: r.name, description: r.description ?? "", permissions: r.permissions });
  }
  async function save() {
    setBusy(true);
    try {
      if (edit === "new") await http.post("/admin/roles", f);
      else if (edit) await http.put(`/admin/roles/${edit.id}`, f);
      toast(edit === "new" ? "Role created" : "Role updated — holders must sign in again");
      setEdit(null);
      reload();
    } catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
  }

  return (
    <div className="space-y-4">
      <AdminPageHeader icon={KeyRound} title="Roles & permissions" description="A role is a set of permissions. Each staff member has exactly one role."
        actions={<Button onClick={() => openEditor("new")}><Plus className="size-4" />New custom role</Button>} />
      <div className="grid gap-3 lg:grid-cols-2">
        {roles.map((r) => (
          <section key={r.id} className="card p-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="font-semibold">{r.name} {r.is_system ? <Badge className="ml-1"><Lock className="size-3" />Built-in</Badge> : <Badge tone="info" className="ml-1">Custom</Badge>}</h2>
                <p className="text-sm text-muted">{r.description}</p>
              </div>
              <span className="shrink-0 text-xs text-muted">{r.members ?? 0} staff</span>
            </div>
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {r.permissions.map((p) => <li key={p} className="rounded bg-canvas px-2 py-0.5 text-xs">{label(p)}</li>)}
            </ul>
            {!r.is_system && (
              <div className="mt-3 flex gap-2">
                <Button size="sm" variant="outline" onClick={() => openEditor(r)}>Edit</Button>
                <Button size="sm" variant="ghost" className="text-red-600" onClick={async () => {
                  if (!(await confirmAction({ title: `Delete the "${r.name}" role?`, confirmLabel: "Delete role", tone: "danger" }))) return;
                  try { await http.del(`/admin/roles/${r.id}`); toast("Role deleted"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
                }}>Delete</Button>
              </div>
            )}
          </section>
        ))}
      </div>

      <Modal open={!!edit} onClose={() => setEdit(null)} size="lg" title={edit === "new" ? "New custom role" : `Edit ${f.name}`}
        footer={<><Button variant="ghost" onClick={() => setEdit(null)}>Cancel</Button><Button loading={busy} disabled={!f.name || !f.permissions.length} onClick={save}>Save role</Button></>}>
        <div className="space-y-3">
          <Input label="Role name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
          <Input label="Description" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} />
          {groups.map((g) => (
            <fieldset key={g}>
              <legend className="label">{g}</legend>
              <div className="grid gap-1.5 sm:grid-cols-2">
                {perms.filter((p) => p.group === g).map((p) => (
                  <Checkbox key={p.code} label={p.label} checked={f.permissions.includes(p.code)}
                    onChange={(e) => setF({ ...f, permissions: e.target.checked ? [...f.permissions, p.code] : f.permissions.filter((x) => x !== p.code) })} />
                ))}
              </div>
            </fieldset>
          ))}
          {edit !== "new" && <Alert tone="warn">Saving signs out everyone with this role so their new permissions apply.</Alert>}
        </div>
      </Modal>
    </div>
  );
}
