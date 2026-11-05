"use client";

import { useState } from "react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { Badge, Button, Input, PageLoader, Select, useToast } from "@/components/ui";
import { CategoryIcon } from "@/components/icons";
import { http, errorMessage } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import type { Category } from "@/lib/types";

export default function Page() {
  const { data, reload } = useApi<Category[]>("/categories/admin/all");
  const toast = useToast();
  const [name, setName] = useState("");
  const [parent, setParent] = useState("");
  if (!data) return <PageLoader />;
  const save = async (c: Category, patch: Partial<Category>) => {
    try {
      await http.patch(`/categories/admin/${c.id}`, { name: c.name, parent_id: c.parent_id, icon: c.icon, description: c.description, sort_order: c.sort_order, is_active: c.is_active, ...patch });
      reload();
    } catch (e) { toast(errorMessage(e), "bad"); }
  };
  const move = async (list: Category[], i: number, d: number) => {
    const ids = list.map((c) => c.id);
    const j = i + d; if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    try { await http.post("/categories/admin/reorder", { ids }); reload(); } catch (e) { toast(errorMessage(e), "bad"); }
  };
  const Row = ({ c, list, i, depth }: { c: Category; list: Category[]; i: number; depth: number }) => (
    <li className="flex items-center gap-2 border-b border-line/60 py-2" style={{ paddingLeft: depth * 24 }}>
      {depth === 0 && <CategoryIcon name={c.icon} className="size-4 text-brand-700" />}
      <span className="flex-1 text-sm font-medium">{c.name} <span className="text-xs text-muted">({c.listing_count})</span></span>
      {!c.is_active && <Badge tone="bad">Inactive</Badge>}
      <button aria-label="Move up" className="p-1 text-muted hover:text-ink" onClick={() => move(list, i, -1)}><ArrowUp className="size-4" /></button>
      <button aria-label="Move down" className="p-1 text-muted hover:text-ink" onClick={() => move(list, i, 1)}><ArrowDown className="size-4" /></button>
      <Button size="sm" variant="ghost" onClick={() => { const n = prompt("Rename category", c.name); if (n) save(c, { name: n }); }}>Rename</Button>
      <Button size="sm" variant="outline" onClick={() => save(c, { is_active: !c.is_active })}>{c.is_active ? "Deactivate" : "Activate"}</Button>
    </li>
  );
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Categories</h1>
      <form className="card flex flex-wrap items-end gap-2 p-4" onSubmit={async (e) => {
        e.preventDefault();
        try { await http.post("/categories/admin", { name, parent_id: parent || null }); setName(""); toast("Category created"); reload(); } catch (err) { toast(errorMessage(err), "bad"); }
      }}>
        <div className="flex-1"><Input label="New category" value={name} onChange={(e) => setName(e.target.value)} required /></div>
        <div className="w-56"><Select label="Parent" value={parent} onChange={(e) => setParent(e.target.value)}><option value="">Top level</option>{data.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</Select></div>
        <Button type="submit">Add</Button>
      </form>
      <ul className="card px-4">
        {data.map((c, i) => (
          <div key={c.id}><Row c={c} list={data} i={i} depth={0} />{c.children.map((ch, j) => <Row key={ch.id} c={ch} list={c.children} i={j} depth={1} />)}</div>
        ))}
      </ul>
    </div>
  );
}
