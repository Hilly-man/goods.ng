/**
 * Flat, brand-coloured spot illustrations (inline SVG — no network requests, crisp at any size).
 * Colours come from the Tailwind theme tokens so they follow any palette change.
 */

const B50 = "var(--color-brand-50)";
const B100 = "var(--color-brand-100)";
const B200 = "var(--color-brand-200)";
const B400 = "var(--color-brand-400)";
const B600 = "var(--color-brand-600)";
const B700 = "var(--color-brand-700)";
const B900 = "var(--color-brand-900)";
const A400 = "var(--color-accent-400)";
const A500 = "var(--color-accent-500)";
const INK = "#1f2937";
const W = "#ffffff";

type P = { className?: string; title?: string };

function Frame({ className, title, children }: P & { children: React.ReactNode }) {
  return (
    <svg viewBox="0 0 320 240" className={className} role={title ? "img" : undefined} aria-hidden={title ? undefined : true}>
      {title && <title>{title}</title>}
      {children}
    </svg>
  );
}

function Sparkle({ x, y, s = 1, c = A400 }: { x: number; y: number; s?: number; c?: string }) {
  return <path transform={`translate(${x} ${y}) scale(${s})`} d="M0-8 2-2 8 0 2 2 0 8-2 2-8 0-2-2z" fill={c} />;
}

function ShieldCheck({ x, y, s = 1 }: { x: number; y: number; s?: number }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M0-26 22-18v16C22 13 12 23 0 28-12 23-22 13-22-2v-16z" fill={B600} />
      <path d="M0-26 22-18v16C22 13 12 23 0 28z" fill={B700} />
      <path d="m-9 1 6 6 12-13" fill="none" stroke={W} strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
    </g>
  );
}

function Bag({ x, y, s = 1, c = A500 }: { x: number; y: number; s?: number; c?: string }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M-10-14a10 10 0 0 1 20 0" fill="none" stroke={INK} strokeWidth="3" strokeLinecap="round" />
      <rect x="-20" y="-14" width="40" height="38" rx="6" fill={c} />
      <rect x="-20" y="-14" width="40" height="8" rx="4" fill={A400} />
      <circle cx="-9" cy="-4" r="2.5" fill={INK} /><circle cx="9" cy="-4" r="2.5" fill={INK} />
    </g>
  );
}

function Naira({ x, y, r = 14 }: { x: number; y: number; r?: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <circle r={r} fill={A500} />
      <circle r={r - 3} fill={A400} />
      <text y={r * 0.38} textAnchor="middle" fontSize={r * 1.1} fontWeight="800" fill="#92400e" fontFamily="system-ui, sans-serif">₦</text>
    </g>
  );
}

/** A storefront and a phone showing a protected listing — "an online marketplace". */
export function MarketplaceIllustration(p: P) {
  return (
    <Frame {...p}>
      <ellipse cx="160" cy="214" rx="138" ry="12" fill={B100} />
      <path d="M38 120C30 60 90 18 160 22s128 44 124 100-50 92-124 92S46 180 38 120z" fill={B50} />
      {/* store */}
      <rect x="62" y="92" width="132" height="118" rx="6" fill={W} stroke={B200} strokeWidth="3" />
      <path d="M54 70h148l-6 30H60z" fill={B600} />
      {[0, 1, 2, 3, 4, 5].map((i) => (
        <path key={i} d={`M${60 + i * 23} 100h23v8a11.5 11.5 0 0 1-23 0z`} fill={i % 2 ? W : B600} stroke={B600} strokeWidth="1.5" />
      ))}
      <rect x="80" y="130" width="40" height="80" rx="4" fill={B200} />
      <circle cx="113" cy="172" r="2.5" fill={B700} />
      <rect x="134" y="130" width="46" height="36" rx="4" fill={B100} />
      <rect x="140" y="146" width="14" height="20" rx="2" fill={A400} /><rect x="158" y="140" width="16" height="26" rx="2" fill={B400} />
      <rect x="96" y="50" width="64" height="18" rx="9" fill={B900} />
      <text x="128" y="63" textAnchor="middle" fontSize="11" fontWeight="800" fill={W} fontFamily="system-ui, sans-serif">GOODS.NG</text>
      {/* phone */}
      <g transform="rotate(6 236 140)">
        <rect x="196" y="72" width="84" height="146" rx="14" fill={INK} />
        <rect x="202" y="84" width="72" height="124" rx="8" fill={W} />
        <rect x="208" y="90" width="60" height="44" rx="6" fill={B100} />
        <path d="m216 128 14-18 10 12 8-8 14 14z" fill={B400} /><circle cx="254" cy="102" r="5" fill={A400} />
        <rect x="208" y="140" width="44" height="6" rx="3" fill={INK} opacity=".7" />
        <rect x="208" y="151" width="30" height="8" rx="3" fill={B700} />
        <rect x="208" y="186" width="60" height="14" rx="5" fill={B600} />
        <rect x="222" y="191" width="32" height="4" rx="2" fill={W} />
      </g>
      <ShieldCheck x={286} y={78} s={0.9} />
      <Bag x={44} y={178} s={0.9} />
      <Sparkle x={40} y={54} /><Sparkle x={300} y={180} s={0.7} c={B400} /><Sparkle x={220} y={38} s={0.6} />
    </Frame>
  );
}

