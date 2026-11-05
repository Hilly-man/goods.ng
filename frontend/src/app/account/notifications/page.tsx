"use client";

import { useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { Button, PageLoader, useToast } from "@/components/ui";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { titleCase } from "@/lib/format";

type Pref = { event_type: string; in_app: boolean; email: boolean; sms: boolean };

function Prefs() {
  const { data, setData } = useApi<Pref[]>("/users/me/notification-preferences");
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  if (!data) return <PageLoader />;
  const toggle = (i: number, k: "in_app" | "email" | "sms") => setData(data.map((p, j) => (j === i ? { ...p, [k]: !p[k] } : p)));
  return (
    <div className="card overflow-x-auto">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-line text-left text-muted"><th className="p-3">Event</th><th className="p-3">In-app</th><th className="p-3">Email</th><th className="p-3">SMS</th></tr></thead>
        <tbody>
          {data.map((p, i) => (
            <tr key={p.event_type} className="border-b border-line/60">
              <td className="p-3">{titleCase(p.event_type)}</td>
              {(["in_app", "email", "sms"] as const).map((k) => (
                <td key={k} className="p-3"><input type="checkbox" className="size-4 accent-brand-700" checked={p[k]} onChange={() => toggle(i, k)} aria-label={`${titleCase(p.event_type)} ${k}`} /></td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="p-3"><Button loading={busy} onClick={async () => {
        setBusy(true);
        try { setData(await http.put<Pref[]>("/users/me/notification-preferences", data)); toast("Preferences saved"); }
        catch (e) { toast(errorMessage(e), "bad"); } finally { setBusy(false); }
      }}>Save preferences</Button></div>
    </div>
  );
}

export default function Page() {
  return <RequireAuth>{() => <div className="container-page max-w-3xl py-6"><h1 className="mb-4 text-2xl font-bold">Notification settings</h1><Prefs /></div>}</RequireAuth>;
}
