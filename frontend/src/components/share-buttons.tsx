"use client";

import { Link2 } from "lucide-react";
import { siFacebook, siTelegram, siWhatsapp, siX, type SimpleIcon } from "simple-icons";
import { useToast } from "./ui";

export function ShareButtons({ url, title }: { url: string; title: string }) {
  const toast = useToast();
  const u = encodeURIComponent(url);
  const t = encodeURIComponent(title);
  const links: { label: string; href: string; icon: SimpleIcon }[] = [
    { label: "Facebook", href: `https://www.facebook.com/sharer/sharer.php?u=${u}`, icon: siFacebook },
    { label: "X", href: `https://twitter.com/intent/tweet?url=${u}&text=${t}`, icon: siX },
    { label: "Telegram", href: `https://t.me/share/url?url=${u}&text=${t}`, icon: siTelegram },
    { label: "WhatsApp", href: `https://wa.me/?text=${t}%20${u}`, icon: siWhatsapp },
  ];
  async function copy() {
    try {
      await navigator.clipboard.writeText(url);
      toast("Link copied", "info");
    } catch {
      toast("Could not copy the link", "bad");
    }
  }
  return (
    <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-line pt-4">
      <span className="mr-1 text-xs font-medium text-muted">Share:</span>
      {links.map((l) => (
        <a key={l.label} href={l.href} target="_blank" rel="noreferrer" aria-label={`Share on ${l.label}`}
          style={{ backgroundColor: `#${l.icon.hex}` }}
          className="grid size-8 place-items-center rounded text-white transition hover:opacity-90">
          <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden><path d={l.icon.path} /></svg>
        </a>
      ))}
      <button type="button" onClick={copy} aria-label="Copy link"
        className="grid size-8 place-items-center rounded bg-canvas text-ink/70 transition hover:bg-brand-50 hover:text-brand-700">
        <Link2 className="size-4" />
      </button>
    </div>
  );
}