/** Phone with search + listing + "pay safely", a shield and a shopping bag — "buying". */
export function BuyerIllustration(p: P) {
  return (
    <Frame {...p}>
      <ellipse cx="160" cy="220" rx="120" ry="10" fill={B100} />
      <circle cx="160" cy="118" r="98" fill={B50} />
      <rect x="112" y="24" width="96" height="190" rx="16" fill={INK} />
      <rect x="119" y="38" width="82" height="164" rx="9" fill={W} />
      {/* search bar */}
      <rect x="126" y="46" width="68" height="16" rx="8" fill={B50} stroke={B200} />
      <circle cx="136" cy="54" r="4" fill="none" stroke={B700} strokeWidth="2" /><path d="m139 57 3 3" stroke={B700} strokeWidth="2" strokeLinecap="round" />
      <rect x="146" y="52" width="36" height="4" rx="2" fill={B200} />
      {/* listing */}
      <rect x="126" y="70" width="68" height="56" rx="6" fill={B100} />
      <rect x="148" y="80" width="24" height="40" rx="4" fill={INK} /><rect x="151" y="84" width="18" height="30" rx="2" fill={B400} />
      <rect x="126" y="132" width="50" height="6" rx="3" fill={INK} opacity=".7" />
      <rect x="126" y="143" width="34" height="9" rx="3" fill={B700} />
      {/* offer chip */}
      <rect x="126" y="158" width="40" height="12" rx="6" fill={A400} />
      <rect x="132" y="162" width="28" height="4" rx="2" fill="#92400e" />
      {/* pay button */}
      <rect x="126" y="178" width="68" height="16" rx="6" fill={B600} />
      <rect x="144" y="184" width="32" height="4" rx="2" fill={W} />
      {/* chat bubble */}
      <g>
        <path d="M44 74h56a10 10 0 0 1 10 10v20a10 10 0 0 1-10 10H66l-12 10v-10h-10a10 10 0 0 1-10-10V84a10 10 0 0 1 10-10z" fill={W} stroke={B200} strokeWidth="2" />
        <text x="72" y="99" textAnchor="middle" fontSize="11" fontWeight="800" fill={B700} fontFamily="system-ui, sans-serif">₦ Offer?</text>
      </g>
      <ShieldCheck x={248} y={150} s={1.25} />
      <Bag x={72} y={176} s={1.1} />
      <Naira x={250} y={70} r={15} />
      <Sparkle x={290} y={110} s={0.8} /><Sparkle x={36} y={140} s={0.6} c={B400} /><Sparkle x={214} y={30} s={0.6} />
    </Frame>
  );
}

