#!/usr/bin/env node
/*
 * probe_decklog — the Deck log says what the record says, and nothing else.
 *
 * Asserts on what a reader sees and takes away, not on objects built:
 *   - the log opens (button and L), follows the dial, and closes (Esc)
 *   - the values in "This month" are the carried values at their carried
 *     precision; outside a source's coverage the cell is empty and says NO OBS
 *   - no cell anywhere reads NaN, undefined, null or Infinity
 *   - the extent series has one row per calendar month, the four outage months
 *     among them, empty and marked; the index column is OSI SAF's integer km2
 *   - each CSV parses, has the rows the record has, and equals the record
 *   - on an ordinary host "Download CSV" saves exactly that text
 *   - every explainer the log points at exists
 *   - on a 390 px phone the open log does not widen the page
 *
 *   node scripts/probe_decklog.cjs [dist/deck.html]
 */
'use strict';
const fs = require('fs');
const path = require('path');
let chromium;
try { ({ chromium } = require('playwright-core')); } catch (e) { ({ chromium } = require('playwright')); }

const ROOT = path.join(__dirname, '..');
const SRC = path.resolve(process.argv[2] || path.join(ROOT, 'dist', 'deck.html'));
const CHROME = process.env.OLYMPUS_CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const ANCHOR = '\nrequestAnimationFrame(frame);\n})();\n</script>';
const HARNESS = '\nwindow.__oly=()=>({st,sync,drawTL,OSI,EX,LAYERS,EXPL,NMON,YM0,DL,DECKLOG,LIVE,lgCSVText,lgSeries,logOpen,frameAt,hemiKey});\n';
const SK = (body) => `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${body}</body></html>`;

let pass = 0, fail = 0;
const ok = (name, cond, detail = '') => { if (cond) pass++; else fail++; console.log(`${cond ? '  ok  ' : '  FAIL'}  ${name}${detail ? '  — ' + detail : ''}`); };

function parseCSV(text) {
  const lines = text.split('\n').filter((l) => l.length && !l.startsWith('#'));
  const split = (l) => { const out = []; let cur = '', q = false;
    for (let i = 0; i < l.length; i++) { const c = l[i];
      if (q) { if (c === '"' && l[i + 1] === '"') { cur += '"'; i++; } else if (c === '"') q = false; else cur += c; }
      else if (c === '"') q = true; else if (c === ',') { out.push(cur); cur = ''; } else cur += c; }
    out.push(cur); return out; };
  const head = split(lines[0]);
  return { head, rows: lines.slice(1).map((l) => { const v = split(l); const o = {}; head.forEach((h, i) => { o[h] = v[i]; }); return o; }) };
}

