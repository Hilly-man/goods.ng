import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";
import sharp from "sharp";
import { SITE_URL } from "@/lib/seo";

function clean(value: string | null, max: number): string | undefined {
  if (!value) return undefined;
  const text = value
    .replace(/₦/g, "NGN ")
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return text ? text.slice(0, max) : undefined;
}

async function loadImage(raw: string | null): Promise<string | null> {
  if (!raw) return null;
  let url: URL;
  try {
    url = new URL(raw, SITE_URL);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;

  const allowedHosts = new Set(
    [new URL(SITE_URL).host, ...(process.env.OG_IMAGE_HOSTS ?? "").split(",")]
      .map((host) => host.trim())
      .filter(Boolean),
  );
  if (!allowedHosts.has(url.host)) return null;

  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(5000), cache: "force-cache" });
    if (!res.ok) return null;
    const type = (res.headers.get("content-type") ?? "").split(";")[0];
    if (!type.startsWith("image/")) return null;
    const bytes = Buffer.from(await res.arrayBuffer());
    if (!bytes.length || bytes.length > 8_000_000) return null;
    // Satori's image renderer does not decode WebP reliably. Normalise every input to PNG
    // so listing photos (stored as WebP) still appear on social cards.
    const png = await sharp(bytes).resize(860, 860, { fit: "cover" }).png().toBuffer();
    return `data:image/png;base64,${png.toString("base64")}`;
  } catch {
    return null;
  }
}

export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const title = clean(params.get("title"), 100) ?? "Buy. Sell. Trade with Confidence.";
  const subtitle = clean(params.get("subtitle"), 150);
  const eyebrow = clean(params.get("eyebrow"), 40);
  const price = clean(params.get("price"), 24);
  const badge = clean(params.get("badge"), 32);
  const image = await loadImage(params.get("image"));

  const titleSize = title.length > 80 ? 40 : title.length > 60 ? 48 : 58;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          position: "relative",
          overflow: "hidden",
          background: "#18251D",
          color: "#ffffff",
          padding: "56px 64px",
        }}
      >
        <div
          style={{
            position: "absolute",
            top: -180,
            right: -140,
            width: 560,
            height: 560,
            borderRadius: 9999,
            background: "#B7FF73",
            opacity: 0.13,
            display: "flex",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -240,
            left: -160,
            width: 520,
            height: 520,
            borderRadius: 9999,
            background: "#B7FF73",
            opacity: 0.07,
            display: "flex",
          }}
        />

        <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%", position: "relative" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
              <div
                style={{
                  width: 46,
                  height: 46,
                  borderRadius: 12,
                  background: "#B7FF73",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#18251D",
                  fontSize: 25,
                  fontWeight: 900,
                }}
              >
                G
              </div>
              <div style={{ display: "flex", flexDirection: "column" }}>
                <span style={{ fontSize: 26, fontWeight: 800, letterSpacing: 1.4, color: "#B7FF73" }}>GOODS.NG</span>
                <span style={{ fontSize: 15, color: "#C9D6C9" }}>Buy. Sell. Trade with Confidence.</span>
              </div>
            </div>
            {badge ? (
              <div
                style={{
                  display: "flex",
                  background: "#B7FF73",
                  color: "#18251D",
                  padding: "10px 16px",
                  borderRadius: 999,
                  fontSize: 16,
                  fontWeight: 800,
                }}
              >
                {badge}
              </div>
            ) : null}
          </div>

          <div style={{ display: "flex", flex: 1, alignItems: "center", gap: image ? 48 : 0, marginTop: 28 }}>
            <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
              {eyebrow ? (
                <span style={{ fontSize: 18, letterSpacing: 2, textTransform: "uppercase", color: "#B7FF73", fontWeight: 700 }}>
                  {eyebrow}
                </span>
              ) : null}
              <span style={{ fontSize: titleSize, lineHeight: 1.08, fontWeight: 900, marginTop: 14, letterSpacing: -1 }}>
                {title}
              </span>
              {subtitle ? (
                <span style={{ fontSize: 22, lineHeight: 1.35, color: "#D7E3D5", marginTop: 18 }}>{subtitle}</span>
              ) : null}
              {price ? (
                <span
                  style={{
                    display: "flex",
                    alignSelf: "flex-start",
                    background: "#B7FF73",
                    color: "#18251D",
                    fontSize: 28,
                    fontWeight: 900,
                    padding: "10px 18px",
                    borderRadius: 10,
                    marginTop: 22,
                  }}
                >
                  {price}
                </span>
              ) : null}
            </div>

            {image ? (
              <div
                style={{
                  display: "flex",
                  width: 430,
                  height: 430,
                  borderRadius: 24,
                  overflow: "hidden",
                  border: "6px solid rgba(255,255,255,0.12)",
                  background: "#22352A",
                }}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={image}
                  alt=""
                  width={430}
                  height={430}
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              </div>
            ) : null}
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              borderTop: "1px solid rgba(255,255,255,0.16)",
              paddingTop: 18,
              fontSize: 15,
              color: "#9FB39F",
            }}
          >
            <span>Escrow-protected checkout · Verified sellers · Goods Flex</span>
            <span>goods.ng</span>
          </div>
        </div>
      </div>
    ),
    {
      width: 1200,
      height: 630,
      headers: {
        "Cache-Control": "public, max-age=86400, s-maxage=604800, stale-while-revalidate=86400",
      },
    },
  );
}
