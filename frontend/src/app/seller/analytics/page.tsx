"use client";

import Link from "next/link";
import { useState } from "react";
import { Lock } from "lucide-react";
import { RequireAuth } from "@/components/require-auth";
import { PageLoader, Stat, Tabs } from "@/components/ui";
import { useApi } from "@/lib/hooks";

type A = {
  premium: boolean; days: number; locked?: string[];
  views_by_day: { date: string; views: number }[];
  contacts_by_channel?: Record<string, number>;
  top_products?: { id: string; title: string; slug: string; views: number; contact_clicks: number; enquiries: number; favourites: number }[];
  conversion?: { views: number; contacts: number; rate: number };
};

function Bars({ data }: { data: { date: string; views: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.views));
  if (!data.length) return <p className="py-10 text-center text-sm text-muted">No views in this period yet.</p>;
  return (
    <div className="flex h-44 items-end gap-1" role="img" aria-label="Views per day">
      {data.map((d) => (
        <div key={d.date} className="group relative flex-1">
          <div className="rounded-t bg-brand-600 transition group-hover:bg-brand-800" style={{ height: `${(d.views / max) * 160 + 2}px` }} />
          <span className="pointer-events-none absolute -top-7 left-1/2 hidden -translate-x-1/2 whitespace-nowrap rounded bg-ink px-1.5 py-0.5 text-[10px] text-white group-hover:block">{d.date}: {d.views}</span>
        </div>
      ))}
    </div>
  );
}

function View() {
  const [days, setDays] = useState("30");
  const { data } = useApi<A>("/sellers/me/analytics", { days });
  if (!data) return <PageLoader />;
  return (
    <div className="space-y-4">
      <Tabs value={days} onChange={setDays} tabs={[{ value: "7", label: "7 days" }, { value: "30", label: "30 days" }, { value: "90", label: "90 days" }]} />
      <div className="card p-4"><h2 className="mb-3 font-semibold">Product views</h2><Bars data={data.views_by_day} /></div>
      {data.premium && data.conversion ? (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Views" value={data.conversion.views} />
            <Stat label="Direct contacts" value={data.conversion.contacts} />
            <Stat label="Contact rate" value={`${data.conversion.rate}%`} />
            <Stat label="WhatsApp / Calls" value={`${data.contacts_by_channel?.whatsapp ?? 0} / ${data.contacts_by_channel?.phone ?? 0}`} />
          </div>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-line text-left text-muted"><th className="p-3">Top listings</th><th className="p-3">Views</th><th className="p-3">Enquiries</th><th className="p-3">Contacts</th><th className="p-3">Saves</th></tr></thead>
              <tbody>{data.top_products?.map((p) => <tr key={p.id} className="border-b border-line/60"><td className="max-w-xs truncate p-3"><Link href={`/item/${p.slug}`} className="hover:text-brand-700">{p.title}</Link></td><td className="p-3">{p.views}</td><td className="p-3">{p.enquiries}</td><td className="p-3">{p.contact_clicks}</td><td className="p-3">{p.favourites}</td></tr>)}</tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="card flex flex-col items-center gap-2 p-8 text-center">
          <Lock className="size-8 text-premium-500" />
          <p className="font-semibold">Advanced analytics are a Premium feature</p>
          <p className="text-sm text-muted">See contact clicks by channel, conversion rates and your best-performing listings.</p>
          <Link href="/premium" className="mt-2 font-semibold text-brand-700">Upgrade to Premium →</Link>
        </div>
      )}
    </div>
  );
}

export default function Page() {
  return <RequireAuth seller>{() => <><h1 className="mb-4 text-2xl font-bold">Sales analytics</h1><View /></>}</RequireAuth>;
}
