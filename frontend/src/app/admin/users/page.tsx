"use client";

import { AdminTable, askReason } from "@/components/admin-table";
import { Badge, Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, titleCase } from "@/lib/format";

type U = { id: string; email: string; phone: string | null; full_name: string; role: string; is_active: boolean; phone_verified: boolean; is_seller: boolean; created_at: string; last_login_at: string | null };

export default function Page() {
  const toast = useToast();
  return (
    <><h1 className="mb-4 text-2xl font-bold">Users</h1>
    <AdminTable<U> path="/admin/users" searchable columns={[
      { key: "n", label: "User", render: (u) => <><p className="font-medium">{u.full_name}</p><p className="text-xs text-muted">{u.email} · {u.phone ?? "no phone"}</p></> },
      { key: "r", label: "Role", render: (u) => <Badge tone={u.role === "user" ? "neutral" : "dark"}>{titleCase(u.role)}</Badge> },
      { key: "s", label: "Seller", render: (u) => (u.is_seller ? "Yes" : "—") },
      { key: "v", label: "Phone", render: (u) => (u.phone_verified ? <Badge tone="good">Verified</Badge> : "—") },
      { key: "a", label: "Status", render: (u) => <Badge tone={u.is_active ? "good" : "bad"}>{u.is_active ? "Active" : "Disabled"}</Badge> },
      { key: "j", label: "Joined", render: (u) => date(u.created_at) },
    ]} actions={(u, reload) => (
      <Button size="sm" variant={u.is_active ? "outline" : "secondary"} onClick={async () => {
        const reason = askReason(u.is_active ? "Reason for disabling this account:" : "Reason for re-enabling:"); if (!reason) return;
        try { await http.post(`/admin/users/${u.id}/status`, { is_active: !u.is_active, reason }); toast("Updated"); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
      }}>{u.is_active ? "Disable" : "Enable"}</Button>
    )} /></>
  );
}
