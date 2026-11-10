/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Render the Goods Flex (BNPL) motion ad at 16:9 and 9:16.
 *
 *   node scripts/render-flex-promo.cjs
 *
 * Requires Playwright (already a dev dependency) and ffmpeg. Set FFMPEG to the binary if it is not on
 * the default path used below. Frames are rendered deterministically via window.render(t) and encoded
 * with the soundtrack from the existing Goods.ng promo.
 */
const { chromium } = require("@playwright/test");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const SOURCE = path.join(ROOT, "public/promo/flex/source.html");
const OUT = path.join(ROOT, "public/promo");
const TMP = "/tmp/goods-flex-render";
const FFMPEG = process.env.FFMPEG || "/Users/hillyman/Documents/goods.ng/backend/.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v9.0";
const FPS = 30;
const DURATION = 25;

const FORMATS = [
  { name: "flex-16x9", width: 1920, height: 1080, poster: "flex-poster-16x9.jpg", posterAt: 24.0 },
  { name: "flex-9x16", width: 1080, height: 1920, poster: "flex-poster-9x16.jpg", posterAt: 24.0 },
];

function sh(cmd, args) {
  execFileSync(cmd, args, { stdio: "inherit" });
}

function buildAudio() {
  const audio = path.join(TMP, "audio.m4a");
  if (fs.existsSync(audio)) return audio;
  try {
    sh(FFMPEG, ["-y", "-i", path.join(OUT, "goodsng-promo-16x9.mp4"), "-t", String(DURATION), "-vn",
      "-af", "afade=t=in:st=0:d=0.7,afade=t=out:st=" + (DURATION - 1.6) + ":d=1.6",
      "-c:a", "aac", "-b:a", "128k", audio]);
    return audio;
  } catch (e) {
    console.warn("Could not extract soundtrack; rendering silent video.", e.message);
    sh(FFMPEG, ["-y", "-f", "lavfi", "-i", `anullsrc=r=44100:cl=stereo`, "-t", String(DURATION),
      "-c:a", "aac", "-b:a", "128k", audio]);
    return audio;
  }
}

async function render(browser, fmt, audio) {
  const page = await browser.newPage({ viewport: { width: fmt.width, height: fmt.height }, deviceScaleFactor: 1 });
  await page.goto("file://" + SOURCE);
  await page.waitForFunction(() => window.__ready === true);
  await page.evaluate(() => document.fonts && document.fonts.ready);

  const dir = path.join(TMP, fmt.name);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });

  const total = FPS * DURATION;
  for (let i = 0; i < total; i++) {
    await page.evaluate((t) => window.render(t), i / FPS);
    await page.screenshot({ path: path.join(dir, `f_${String(i).padStart(5, "0")}.jpg`), type: "jpeg", quality: 96 });
    if (i % 150 === 0) console.log(`${fmt.name}: ${i}/${total} frames`);
  }

  // Poster
  await page.evaluate((t) => window.render(t), fmt.posterAt);
  await page.screenshot({ path: path.join(OUT, fmt.poster), type: "jpeg", quality: 92 });

  const mp4 = path.join(OUT, `goodsng-${fmt.name}.mp4`);
  sh(FFMPEG, ["-y", "-framerate", String(FPS), "-i", path.join(dir, "f_%05d.jpg"), "-i", audio,
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-crf", "18", "-preset", "medium",
    "-movflags", "+faststart", "-c:a", "aac", "-b:a", "128k", "-shortest", mp4]);
  await page.close();
  console.log(`Wrote ${mp4}`);
}

(async () => {
  fs.mkdirSync(TMP, { recursive: true });
  const audio = buildAudio();
  const browser = await chromium.launch();
  for (const fmt of FORMATS) await render(browser, fmt, audio);
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
