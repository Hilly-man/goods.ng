/**
 * Footer skyline: one flat silhouette of African landmarks sitting on the footer (original artwork).
 * Left → right: Pyramids of Giza (Egypt), Great Mosque of Djenné (Mali), National Theatre (Lagos),
 * Lekki–Ikoyi Link Bridge (Lagos), Lagos Marina high-rises incl. NECOM House, KICC (Nairobi),
 * Independence Arch (Accra), baobab.
 * "Cut-outs" (windows, columns) use the page background colour so it still reads as a single silhouette.
 */

const INK = "var(--color-brand-950)";
const BG = "var(--color-canvas)";

function star(cx: number, cy: number, outer: number, inner: number) {
  return Array.from({ length: 10 }, (_, i) => {
    const r = i % 2 === 0 ? outer : inner;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}

// Lekki–Ikoyi Link Bridge geometry: gently arched deck, single tapered pylon, fan of stay cables.
const B = { x0: 536, x1: 764, px: 650, deckY: 202, rise: 9, top: 40 };
const deckY = (x: number) => {
  const t = (x - B.px) / ((B.x1 - B.x0) / 2);
  return B.deckY - B.rise * (1 - t * t);
};

function Landmarks() {
  const deckPath = Array.from({ length: 41 }, (_, i) => {
    const x = B.x0 + ((B.x1 - B.x0) * i) / 40;
    return `${i ? "L" : "M"}${x.toFixed(1)} ${deckY(x).toFixed(1)}`;
  }).join(" ");
  const deckUnder = Array.from({ length: 41 }, (_, i) => {
    const x = B.x1 - ((B.x1 - B.x0) * i) / 40;
    return `L${x.toFixed(1)} ${(deckY(x) + 5).toFixed(1)}`;
  }).join(" ");

  return (
    <>
        {/* ---------- Pyramids of Giza ---------- */}
        <path d="M10 220 L62 166 L114 220Z" />
        <path d="M66 220 L146 136 L226 220Z" />

        {/* ---------- Great Mosque of Djenné ---------- */}
        <path d="M240 220 V182 H352 V220Z" />
        {Array.from({ length: 11 }).map((_, i) => <path key={i} d={`M${242 + i * 10} 183 l3 -8 l3 8Z`} />)}
        {[[248, 150], [284, 130], [320, 150]].map(([x, top]) => (
          <g key={x}>
            <path d={`M${x} 184 V${top + 12} Q${x + 12} ${top - 8} ${x + 24} ${top + 12} V184Z`} />
            <rect x={x + 10} y={top - 9} width="4" height="10" />
            {[0, 1, 2].map((k) => <rect key={k} x={x - 3} y={top + 20 + k * 10} width="30" height="2" />)}
          </g>
        ))}

        {/* ---------- National Theatre, Lagos (military-cap profile) ---------- */}
        {/* drum base with columns */}
        <path d="M384 220 L388 194 H500 L504 220Z" />
        {/* wide flared brim */}
        <path d="M364 198 Q444 178 524 198 L520 205 Q444 187 368 205Z" />
        {/* domed crown */}
        <path d="M390 192 C396 164 422 152 444 151 C466 152 492 164 498 192 Q444 182 390 192Z" />
        <path d="M428 154 Q444 145 460 154Z" />
        <g fill={BG}>
          {Array.from({ length: 13 }).map((_, i) => <rect key={i} x={394 + i * 8.4} y="208" width="3" height="12" />)}
          <path d="M404 180 Q444 168 484 180 L484 182 Q444 171 404 182Z" />
        </g>

        {/* ---------- Lekki–Ikoyi Link Bridge ---------- */}
        <path d={`${deckPath} ${deckUnder} Z`} />
        {[556, 590, 620, 680, 712, 744].map((x) => <rect key={x} x={x - 2} y={deckY(x) + 4} width="4" height={220 - deckY(x) - 4} />)}
        {/* tapered pylon with pointed tip */}
        <path d={`M${B.px - 6} ${B.deckY} L${B.px - 2.5} ${B.top + 12} L${B.px} ${B.top} L${B.px + 2.5} ${B.top + 12} L${B.px + 6} ${B.deckY}Z`} />
        <g stroke={INK} strokeWidth="0.9" fill="none">
          {Array.from({ length: 11 }).map((_, i) => {
            const y = B.top + 18 + i * 7;
            const left = B.x0 + 10 + i * 9.5;
            const right = B.x1 - 10 - i * 9.5;
            return (
              <g key={i}>
                <line x1={B.px - 1.5} y1={y} x2={left} y2={deckY(left)} />
                <line x1={B.px + 1.5} y1={y} x2={right} y2={deckY(right)} />
              </g>
            );
          })}
        </g>

        {/* ---------- Lagos Marina high-rises ---------- */}
        {/* stepped-top office tower */}
        <path d="M780 220 V136 H786 V128 H800 V136 H806 V220Z" />
        {/* NECOM House with telecom mast */}
        <rect x="810" y="72" width="24" height="148" />
        <rect x="814" y="64" width="16" height="8" />
        <rect x="821" y="28" width="2" height="36" />
        <rect x="816" y="44" width="12" height="2" />
        <rect x="818" y="36" width="8" height="2" />
        {/* angled-crown tower */}
        <path d="M838 220 V108 L866 94 V220Z" />
        {/* curved glass tower */}
        <path d="M870 220 V132 Q882 112 894 132 V220Z" />
        {/* spire tower */}
        <path d="M898 220 V100 H904 V92 H918 V100 H924 V220Z" />
        <rect x="910" y="70" width="2" height="22" />
        {/* low block */}
        <rect x="928" y="168" width="20" height="52" />
        <g fill={BG}>
          {Array.from({ length: 12 }).map((_, r) => (
            <g key={r}>
              {r < 7 && <rect x="784" y={144 + r * 10} width="18" height="2" />}
              <rect x="814" y={80 + r * 11} width="16" height="2" />
              {r < 10 && <rect x="842" y={116 + r * 10} width="20" height="2" />}
              {r < 7 && <rect x="874" y={140 + r * 11} width="16" height="2" />}
              {r < 10 && <rect x="902" y={108 + r * 11} width="18" height="2" />}
            </g>
          ))}
        </g>

        {/* ---------- KICC, Nairobi ---------- */}
        <path d="M956 220 L966 196 H998 L1008 220Z" />
        <rect x="1010" y="104" width="20" height="116" />
        <rect x="1006" y="100" width="28" height="5" />
        <ellipse cx="1020" cy="94" rx="22" ry="4" />
        <rect x="1019" y="82" width="2" height="10" />

        {/* ---------- Independence Arch, Accra ---------- */}
        <path d="M1046 220 V162 H1132 V220 H1118 V186 Q1089 168 1060 186 V220Z" />
        <rect x="1042" y="157" width="94" height="6" />
        <polygon points={star(1089, 142, 11, 4.6)} />

        {/* ---------- Baobab ---------- */}
        <path d="M1154 220 C1157 198 1155 180 1150 168 C1160 172 1176 172 1186 168 C1181 180 1179 198 1182 220Z" />
        <path d="M1153 170 C1146 160 1142 150 1140 140 M1162 169 C1162 156 1164 146 1168 134 M1174 169 C1176 158 1178 150 1184 142 M1183 170 C1188 164 1192 158 1194 150"
          stroke={INK} strokeWidth="4.5" strokeLinecap="round" fill="none" />
        <ellipse cx="1140" cy="137" rx="9" ry="4.5" />
        <ellipse cx="1168" cy="131" rx="9" ry="4.5" />
        <ellipse cx="1184" cy="139" rx="7" ry="4" />
        <ellipse cx="1194" cy="147" rx="5" ry="3.5" />

    </>
  );
}

/**
 * Full-width footer panorama: sun, Zuma Rock and savannah hills behind; the landmark silhouettes in
 * front, framed by palms and thatched huts; then a kente-inspired band into the footer.
 */
export function AfricaSkyline() {
  return (
    <div aria-hidden className="relative mt-16 select-none">
      <svg viewBox="0 0 1440 240" preserveAspectRatio="xMidYMax slice" className="block h-32 w-full sm:h-44 lg:h-56" fill={INK}>
        <defs>
          <linearGradient id="sky-sun" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#fbbf24" stopOpacity="0.55" />
            <stop offset="1" stopColor="#f59e0b" stopOpacity="0.15" />
          </linearGradient>
          <linearGradient id="sky-hills" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#10b86b" stopOpacity="0.28" />
            <stop offset="1" stopColor="#057a48" stopOpacity="0.45" />
          </linearGradient>
        </defs>

        {/* ---------- background ---------- */}
        <circle cx="742" cy="96" r="46" fill="url(#sky-sun)" />
        {/* Zuma Rock */}
        <path d="M612 240 C626 150 662 94 730 86 C792 80 840 134 864 240Z" fill="url(#sky-hills)" />
        <path d="M674 134 C684 162 688 198 682 236 M730 100 C738 142 738 192 732 236 M788 114 C796 152 802 198 800 236"
          stroke="#057a48" strokeOpacity="0.25" strokeWidth="3" fill="none" />
        {/* savannah hills */}
        <path d="M0 240 V196 C90 168 160 182 230 200 C330 224 420 176 540 186 C680 198 760 160 880 172 C1010 186 1100 150 1220 164 C1320 176 1390 168 1440 160 V240Z"
          fill="url(#sky-hills)" />

        {/* ---------- foreground ---------- */}
        <rect x="0" y="226" width="1440" height="14" />

        {/* palm (far left) */}
        <path d="M30 228 C28 198 32 172 42 146 L47 148 C39 174 36 200 38 228Z" />
        <path d="M44 146 C30 134 14 134 2 144 C18 136 32 140 44 149Z M44 146 C42 128 32 116 18 112 C34 120 42 132 43 149Z M44 146 C56 130 72 124 86 128 C72 130 60 138 46 150Z M44 146 C60 142 74 150 80 164 C70 152 58 148 46 150Z" />

        {/* landmarks, scaled to sit on the ground line */}
        <g transform="translate(72 -11.6) scale(1.08)">
          <Landmarks />
        </g>

        {/* thatched huts (far right) */}
        <rect x="1374" y="200" width="30" height="28" />
        <path d="M1366 204 L1389 174 L1412 204Z" />
        <rect x="1414" y="210" width="22" height="18" />
        <path d="M1408 213 L1426 192 L1444 213Z" />
        <path d="M1384 228 V214 Q1389 207 1394 214 V228Z" fill={BG} opacity="0.25" />
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
