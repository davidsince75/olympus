/*
 * render_ice — render dist/ice_surface.html the way the artifact host will, and
 * read the surface back out of its own DOM.
 *
 * The page is wrapped in the real artifact skeleton first, because the published
 * page is wrapped and an unwrapped local render has bitten this project before.
 *
 *   node scripts/render_ice.cjs [out.png]
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'dist', 'ice_surface.html');
const OUT = process.argv[2] || path.join(ROOT, 'dist', 'ice_surface.png');
const EXEC = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const SKELETON = (body) => `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}
[hidden]{display:none!important}</style></head><body>${body}</body></html>`;

(async () => {
  const wrapped = path.join(ROOT, 'dist', '_ice_wrapped.html');
  fs.writeFileSync(wrapped, SKELETON(fs.readFileSync(SRC, 'utf8')));

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1380, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

  await page.goto('file://' + wrapped, { waitUntil: 'load' });
  await page.waitForFunction(() => {
    const t = document.getElementById('r-extent');
    return t && t.textContent !== '—';
  }, null, { timeout: 30000 });
  await page.waitForTimeout(600);

  // Read the instrument back out of the DOM rather than trusting the picture.
  const read = await page.evaluate(() => {
    const txt = (id) => (document.getElementById(id) || {}).textContent;
    const cv = document.getElementById('map');
    const ctx = cv.getContext('2d');
    const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
    let painted = 0;
    for (let i = 0; i < d.length; i += 4 * 97) if (d[i] + d[i + 1] + d[i + 2] > 60) painted++;
    return {
      extent: txt('r-extent'), area: txt('r-icearea'), cells: txt('r-cells'),
      grid: txt('r-grid'), epsg: txt('eyebrow-epsg'), date: txt('eyebrow-date'),
      prov: (document.getElementById('prov') || {}).textContent.slice(0, 90),
      paintedSamples: painted,
      fontLoaded: document.fonts ? document.fonts.check('12px "IBM Plex Mono"') : null
    };
  });

  // Move the cursor onto the pole and check the readout inverts to somewhere real.
  const box = await page.locator('#frame').boundingBox();
  await page.mouse.move(box.x + box.width * 0.52, box.y + box.height * 0.42);
  await page.waitForTimeout(250);
  const cur = await page.evaluate(() => ({
    lat: document.getElementById('r-lat').textContent,
    lon: document.getElementById('r-lon').textContent,
    conc: document.getElementById('r-conc').textContent,
    area: document.getElementById('r-area').textContent
  }));

  await page.screenshot({ path: OUT, fullPage: true });
  await browser.close();
  fs.unlinkSync(wrapped);

  console.log(JSON.stringify({ read, cur, errors }, null, 1));
  if (errors.length) { console.error('page errors present'); process.exit(1); }
  if (read.paintedSamples < 50) { console.error('canvas looks empty'); process.exit(1); }
  console.log('rendered ->', OUT);
})();
