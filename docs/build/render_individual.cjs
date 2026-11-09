const fs = require("fs");
const path = require("path");
const { chromium } = require("/Users/hillyman/Documents/goods.ng/frontend/node_modules/@playwright/test");

const dir = __dirname;
const part0 = fs.readFileSync(path.join(dir, "part0.html"), "utf8");
const head = part0.slice(0, part0.indexOf("<body>"));

function decode(value) {
  return value
    .replace(/<[^>]+>/g, "")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ")
    .trim();
}

function stripPartCover(part) {
  return part.replace(/^[\s\S]*?\n<\/div>\n\n(?=<div>)/, "");
}

function sections(content) {
  return [...content.matchAll(/<h2>(.*?)<\/h2>/g)].map((match) => decode(match[1]));
}

function cover({ kicker, title, subtitle, includes }) {
  return `
<div class="cover">
  <div class="glow"></div><div class="glow2"></div>
  <div class="brand">GOODS.NG</div>
  <div class="tagline">Buy. Sell. Trade with Confidence.</div>
  <div class="eyebrow" style="color:#B7FF73;position:relative;margin-top:30mm">${kicker}</div>
  <h1 style="margin:4mm 0 6mm">${title}</h1>
  <div class="rule"></div>
  <div class="sub">${subtitle}</div>
  <div style="position:relative;margin-top:9mm;color:#B7FF73;font-size:9pt;max-width:130mm">${includes}</div>
  <div class="meta">
    <div><div class="k">Version</div><div class="v">1.0</div></div>
    <div><div class="k">Date</div><div class="v">8 November 2026</div></div>
    <div><div class="k">Status</div><div class="v">Go-live planning baseline</div></div>
    <div><div class="k">Market</div><div class="v">Nigeria · NGN</div></div>
  </div>
  <div class="footer">
    <span>Confidential — internal product &amp; engineering document</span>
    <span>goods.ng</span>
  </div>
</div>`;
}

function documentControl({ about, audience, callout }) {
  return `
<div style="page-break-after:always">
  <div class="eyebrow">Document control</div>
  <h2>About this document</h2>
  <p>${about}</p>
  <table class="doc-meta tight">
    <tbody>
      <tr><td>Product</td><td>Goods.ng — multi-vendor marketplace for Nigeria</td></tr>
      <tr><td>Owner</td><td>Product &amp; Engineering, Goods.ng</td></tr>
      <tr><td>Audience</td><td>${audience}</td></tr>
      <tr><td>Source of truth</td><td>Repository <span class="req">docs/</span>, application code, migrations and automated tests as of 8 November 2026</td></tr>
      <tr><td>Verification baseline</td><td>205 backend tests, 10 frontend unit tests, Playwright E2E, ruff/eslint/tsc clean, production build passing</td></tr>
      <tr><td>Companion documents</td><td>PRD (priority authority) · TAD (implementation authority) · FRD (acceptance authority)</td></tr>
    </tbody>
  </table>
  <div class="callout">${callout}</div>
</div>`;
}

function tocPage(items) {
  return `
<div class="toc-page">
  <h2>Contents</h2>
  <div class="toc-list">
    ${items.map((item) => `<div class="sub">${item}</div>`).join("\n")}
  </div>
</div>`;
}

function compose({ doc, partFile, extraFile, coverData, controlData, tocExtra = [] }) {
  const content = stripPartCover(fs.readFileSync(path.join(dir, partFile), "utf8"));
  const extra = extraFile ? stripPartCover(fs.readFileSync(path.join(dir, extraFile), "utf8")) : "";
  const items = sections(content);
  const toc = [...items.map((item, index) => `${index + 1}. ${item}`), ...tocExtra];
  return `<!DOCTYPE html><html lang="en">${head}<body>
${cover(coverData)}
${documentControl(controlData)}
${tocPage(toc)}
${content}
${extra}
</body></html>`;
}

