"use client";

import Link from "next/link";
import { useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Alert, Badge, Button, Input, PageLoader, Select, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { date, titleCase, VERIFICATION_LABEL } from "@/lib/format";
import type { User, VerificationLevel } from "@/lib/types";

type V = { current_level: VerificationLevel; requests: { id: string; level_requested: string; document_type: string; document_number: string; status: string; review_notes: string | null; created_at: string }[] };

function View({ user }: { user: User }) {
  const { data, reload } = useApi<V>("/sellers/me/verification");
  const toast = useToast();
  const [level, setLevel] = useState("identity_verified");
  const [doc, setDoc] = useState("nin");
  const [num, setNum] = useState("");
  const [biz, setBiz] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  if (!data) return <PageLoader />;
  const pending = data.requests.some((r) => r.status === "pending");
  return (
    <div className="space-y-4">
      <div className="card p-5"><p className="text-sm text-muted">Current level</p><p className="text-xl font-bold">{VERIFICATION_LABEL[data.current_level]}</p></div>
      {!user.phone_verified ? (
        <Alert tone="warn" title="Verify your phone first">Phone verification is required before submitting documents. <Link href="/account" className="underline">Verify now</Link></Alert>
      ) : pending ? (
        <Alert tone="info" title="Under review">Your documents are being reviewed. This usually takes 1–2 working days.</Alert>
      ) : (
        <form className="card space-y-4 p-5" onSubmit={async (e) => {
          e.preventDefault(); if (!file) return toast("Attach a clear photo of the document", "bad");
          setBusy(true);
          const fd = new FormData();
          fd.append("level", level); fd.append("document_type", level === "business_verified" ? "cac" : doc); fd.append("document_number", num); if (biz) fd.append("business_name", biz); fd.append("file", file);
          try { await http.post("/sellers/me/verification", fd); toast("Submitted for review"); setNum(""); setFile(null); reload(); }
          catch (err) { toast(errorMessage(err), "bad"); } finally { setBusy(false); }
        }}>
          <h2 className="font-semibold">Request verification</h2>
          <Select label="Level" value={level} onChange={(e) => setLevel(e.target.value)}><option value="identity_verified">Identity verified (individual)</option><option value="business_verified">Business verified (CAC)</option></Select>
          {level === "identity_verified" && <Select label="Document" value={doc} onChange={(e) => setDoc(e.target.value)}>{[["nin", "NIN slip / card"], ["intl_passport", "International passport"], ["drivers_licence", "Driver's licence"], ["voters_card", "Voter's card"]].map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>}
          {level === "business_verified" && <Input label="Registered business name" value={biz} onChange={(e) => setBiz(e.target.value)} />}
          <Input label={level === "business_verified" ? "RC / BN number" : "Document number"} required value={num} onChange={(e) => setNum(e.target.value)} hint="Encrypted and only visible to authorised verification staff." />
          <label className="block"><span className="label">Photo of document</span><input type="file" accept="image/jpeg,image/png,image/webp" required onChange={(e) => setFile(e.target.files?.[0] ?? null)} className="text-sm" /></label>
          <Button type="submit" loading={busy}>Submit for review</Button>
        </form>
      )}
      {data.requests.length > 0 && (
        <ul className="card divide-y divide-line">
          {data.requests.map((r) => (
            <li key={r.id} className="flex items-center justify-between p-3 text-sm">
              <span>{titleCase(r.level_requested)} · {titleCase(r.document_type)} {r.document_number}<span className="block text-xs text-muted">{date(r.created_at)}{r.review_notes && ` · ${r.review_notes}`}</span></span>
              <Badge tone={r.status === "approved" ? "good" : r.status === "rejected" ? "bad" : "warn"} className="capitalize">{r.status}</Badge>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{(u) => <><h1 className="mb-4 text-2xl font-bold">Verification</h1><View user={u} /></>}</RequireAuth>;
}
