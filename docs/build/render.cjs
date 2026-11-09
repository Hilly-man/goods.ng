const fs = require('fs');
const path = require('path');
const { chromium } = require('/Users/hillyman/Documents/goods.ng/frontend/node_modules/@playwright/test');

const dir = __dirname;
const parts = ['part0.html', 'part1.html', 'part2.html', 'part3.html', 'part4.html'];
const html = parts.map((p) => fs.readFileSync(path.join(dir, p), 'utf8')).join('\n');
const htmlPath = path.join(dir, 'goodsng-prd-tad-frd.html');
fs.writeFileSync(htmlPath, html);

const out1 = '/Users/hillyman/Documents/goods.ng/frontend/public/docs/goodsng-prd-tad-frd.pdf';
const out2 = '/Users/hillyman/Documents/goods.ng/docs/goodsng-prd-tad-frd.pdf';
fs.mkdirSync(path.dirname(out1), { recursive: true });

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + htmlPath, { waitUntil: 'load' });
  await page.waitForTimeout(600);
  await page.pdf({
    path: out1,
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate:
      '<div style="width:100%;font-size:7px;color:#5C6B60;padding:0 14mm;display:flex;justify-content:space-between;">' +
      '<span>Goods.ng · PRD · TAD · FRD · v1.0 · 8 November 2026</span>' +
      '<span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>',
    margin: { top: '14mm', right: '14mm', bottom: '16mm', left: '14mm' },
  });
  await browser.close();
  fs.copyFileSync(out1, out2);
  const s = fs.statSync(out1);
  console.log('rendered', out1, (s.size / 1024).toFixed(1) + ' KB');
  console.log('copied', out2);
})();
