"use client";

import Link from "next/link";
import { MessageCircle } from "lucide-react";
import clsx from "clsx";
import { useState } from "react";
import { RequireAuth } from "@/components/require-auth";
import { EmptyState, PageLoader, Tabs } from "@/components/ui";
import { useApi, usePolling } from "@/lib/hooks";
import { naira, timeAgo } from "@/lib/format";

type Conv = {
  id: string; role: "buyer" | "seller"; unread: number; last_message_at: string; last_message_preview: string;
  other_party: { name: string; avatar_url: string | null };
  product: { title: string; price: string; thumb_url: string | null } | null;
};

function Inbox() {
  const [role, setRole] = useState<"" | "buyer" | "seller">("");
  const { data, reload } = useApi<Conv[]>("/conversations", { role: role || undefined });
  usePolling(reload, 15000);
  return (
    <>
      <Tabs value={role} onChange={setRole} tabs={[{ value: "", label: "All" }, { value: "buyer", label: "Buying" }, { value: "seller", label: "Selling" }]} />
      {!data ? <PageLoader /> : !data.length ? (
        <EmptyState icon={<MessageCircle />} title="No conversations yet" body="Chat with a seller from any listing page." />
      ) : (
        <ul className="divide-y divide-line">
          {data.map((c) => (
            <li key={c.id}>
              <Link href={`/messages/${c.id}`} className={clsx("flex gap-3 p-3 hover:bg-canvas", c.unread > 0 && "bg-brand-50/50")}>
                <span className="size-14 shrink-0 overflow-hidden rounded-lg bg-canvas">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  {c.product?.thumb_url && <img src={c.product.thumb_url} alt="" className="size-full object-cover" />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex justify-between gap-2"><span className={clsx("truncate", c.unread ? "font-bold" : "font-semibold")}>{c.other_party.name}</span><span className="shrink-0 text-xs text-muted">{timeAgo(c.last_message_at)}</span></span>
                  {c.product && <span className="block truncate text-xs text-brand-700">{c.product.title} · {naira(c.product.price)}</span>}
                  <span className="flex justify-between gap-2"><span className="truncate text-sm text-muted">{c.last_message_preview}</span>{c.unread > 0 && <span className="grid min-w-5 place-items-center rounded-full bg-brand-700 px-1.5 text-xs font-bold text-white">{c.unread}</span>}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export default function Page() {
  return <RequireAuth>{() => <div className="container-page max-w-3xl py-6"><h1 className="mb-3 text-2xl font-bold">Messages</h1><div className="card overflow-hidden"><Inbox /></div></div>}</RequireAuth>;
}
