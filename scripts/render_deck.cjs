/*
 * render_deck — render dist/deck.html the way the artifact host will, and read
 * the instrument back out of its own DOM.
 *
 * Wrapped in the real artifact skeleton first: the published deck once carried
 * the skeleton baked into its own source and rendered it twice, so a local
 * render of the unwrapped file is not a render of what people see.
 *
 *   node scripts/render_deck.cjs [out-prefix]
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright-core');

const ROOT = path.join(__dirname, '..');
const SRC = path.join(ROOT, 'dist', 'deck.html');
const PREFIX = process.argv[2] || path.join(ROOT, 'dist', 'deck');
const EXEC = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';

const SKELETON = (body) => `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}
[hidden]{display:none!important}</style></head><body>${body}</body></html>`;

const read = () => {
  const txt = (id) => { const e = document.getElementById(id); return e ? e.textContent.trim() : null; };
  const cv = document.getElementById('map');
  const ctx = cv.getContext('2d');
  const d = ctx.getImageData(0, 0, cv.width, cv.height).data;
  let lit = 0, blue = 0;
  for (let i = 0; i < d.length; i += 4 * 53) {
    if (d[i] + d[i + 1] + d[i + 2] > 90) lit++;
    if (d[i + 2] > d[i] + 12) blue++;
  }
  return {
    proj: txt('proj'), extVal: txt('extVal'), extClim: txt('extClim'),
    extDelta: txt('extDelta'), tDate: txt('tDate'), tYear: txt('tYear'),
    conc: txt('conc'), mapTag: txt('mapTag'), srcfile: txt('srcfile'),
    scalelab: txt('scalelab'), stncount: txt('stncount'), laycount: txt('laycount'),
    canvas: `${cv.width}x${cv.height}`, litSamples: lit, blueSamples: blue
  };
};

(async () => {
  const wrapped = path.join(ROOT, 'dist', '_deck_wrapped.html');
  fs.writeFileSync(wrapped, SKELETON(fs.readFileSync(SRC, 'utf8')));

  const browser = await chromium.launch({ executablePath: EXEC, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1000 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

  await page.goto('file://' + wrapped, { waitUntil: 'load' });
  // The atlases decode a sheet at a time, yielding between each.
  await page.waitForFunction(() => {
    const e = document.getElementById('extVal');
    return e && e.textContent && e.textContent.trim() !== '' && e.textContent.trim() !== '—';
  }, null, { timeout: 90000 }).catch(() => {});
  await page.waitForTimeout(4000);

  const out = { south: await page.evaluate(read) };
  await page.screenshot({ path: PREFIX + '-south.png', fullPage: false });

  // Switch hemisphere through the deck's own control, not by poking state.
  const north = await page.locator('#modeBar button[data-mode="N"]').first();
  if (await north.count()) {
    await north.click();
    await page.waitForTimeout(3500);
    out.north = await page.evaluate(read);
    await page.screenshot({ path: PREFIX + '-north.png', fullPage: false });
  }

  await browser.close();
  fs.unlinkSync(wrapped);

  console.log(JSON.stringify({ out, errors: errors.slice(0, 8) }, null, 1));
  // The render host is offline, so the Google Fonts stylesheet legitimately
  // fails here and only here. Everything else is a real error.
  const real = errors.filter((e) => !/ERR_CONNECTION_RESET|fonts\.googleapis/.test(e));
  const bad = [];
  if (real.length) bad.push(`${real.length} page error(s)`);
  for (const [k, v] of Object.entries(out)) {
    if (!v.litSamples || v.litSamples < 40) bad.push(`${k}: canvas looks empty`);
    if (!v.extVal) bad.push(`${k}: no extent readout`);
  }
  if (bad.length) { console.error('FAIL: ' + bad.join('; ')); process.exit(1); }
  console.log('rendered ->', PREFIX + '-{south,north}.png');
})();
