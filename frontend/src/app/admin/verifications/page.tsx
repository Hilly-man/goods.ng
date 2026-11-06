"use client";

import { BadgeCheck } from "lucide-react";
import { AdminPageHeader, FilterChips } from "@/components/admin-ui";
import Link from "next/link";
import { useState } from "react";
import { AdminTable, askReason } from "@/components/admin-table";
import { Button, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { date, titleCase } from "@/lib/format";

type V = { id: string; seller: { store_name: string; slug: string; current_level: string }; level_requested: string; document_type: string; document_number: string; business_name: string | null; status: string; created_at: string };

export default function Page() {
  const toast = useToast();
  const [status, setStatus] = useState("pending");
  const [revealed, setRevealed] = useState<Record<string, string>>({});
  return (
    <><AdminPageHeader icon={BadgeCheck} title="Seller verification" description="Check identity and business documents, then approve or reject." />
    <AdminTable<V> path="/admin/verifications" query={{ status }} filters={<FilterChips label="Status" value={status} onChange={setStatus} options={[{ value: "pending", label: "Pending" }, { value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }]} />} columns={[
      { key: "s", label: "Seller", render: (v) => <><Link href={`/store/${v.seller.slug}`} className="font-medium text-brand-700">{v.seller.store_name}</Link><p className="text-xs text-muted">Current: {titleCase(v.seller.current_level)}</p></> },
      { key: "l", label: "Requested", render: (v) => titleCase(v.level_requested) },
      { key: "d", label: "Document", render: (v) => <>{titleCase(v.document_type)} <span className="font-mono">{revealed[v.id] ?? v.document_number}</span>{v.business_name && <p className="text-xs">{v.business_name}</p>}</> },
      { key: "t", label: "Submitted", render: (v) => date(v.created_at) },
    ]} actions={(v, reload) => (<>
      <Button size="sm" variant="ghost" onClick={async () => { try { const r = await http.get<{ document_number: string }>(`/admin/verifications/${v.id}/document-number`); setRevealed({ ...revealed, [v.id]: r.document_number }); } catch (e) { toast(errorMessage(e), "bad"); } }} title="Reveal is audit-logged">Reveal</Button>
      {v.status === "pending" && <>
        <Button size="sm" onClick={async () => { const notes = await askReason("Approval notes (e.g. NIN matched on NIMC):"); if (!notes) return; try { await http.post(`/admin/verifications/${v.id}/decide`, { approve: true, notes }); toast("Approved"); reload(); } catch (e) { toast(errorMessage(e), "bad"); } }}>Approve</Button>
        <Button size="sm" variant="danger" onClick={async () => { const notes = await askReason("Reason for rejection (shown to seller):"); if (!notes) return; try { await http.post(`/admin/verifications/${v.id}/decide`, { approve: false, notes }); reload(); } catch (e) { toast(errorMessage(e), "bad"); } }}>Reject</Button>
      </>}
    </>)} />
    <p className="mt-3 text-xs text-muted">Document images are stored in private storage. Document number reveals are recorded in the audit log.</p></>
  );
}
