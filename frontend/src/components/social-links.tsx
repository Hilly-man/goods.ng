import { siFacebook, siInstagram, siTiktok, siWhatsapp, siX, siYoutube, type SimpleIcon } from "simple-icons";

const SOCIALS: { name: string; href: string; icon: SimpleIcon }[] = [
  { name: "Instagram", href: "https://instagram.com/goods.ng", icon: siInstagram },
  { name: "Facebook", href: "https://facebook.com/goods.ng", icon: siFacebook },
  { name: "X (Twitter)", href: "https://x.com/goodsng", icon: siX },
  { name: "TikTok", href: "https://tiktok.com/@goods.ng", icon: siTiktok },
  { name: "YouTube", href: "https://youtube.com/@goodsng", icon: siYoutube },
  { name: "WhatsApp", href: "https://wa.me/2342013300000", icon: siWhatsapp },
];

/** Round brand icons; each fills with its brand colour on hover/focus. */
export function SocialLinks() {
  return (
    <ul className="flex flex-wrap gap-2" aria-label="Goods.ng on social media">
      {SOCIALS.map((s) => (
        <li key={s.name}>
          <a
            href={s.href}
            target="_blank"
            rel="noopener noreferrer"
            aria-label={`Goods.ng on ${s.name}`}
            title={s.name}
            style={{ "--brand": `#${s.icon.hex === "000000" ? "1f2937" : s.icon.hex}` } as React.CSSProperties}
            className="grid size-9 place-items-center rounded-full bg-white/10 text-white transition hover:scale-105 hover:bg-[var(--brand)] focus-visible:bg-[var(--brand)]"
          >
            <svg viewBox="0 0 24 24" className="size-4" fill="currentColor" aria-hidden>
              <path d={s.icon.path} />
            </svg>
          </a>
        </li>
      ))}
    </ul>
  );
}