/** Market stall with priced goods, a parcel ready to ship and coins — "selling". */
export function SellerIllustration(p: P) {
  return (
    <Frame {...p}>
      <ellipse cx="160" cy="218" rx="132" ry="11" fill={B100} />
      <path d="M30 128C24 66 84 26 160 24s136 40 132 100-56 90-132 90S36 186 30 128z" fill={B50} />
      {/* stall */}
      <rect x="66" y="78" width="6" height="134" fill={B900} /><rect x="210" y="78" width="6" height="134" fill={B900} />
      <path d="M52 56h178l10 34H42z" fill={A500} />
      {[0, 1, 2, 3, 4, 5, 6].map((i) => (
        <path key={i} d={`M${42 + i * 28.3} 90h28.3v6a14.15 14.15 0 0 1-28.3 0z`} fill={i % 2 ? W : A500} stroke={A500} strokeWidth="1.5" />
      ))}
      <rect x="58" y="160" width="166" height="52" rx="4" fill={B700} />
      <rect x="58" y="160" width="166" height="8" fill={B900} />
      {/* goods on the counter */}
      <rect x="78" y="124" width="22" height="36" rx="4" fill={INK} /><rect x="81" y="128" width="16" height="26" rx="2" fill={B400} />
      <rect x="108" y="132" width="40" height="28" rx="3" fill={B200} /><rect x="108" y="140" width="40" height="4" fill={B400} />
      <path d="M156 160v-22a14 14 0 0 1 28 0v22z" fill={A400} />
      <circle cx="200" cy="148" r="12" fill="#ef4444" /><path d="M200 136c2-5 6-6 9-5" stroke={B700} strokeWidth="3" fill="none" strokeLinecap="round" />
      {/* price tag */}
      <g transform="rotate(-12 120 112)">
        <path d="M100 100h38l10 12-10 12h-38z" fill={W} stroke={B600} strokeWidth="2.5" />
        <circle cx="106" cy="112" r="3" fill={B600} />
        <text x="126" y="117" textAnchor="middle" fontSize="13" fontWeight="800" fill={B700} fontFamily="system-ui, sans-serif">₦</text>
      </g>
      {/* parcel ready to ship */}
      <g transform="translate(252 166)">
        <path d="M-30-14 0-28 30-14 0 0z" fill="#d6a46a" />
        <path d="M-30-14 0 0v34l-30-14z" fill="#c08a4e" />
        <path d="M30-14 0 0v34l30-14z" fill="#a8743d" />
        <path d="m-15-21 30 14v12" stroke="#f3dcb8" strokeWidth="5" fill="none" />
      </g>
      <circle cx="282" cy="128" r="14" fill={B600} /><path d="m275 128 5 5 9-10" stroke={W} strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <Naira x={34} y={176} r={15} /><Naira x={50} y={196} r={12} />
      <Sparkle x={262} y={46} /><Sparkle x={32} y={76} s={0.7} c={B400} /><Sparkle x={300} y={96} s={0.6} />
    </Frame>
  );
}

function Chip({ x, y, rotate = 0, w, children }: { x: number; y: number; rotate?: number; w: number; children: React.ReactNode }) {
  return (
    <g transform={`translate(${x} ${y}) rotate(${rotate})`}>
      <rect x="2" y="3" width={w} height="30" rx="9" fill={B900} opacity=".08" />
      <rect width={w} height="30" rx="9" fill={W} />
      {children}
    </g>
  );
}

function Star({ x, y, s = 1 }: { x: number; y: number; s?: number }) {
  return <path transform={`translate(${x} ${y}) scale(${s})`} d="m0-6 1.8 3.8 4.2.5-3.1 2.9.8 4.1L0 3.3l-3.7 2 .8-4.1-3.1-2.9 4.2-.5z" fill={A500} />;
}