(async () => {
  const raw = fs.readFileSync(SRC, 'utf8');
  if (!raw.includes(ANCHOR)) { console.log('FAIL  harness anchor not found'); process.exit(1); }
  const tmp = path.join(ROOT, 'build', '_probe_decklog.html');
  fs.writeFileSync(tmp, SK(raw.replace(ANCHOR, '\nrequestAnimationFrame(frame);\n' + HARNESS + '})();\n</script>')));
  const b = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const ctx = await b.newContext({ viewport: { width: 1500, height: 1000 }, acceptDownloads: true });
  const pg = await ctx.newPage();
  await pg.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());
  const errors = [];
  pg.on('pageerror', (e) => errors.push(String(e)));
  // fonts are blocked on purpose here; any other failed request is an error
  pg.on('console', (m) => { if (m.type() === 'error' && !/Failed to load resource/.test(m.text())) errors.push('console: ' + m.text()); });
  pg.on('requestfailed', (r) => { if (!/fonts\.(googleapis|gstatic)/.test(r.url())) errors.push('request failed: ' + r.url().slice(0, 120)); });
  await pg.goto('file://' + tmp, { waitUntil: 'load', timeout: 180000 });
  await pg.waitForFunction(() => window.__oly && window.__oly().DL, null, { timeout: 60000 });

  // ---------------------------------------------------------------- opening
  ok('log starts closed', await pg.evaluate(() => document.getElementById('dlog').hidden === true));
  await pg.keyboard.press('l');
  ok('L opens the log', await pg.evaluate(() => !document.getElementById('dlog').hidden && document.getElementById('logBtn').getAttribute('aria-pressed') === 'true'));
  const last = await pg.evaluate(() => { const A = window.__oly(); const t = A.YM0 + A.OSI.hemi.sh.ymo[A.OSI.hemi.sh.n - 1]; return Math.floor(t / 12) + String(t % 12 + 1).padStart(2, '0'); });
  ok('it opens on the newest month on the record', (await pg.textContent('#dlogYm')).startsWith(last), last);

  // cells of the "Values" table, by quantity and sub-label
  const rowsNow = () => pg.evaluate(() => [...document.querySelectorAll('#dlogBody table.dlt')[0].querySelectorAll('tbody tr:not(.grp)')].map((tr) => {
    const td = tr.querySelectorAll('td'); return { q: td[0].textContent, v: td[1].textContent, s: td[3].textContent }; }));
  const find = (R, q, sub) => R.find((r) => r.q.startsWith(q) && (!sub || r.q.includes(sub)));
  let R = await rowsNow();
  const E = await pg.evaluate(() => { const A = window.__oly(); const H = A.OSI.hemi; return {
    sh: H.sh.ext[H.sh.n - 1].toFixed(3), nh: H.nh.ext[H.nh.n - 1].toFixed(3), ft: !!H.sh.runs[H.sh.runs.length - 1][3],
    shI: A.DECKLOG.sii.hemi.sh.v[A.DECKLOG.sii.hemi.sh.v.length - 1], nhI: A.DECKLOG.sii.hemi.nh.v[A.DECKLOG.sii.hemi.nh.v.length - 1] }; });
  const shDeck = find(R, 'Antarctic sea-ice extent', 'this deck'), nhDeck = find(R, 'Arctic sea-ice extent', 'this deck');
  ok('Antarctic extent is the carried value, 3 decimals', shDeck && shDeck.v === E.sh, shDeck && `${shDeck.v} vs ${E.sh}`);
  ok('Arctic extent is the carried value, 3 decimals', nhDeck && nhDeck.v === E.nh, nhDeck && `${nhDeck.v} vs ${E.nh}`);
  ok('a fast-track month says FT', shDeck && shDeck.s === (E.ft ? 'FT' : 'MEAS'), shDeck && shDeck.s);
  const shIdx = find(R, 'Antarctic sea-ice extent', 'published index');
  ok('OSI SAF index beside it, from the published km²', shIdx && shIdx.v === (E.shI / 1e6).toFixed(3) && shIdx.s === 'REF', shIdx && `${shIdx.v} ${shIdx.s}`);
  const amoc = find(R, 'Overturning');
  ok('AMOC outside RAPID coverage is empty and NO OBS', amoc && amoc.v === '' && amoc.s === 'NO OBS', amoc && `"${amoc.v}" ${amoc.s}`);

  // ---------------------------------------------------------------- the dial drives it
  const want = await pg.evaluate(() => { const A = window.__oly(); const off = 2015 * 12 + 11 - A.YM0; const k = A.frameAt('sh', off);
    A.st.t = k; A.sync(); A.drawTL(); const i = A.EX.amoc.months.indexOf('201512');
    return { moc: A.EX.amoc.moc[i].toFixed(3), ext: A.OSI.hemi.sh.ext[k].toFixed(3) }; });
  R = await rowsNow();
  ok('moving the dial moves the log', (await pg.textContent('#dlogYm')).startsWith('201512'));
  const amoc2 = find(R, 'Overturning');
  ok('AMOC inside coverage is the carried monthly mean', amoc2 && amoc2.v === want.moc && amoc2.s === 'MEAS', amoc2 && `${amoc2.v} vs ${want.moc}`);
  ok('extent follows to the same month', find(R, 'Antarctic sea-ice extent', 'this deck').v === want.ext);
  const roni = find(R, 'Relative Oceanic');
  ok('RONI for the season centred on the month', roni && /^[+−±]\d\.\d\d$/.test(roni.v) && roni.s === 'MEAS', roni && roni.v);
  await pg.click('#dlogNext');
  ok('▶ steps one month', (await pg.textContent('#dlogYm')).startsWith('201601'));

  // ---------------------------------------------------------------- nothing that is not a number
  const junk = async () => pg.evaluate(() => [...document.querySelectorAll('#dlog td, #dlog dd')].map((x) => x.textContent).filter((t) => /\bNaN\b|undefined|\bnull\b|Infinity/.test(t)));
  let J = await junk();
  ok('This month: no NaN, undefined, null or Infinity', J.length === 0, J.slice(0, 3).join(' | '));

  // ---------------------------------------------------------------- series
  await pg.click('#dlogTabSeries');
  const ser = await pg.evaluate(() => {
    const rows = [...document.querySelectorAll('#dlogTW tbody tr')];
    const gaps = rows.filter((r) => r.classList.contains('gap')).map((r) => r.dataset.k);
    const gapCells = rows.filter((r) => r.classList.contains('gap')).map((r) => [r.children[1].textContent, r.children[2].textContent]);
    const cur = rows.filter((r) => r.classList.contains('cur')).map((r) => r.dataset.k);
    return { n: rows.length, gaps, gapCells, cur };
  });
  ok('extent series: one row per calendar month', ser.n === 574, `${ser.n}`);
  ok('the four outage months are rows, marked', JSON.stringify(ser.gaps) === JSON.stringify(['198604', '198605', '198606', '198712']), ser.gaps.join(','));
  ok('an outage month has an empty value, not 0', ser.gapCells.every(([v, s]) => v === '' && s === 'NO OBS'), JSON.stringify(ser.gapCells[0]));
  ok('the month on the dial is highlighted', ser.cur.length === 1 && ser.cur[0] === '201601', ser.cur.join(','));

  const csv = await pg.evaluate(() => { const A = window.__oly(); const out = {};
    for (const id of ['extent', 'clim', 'rapid', 'roni', 'nino', 'nsidc', 'kp']) { const S = A.lgSeries(id); out[id] = S ? A.lgCSVText(S) : null; }
    return out; });
  const X = parseCSV(csv.extent);
  ok('extent CSV: 574 rows, both hemispheres', X.rows.length === 574 && X.head.includes('sh_extent_deck_1e6km2') && X.head.includes('nh_index_km2'), `${X.rows.length} rows`);
  const ref = await pg.evaluate(() => { const A = window.__oly(); const H = A.OSI.hemi; const out = {};
    for (const h of ['sh', 'nh']) { const m = {}; H[h].ymo.forEach((o, k) => { const t = A.YM0 + o; m[Math.floor(t / 12) + String(t % 12 + 1).padStart(2, '0')] = H[h].ext[k].toFixed(3); }); out[h] = m; }
    out.sii = A.DECKLOG.sii.hemi; return out; });
  let bad = 0;
  for (const r of X.rows) for (const h of ['sh', 'nh']) {
    const deck = ref[h][r.yyyymm]; if ((deck || '') !== r[`${h}_extent_deck_1e6km2`]) bad++;
    const S = ref.sii[h], i = (+r.yyyymm.slice(0, 4)) * 12 + (+r.yyyymm.slice(4)) - ((+S.m0.slice(0, 4)) * 12 + (+S.m0.slice(4)));
    const pub = S.v[i]; if ((pub == null ? '' : String(pub)) !== r[`${h}_index_km2`]) bad++;
  }
  ok('extent CSV equals the carried record and the published index, cell for cell', bad === 0, `${bad} mismatches`);
  const gapRow = X.rows.find((r) => r.yyyymm === '198712');
  ok('extent CSV: outage month empty with NO OBS', gapRow && gapRow.sh_extent_deck_1e6km2 === '' && gapRow.sh_status === 'NO OBS' && gapRow.sh_index_km2 === '');
  const RP = parseCSV(csv.rapid), AM = await pg.evaluate(() => window.__oly().EX.amoc);
  ok('RAPID CSV equals the carried series', RP.rows.length === AM.months.length && RP.rows.every((r, i) => r.yyyymm === AM.months[i] && r.moc_sv === AM.moc[i].toFixed(3) && r.upper_mid_ocean_sv === AM.umo[i].toFixed(3)), `${RP.rows.length} rows`);
  const RO = parseCSV(csv.roni), RV = await pg.evaluate(() => window.__oly().LIVE.enso.roni.v);
  ok('RONI CSV equals the carried series', RO.rows.length === RV.length && RO.rows[0].season === 'DJF 1950' && RO.rows.every((r, i) => +r.roni_c === RV[i]), `${RO.rows.length} rows, first ${RO.rows[0] && RO.rows[0].season}`);
  const CL = parseCSV(csv.clim);
  ok('climatology CSV: 12 months, n = 30 each', CL.rows.length === 12 && CL.rows.every((r) => r.sh_n === '30' && r.nh_n === '30'));
  const allCSV = Object.values(csv).filter(Boolean).join('\n');
  ok('no CSV carries NaN, undefined, null or Infinity', !/\bNaN\b|undefined|\bnull\b|Infinity/.test(allCSV));
  ok('every CSV names its build and the EUMETSAT credit where due', Object.values(csv).filter(Boolean).every((t) => /^# Deck log built /m.test(t)) && /Copyright EUMETSAT/.test(csv.extent));

  // on an ordinary host the browser saves the file
  const [dl] = await Promise.all([pg.waitForEvent('download', { timeout: 15000 }).catch(() => null), pg.click('#dlogSave')]);
  let saved = null;
  if (dl) { const p = await dl.path(); saved = { name: dl.suggestedFilename(), body: fs.readFileSync(p, 'utf8') }; }
  ok('Download CSV saves the extent series on an ordinary host', saved && saved.name === 'olympus_sea_ice_extent_monthly.csv'
     && saved.body.split('\n').filter((l) => !l.startsWith('#')).join('\n') === csv.extent.split('\n').filter((l) => !l.startsWith('#')).join('\n'),
     saved ? saved.name : 'no download');

  for (const id of ['clim', 'rapid', 'roni', 'nino', 'nsidc', 'kp']) {
    await pg.click(`[data-ser="${id}"]`);
    const n = await pg.evaluate(() => document.querySelectorAll('#dlogTW tbody tr').length);
    ok(`series "${id}" renders`, n > 0, `${n} rows`);
  }
  J = await junk();
  ok('Series: no NaN, undefined, null or Infinity', J.length === 0, J.slice(0, 3).join(' | '));

  // ---------------------------------------------------------------- sources
  await pg.click('#dlogTabManifest');
  const man = await pg.evaluate(() => ({ cards: document.querySelectorAll('.dlog-card').length,
    checks: [...document.querySelectorAll('.dlog-check')].map((c) => c.querySelector('.r').textContent + ': ' + c.textContent.slice(0, 60)) }));
  ok('Sources: a card per source', man.cards >= 9, `${man.cards} cards`);
  ok('Sources: RAPID and ENSO reproduced from the publishers’ files',
     man.checks.some((c) => c.startsWith('agrees') && c.includes('RAPID')) && man.checks.some((c) => c.startsWith('agrees') && c.includes('ENSO')),
     man.checks.length + ' checks');
  ok('Sources: the climatology recomputes from the carried extents', man.checks.some((c) => c.startsWith('agrees') && c.includes('Climatology')));
  J = await junk();
  ok('Sources: no NaN, undefined, null or Infinity', J.length === 0, J.slice(0, 3).join(' | '));

  // every explainer the log and its button point at exists
  const missing = await pg.evaluate(() => { const E = window.__oly().EXPL; return [...new Set([...document.querySelectorAll('#dlog [data-ex], #logBtn, .legend [data-ex]')].map((e) => e.dataset.ex))].filter((k) => k && !E[k]); });
  ok('every explainer the log points at exists', missing.length === 0, missing.join(', '));
  const layersNoted = await pg.evaluate(() => { const A = window.__oly(); A.logOpen(true, 'frame'); return document.querySelectorAll('#dlogBody table.dlt')[1].querySelectorAll('tbody tr').length === A.LAYERS.length; });
  ok('This month describes every layer in the stack', layersNoted);

  await pg.keyboard.press('Escape');
  await pg.focus('#dlogBody').catch(() => {});
  await pg.keyboard.press('Escape');
  ok('Esc closes the log', await pg.evaluate(() => document.getElementById('dlog').hidden));
  ok('no page errors', errors.length === 0, errors.slice(0, 2).join(' | '));
  await ctx.close();

  // ---------------------------------------------------------------- phone
  const ph = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
  const pp = await ph.newPage();
  await pp.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());
  await pp.goto('file://' + tmp, { waitUntil: 'load', timeout: 180000 });
  await pp.waitForFunction(() => window.__oly && window.__oly().DL, null, { timeout: 60000 });
  await pp.tap('#logBtn');
  await pp.waitForTimeout(400);
  const m = await pp.evaluate(() => { const r = document.getElementById('dlog').getBoundingClientRect();
    return { w: document.documentElement.scrollWidth, open: !document.getElementById('dlog').hidden, top: Math.round(r.top), width: Math.round(r.width) }; });
  ok('phone: the log opens full screen without widening the page', m.open && m.w <= 390 && m.width <= 390 && m.top <= 1, JSON.stringify(m));
  await pp.click('#dlogTabSeries');
  const m2 = await pp.evaluate(() => document.documentElement.scrollWidth);
  ok('phone: the wide series table scrolls inside its box', m2 <= 390, `${m2} px`);
  await ph.close();

  await b.close();
  fs.unlinkSync(tmp);
  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(1); });
