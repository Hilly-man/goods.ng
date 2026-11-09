/**
 * Footer panorama: a flat silhouette of the savannah hills sitting on the footer (original artwork).
 * All foreground scenery (sun, palms, baobab, huts) and buildings are omitted, leaving only the
 * rolling background hills.
 */

const INK = "var(--color-brand-950)";

/**
 * Full-width footer panorama: rolling savannah hills, then a kente-inspired band into the footer.
 */
export function AfricaSkyline({ className = "mt-16" }: { className?: string }) {
  return (
    <div aria-hidden className={`relative select-none ${className}`}>
      <svg viewBox="0 0 1440 240" preserveAspectRatio="xMidYMax slice" className="block h-32 w-full sm:h-44 lg:h-56" fill={INK}>
        <defs>
          <linearGradient id="sky-hills" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="var(--color-brand-500)" stopOpacity="0.28" />
            <stop offset="1" stopColor="var(--color-brand-700)" stopOpacity="0.45" />
          </linearGradient>
        </defs>

        {/* ---------- background mountains ---------- */}
        {/* savannah hills */}
        <path d="M0 240 V196 C90 168 160 182 230 200 C330 224 420 176 540 186 C680 198 760 160 880 172 C1010 186 1100 150 1220 164 C1320 176 1390 168 1440 160 V240Z"
          fill="url(#sky-hills)" />
      </svg>
      {/* kente-inspired pattern band */}
      <div
        className="h-3 w-full"
        style={{
          backgroundColor: "var(--color-brand-950)",
          backgroundImage:
            "linear-gradient(135deg, var(--color-accent-500) 25%, transparent 25%), linear-gradient(225deg, var(--color-accent-500) 25%, transparent 25%), linear-gradient(315deg, var(--color-brand-500) 25%, transparent 25%), linear-gradient(45deg, var(--color-brand-500) 25%, transparent 25%)",
          backgroundSize: "24px 12px",
          backgroundPosition: "0 0, 0 0, 12px 0, 12px 0",
        }}
      />
    </div>
  );
}

/** Faint Adire-style geometric texture for the footer background (data-URI SVG, ~400 bytes). */
export const ADIRE_TEXTURE =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' viewBox='0 0 64 64'%3E%3Cg fill='none' stroke='%23ffffff' stroke-opacity='0.035' stroke-width='1.5'%3E%3Ccircle cx='32' cy='32' r='10'/%3E%3Ccircle cx='32' cy='32' r='4'/%3E%3Cpath d='M0 0l16 16M64 0L48 16M0 64l16-16M64 64L48 48'/%3E%3Cpath d='M32 0v8M32 56v8M0 32h8M56 32h8'/%3E%3C/g%3E%3C/svg%3E\")";
