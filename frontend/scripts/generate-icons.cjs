/* eslint-disable @typescript-eslint/no-require-imports */
const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const root = path.resolve(__dirname, "..");
const icon = fs.readFileSync(path.join(root, "src/app/icon.svg"));
const maskable = fs.readFileSync(path.join(root, "public/icon-maskable.svg"));

async function main() {
  await sharp(icon).resize(1024, 1024).png().toFile("/tmp/goodsng-icon-1024.png");

  await sharp(icon).resize(512, 512).png().toFile(path.join(root, "public/icon-512.png"));
  await sharp(icon).resize(192, 192).png().toFile(path.join(root, "public/icon-192.png"));
  await sharp(icon).resize(180, 180).png().toFile(path.join(root, "src/app/apple-icon.png"));

  await sharp(maskable).resize(512, 512).png().toFile(path.join(root, "public/icon-512-maskable.png"));
  await sharp(maskable).resize(192, 192).png().toFile(path.join(root, "public/icon-192-maskable.png"));

  for (const size of [64, 48, 32, 16]) {
    await sharp(icon).resize(size, size).png().toFile(`/tmp/goodsng-icon-${size}.png`);
  }

  console.log("Generated PNG icons from SVG.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