/** A parcel passing safely between two hands under a shield — protected hand-over. */
export function SafetyIllustration(p: P) {
  const SKIN = "#8a5a36";
  const SKIN_D = "#6b4226";
  const hand = (flip: boolean, sleeve: string) => (
    <g transform={flip ? "translate(320 0) scale(-1 1)" : undefined}>
      {/* sleeve + forearm rising from the bottom corner */}
      <path d="M-10 236 34 236 108 182 96 160z" fill={SKIN} />
      <path d="M-10 236 34 236 62 214 38 194z" fill={sleeve} />
      {/* palm cupping the parcel's lower corner */}
      <path d="M92 158c6-6 18-6 26-2l4 34c-8 6-22 6-30-2z" fill={SKIN} />
      {/* thumb on the front face */}
      <rect x="112" y="150" width="22" height="10" rx="5" fill={SKIN} transform="rotate(-14 112 150)" />
      {/* fingers under the base */}
      <rect x="104" y="186" width="30" height="8" rx="4" fill={SKIN_D} />
    </g>
  );
  return (
    <Frame {...p}>
      <defs><clipPath id="gng-safety-card"><rect x="8" y="8" width="304" height="224" rx="22" /></clipPath></defs>
      <rect x="8" y="8" width="304" height="224" rx="22" fill={B50} />
      <g clipPath="url(#gng-safety-card)">
        <path d="M30 150C70 100 110 86 160 112s96 6 130-50" fill="none" stroke={B200} strokeWidth="2" strokeDasharray="5 6" />
        {/* parcel */}
        <path d="M116 132h88v58h-88z" fill="#d6a46a" />
        <path d="M116 132h88l-10-16h-68z" fill="#e8c08c" />
        <rect x="153" y="116" width="14" height="74" fill="#c08a4e" opacity=".6" />
        <rect x="174" y="166" width="22" height="14" rx="2" fill={W} opacity=".85" />
        {hand(false, B700)}
        {hand(true, A500)}
      </g>
      <ShieldCheck x={160} y={64} s={1.3} />
      <Chip x={16} y={74} rotate={-10} w={116}>
        <circle cx="16" cy="15" r="7" fill={B600} /><path d="m12.5 15 2.5 2.5 4.5-5" stroke={W} strokeWidth="2" fill="none" strokeLinecap="round" />
        <text x="28" y="19.5" fontSize="11" fontWeight="700" fill={INK} fontFamily="system-ui, sans-serif">Verified seller</text>
      </Chip>
      <Chip x={206} y={34} rotate={10} w={100}>
        <text x="10" y="20" fontSize="13" fontWeight="800" fill={INK} fontFamily="system-ui, sans-serif">5.0</text>
        <Star x={41} y={15} /><Star x={52} y={15} /><Star x={63} y={15} /><Star x={74} y={15} /><Star x={85} y={15} />
      </Chip>
      <Chip x={204} y={92} rotate={6} w={100}>
        <path d="M12 9h10v6l-5 5-5-5z" fill={B600} />
        <text x="28" y="19.5" fontSize="11" fontWeight="700" fill={INK} fontFamily="system-ui, sans-serif">Payment held</text>
      </Chip>
      <Sparkle x={290} y={150} s={0.7} /><Sparkle x={34} y={140} s={0.6} c={B400} /><Sparkle x={112} y={28} s={0.5} />
    </Frame>
  );
}

/** Rising naira coin stacks with an arrow and seller badges — growing sales. */
export function GrowthIllustration(p: P) {
  const stack = (x: number, n: number) => (
    <g>
      {Array.from({ length: n }, (_, i) => (
        <g key={i} transform={`translate(${x} ${196 - i * 9})`}>
          <ellipse rx="24" ry="7" cy="5" fill="#b45309" />
          <rect x="-24" y="-2" width="48" height="7" fill={A500} />
          <ellipse rx="24" ry="7" cy="-2" fill={A400} />
        </g>
      ))}
    </g>
  );
  return (
    <Frame {...p}>
      <rect x="8" y="8" width="304" height="224" rx="22" fill={B50} />
      <rect x="60" y="200" width="200" height="22" rx="4" fill={B900} />
      <rect x="60" y="200" width="200" height="6" fill={B700} />
      {stack(100, 5)}
      {stack(154, 9)}
      {stack(210, 13)}
      <Naira x={210} y={78} r={13} />
      {/* arrow */}
      <path d="M70 176c40-10 80-40 104-76s48-50 72-56" fill="none" stroke={B600} strokeWidth="9" strokeLinecap="round" />
      <path d="m232 30 26 12-18 22z" fill={B600} />
      <Chip x={22} y={46} rotate={-8} w={92}>
        <path d="M10 20l3-10 4 6 4-6 3 10z" fill={A500} />
        <text x="30" y="19.5" fontSize="11.5" fontWeight="800" fill={INK} fontFamily="system-ui, sans-serif">Premium</text>
      </Chip>
      <Chip x={34} y={102} rotate={6} w={92}>
        <circle cx="16" cy="15" r="7" fill={B600} /><path d="m12.5 15 2.5 2.5 4.5-5" stroke={W} strokeWidth="2" fill="none" strokeLinecap="round" />
        <text x="28" y="19.5" fontSize="11.5" fontWeight="800" fill={INK} fontFamily="system-ui, sans-serif">Verified</text>
      </Chip>
      <Chip x={226} y={150} rotate={-6} w={84}>
        <Star x={15} y={15} />
        <text x="26" y="19.5" fontSize="11.5" fontWeight="800" fill={INK} fontFamily="system-ui, sans-serif">Featured</text>
      </Chip>
      <Sparkle x={282} y={80} s={0.7} /><Sparkle x={140} y={60} s={0.6} c={B400} />
    </Frame>
  );
}
