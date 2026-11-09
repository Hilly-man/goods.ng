const fs = require("fs");
const path = require("path");
const { chromium } = require("/Users/hillyman/Documents/goods.ng/frontend/node_modules/@playwright/test");

const dir = __dirname;
const part0 = fs.readFileSync(path.join(dir, "part0.html"), "utf8");
const head = part0
  .slice(0, part0.indexOf("<body>"))
  .replace(/<title>.*?<\/title>/, "<title>Goods.ng — Integrations &amp; Licensed Partners</title>");
const body = fs.readFileSync(path.join(dir, "part5.html"), "utf8");
const html = `<!DOCTYPE html><html lang="en">${head}<body>${body}</body></html>`;
const htmlPath = path.join(dir, "goodsng-integrations-licensed-partners.html");
fs.writeFileSync(htmlPath, html);

const out = "/Users/hillyman/Documents/goods.ng/frontend/public/docs/goodsng-integrations-licensed-partners.pdf";
const copy = "/Users/hillyman/Documents/goods.ng/docs/goodsng-integrations-licensed-partners.pdf";

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto("file://" + htmlPath, { waitUntil: "load" });
  await page.waitForTimeout(500);
  await page.pdf({
    path: out,
    format: "A4",
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: "<div></div>",
    footerTemplate:
      '<div style="width:100%;font-size:7px;color:#5C6B60;padding:0 14mm;display:flex;justify-content:space-between;">' +
      "<span>Goods.ng · Integrations &amp; Licensed Partners · v1.0 · 8 November 2026</span>" +
      '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>',
    margin: { top: "14mm", right: "14mm", bottom: "16mm", left: "14mm" },
  });
  await browser.close();
  fs.copyFileSync(out, copy);
  console.log("rendered", out, (fs.statSync(out).size / 1024).toFixed(1) + " KB");
})();