const docs = [
  {
    doc: "prd",
    short: "PRD",
    partFile: "part1.html",
    coverData: {
      kicker: "Document 1 of 3",
      title: "Product Requirements Document",
      subtitle:
        "What Goods.ng is, who it serves, what ships in the first release, how it makes money, and the measurable gates that must be met before launch.",
      includes: "14 sections · personas · user journeys · business model · success metrics · launch gates · roadmap · compliance",
    },
    controlData: {
      about:
        "This PRD defines the first production release of Goods.ng. It sets product intent, users, scope, economics, journeys, priorities and launch gates. Implementation detail belongs in the TAD; testable behaviour belongs in the FRD.",
      audience: "Founders, product, design, marketing, operations, finance and compliance",
      callout:
        "<strong>Priority authority.</strong> Where the documents disagree, the PRD decides what matters and in which order; the FRD defines acceptance.",
    },
  },
  {
    doc: "tad",
    short: "TAD",
    partFile: "part2.html",
    extraFile: "part4.html",
    coverData: {
      kicker: "Document 2 of 3",
      title: "Technical Architecture Document",
      subtitle:
        "How the system is structured, deployed, secured and operated, and the exact state of every external integration required for go-live.",
      includes: "22 sections · system context · data and ledger · payments · Flex · security · scalability · Appendix A/B/C (integration checklist, environment variables, glossary)",
    },
    controlData: {
      about:
        "This TAD describes the architecture behind the first release: the modular monolith, PostgreSQL source of truth, Redis cache, worker, provider interfaces, payments and escrow state machine, double-entry ledger, Goods Flex, search and the frontend. Appendix A is the integration go-live checklist.",
      audience: "Engineering, platform, security, QA and integration partners",
      callout:
        "<strong>Integration caveat.</strong> Production boot refuses mock financial providers. Protected Checkout and Goods Flex require licensed escrow and lending partner adapters before live use.",
    },
    tocExtra: ["Appendix A. Integration go-live checklist", "Appendix B. Environment variables", "Appendix C. Glossary"],
  },
  {
    doc: "frd",
    short: "FRD",
    partFile: "part3.html",
    coverData: {
      kicker: "Document 3 of 3",
      title: "Functional Requirements Document",
      subtitle:
        "Testable behaviour for every module: actors, requirement IDs, business rules, state machines, non-functional targets and end-to-end acceptance scenarios.",
      includes: "17 sections · FR-IDs with acceptance criteria · order/payment/negotiation/Flex state machines · NFRs · integration requirements · acceptance scenarios",
    },
    controlData: {
      about:
        "This FRD translates the product scope into testable requirements. Every requirement has a stable ID, a priority and acceptance criteria so it can become an automated or manual test.",
      audience: "QA, engineering, product, operations and compliance",
      callout:
        "<strong>Acceptance authority.</strong> P0 requirements are launch blockers. If a requirement and the implementation disagree, this document defines the expected behaviour.",
    },
  },
];

const outDir = "/Users/hillyman/Documents/goods.ng/frontend/public/docs";
const repoDir = "/Users/hillyman/Documents/goods.ng/docs";
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  const browser = await chromium.launch();
  for (const entry of docs) {
    const html = compose(entry);
    const htmlPath = path.join(dir, `goodsng-${entry.doc}.html`);
    fs.writeFileSync(htmlPath, html);
    const out = path.join(outDir, `goodsng-${entry.doc}.pdf`);
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
        `<div style="width:100%;font-size:7px;color:#5C6B60;padding:0 14mm;display:flex;justify-content:space-between;">` +
        `<span>Goods.ng · ${entry.short} · v1.0 · 8 November 2026</span>` +
        `<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`,
      margin: { top: "14mm", right: "14mm", bottom: "16mm", left: "14mm" },
    });
    await page.close();
    fs.copyFileSync(out, path.join(repoDir, `goodsng-${entry.doc}.pdf`));
    console.log("rendered", out, (fs.statSync(out).size / 1024).toFixed(1) + " KB");
  }
  await browser.close();
})();
