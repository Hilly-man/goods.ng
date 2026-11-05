"use client";

import Link from "next/link";
import { Bell } from "lucide-react";
import clsx from "clsx";
import { RequireAuth } from "@/components/require-auth";
import { Button, EmptyState, PageLoader } from "@/components/ui";
import { http } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { timeAgo } from "@/lib/format";
import type { Notification } from "@/lib/types";

function List() {
  const { data, setData } = useApi<Notification[]>("/notifications", { limit: 100 });
  if (!data) return <PageLoader />;
  if (!data.length) return <div className="card"><EmptyState icon={<Bell />} title="You're all caught up" /></div>;
  const read = (id: string) => http.post(`/notifications/${id}/read`).catch(() => {});
  return (
    <>
      <div className="mb-3 flex justify-end"><Button size="sm" variant="ghost" onClick={async () => { await http.post("/notifications/read-all"); setData(data.map((n) => ({ ...n, read_at: n.read_at ?? new Date().toISOString() }))); }}>Mark all as read</Button></div>
      <ul className="card divide-y divide-line">
        {data.map((n) => {
          const body = (
            <div className={clsx("flex gap-3 p-4", !n.read_at && "bg-brand-50/60")}>
              <span className={clsx("mt-1.5 size-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : "bg-brand-600")} />
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{n.title}</p>
                <p className="text-sm text-ink/80">{n.body}</p>
                <p className="mt-1 text-xs text-muted">{timeAgo(n.created_at)}</p>
              </div>
            </div>
          );
          return <li key={n.id}>{n.link ? <Link href={n.link} onClick={() => read(n.id)} className="block hover:bg-canvas">{body}</Link> : body}</li>;
        })}
      </ul>
    </>
  );
}

export default function Page() {
  return <RequireAuth>{() => <div className="container-page max-w-3xl py-6"><h1 className="mb-2 text-2xl font-bold">Notifications</h1><List /></div>}</RequireAuth>;
}
