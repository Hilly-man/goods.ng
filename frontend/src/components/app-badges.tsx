/**
 * Mobile app placeholders for the footer. Deliberately NOT the official store badges and not links:
 * Apple's and Google's badge artwork is only for apps that are actually available to download.
 */

function AppleLogo() {
  return (
    <svg viewBox="0 0 24 24" className="size-5 shrink-0 fill-white" aria-hidden>
      <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
    </svg>
  );
}

function PlayLogo() {
  return (
    <svg viewBox="0 0 24 24" className="size-5 shrink-0" aria-hidden>
      <path d="M3.6 1.8 13.4 11.9 3.6 22.1C3.2 21.9 3 21.5 3 21V3c0-.5.2-.9.6-1.2Z" fill="#00a0ff" />
      <path d="M3.6 1.8 13.4 11.9l3.2-3.2L5.2 2.1c-.6-.4-1.2-.5-1.6-.3Z" fill="#00d26a" />
      <path d="M3.6 22.1 13.4 11.9l3.2 3.2-11.4 6.6c-.6.4-1.2.6-1.6.4Z" fill="#ff3a44" />
      <path d="m16.6 8.7 3.7 2.1c1.1.6 1.1 1.7 0 2.3l-3.7 2-3.2-3.2Z" fill="#ffd500" />
    </svg>
  );
}

function Badge({ logo, platform, store }: { logo: React.ReactNode; platform: string; store: string }) {
  return (
    <li
      aria-label={`${platform} app — coming soon to ${store}`}
      className="relative flex h-11 cursor-default items-center gap-2 rounded-lg bg-black/60 pl-2.5 pr-3 ring-1 ring-white/20"
    >
      {logo}
      <span className="leading-tight">
        <span className="block text-[9px] uppercase tracking-wider text-white/60">Coming soon</span>
        <span className="block whitespace-nowrap text-[13px] font-semibold text-white">{store}</span>
      </span>
      <span className="absolute -right-2 -top-2 rounded-full bg-accent-500 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide text-brand-950 shadow">Soon</span>
    </li>
  );
}

/** `compact`: just the two buttons (phone footer). */
export function AppBadges({ compact = false }: { compact?: boolean }) {
  return (
    <div>
      {!compact && <h3 className="mb-3 text-sm font-semibold text-white">Get the app</h3>}
      <ul className="flex flex-wrap gap-2.5" aria-label="Goods.ng mobile apps — coming soon">
        <Badge logo={<AppleLogo />} platform="iOS" store="App Store" />
        <Badge logo={<PlayLogo />} platform="Android" store="Google Play" />
      </ul>
      {!compact && <p className="mt-2 text-xs text-white/60">Our iPhone and Android apps are coming soon.</p>}
    </div>
  );
}
