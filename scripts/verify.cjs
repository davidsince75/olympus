#!/usr/bin/env node
/*
 * verify — the whole probe suite, one command, one verdict.
 *
 * Until 24 Sep 2026 the probes were run one by one, by hand, from whichever
 * directory the last session happened to use. Four of them no longer ran at
 * all (relative paths into a src/ that had moved, a stub the learning layer
 * had outgrown), one reported a known defect as "ok", and one failed on a false
 * positive — so the suite was red by default and nobody could tell a new
 * failure from an old one. This runs every probe that is a regression test,
 * from the repo root, against the files that are published, and adds the
 * checks the audit found missing: the page as a stranger meets it, and the
 * page on a phone.
 *
 *   node scripts/verify.cjs            # needs playwright + jsdom, and Chromium
 *
 * Not included, deliberately: probe_aurora.cjs is a before/after comparison
 * for one change (14 Sep), not a regression test; perf_compare, profile_frame
 * and the shot scripts produce pictures and numbers for a person to read.
 */
'use strict';
const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DIST = (f) => path.join(ROOT, 'dist', f);
const SURFACES = ['deck.html', 'atlas.html', 'named_ice.html'];
const CHROME = process.env.OLYMPUS_CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const CAP = 16 * 1024 * 1024;

const results = [];
const rec = (name, ok, detail = '') => {
  results.push({ name, ok, detail });
  console.log(`${ok ? '  ok  ' : '  FAIL'}  ${name}${detail ? '  — ' + detail : ''}`);
};

function run(name, args, pass) {
  const r = spawnSync(process.execPath, args, { cwd: ROOT, encoding: 'utf8', timeout: 20 * 60 * 1000,
                                               maxBuffer: 64 * 1024 * 1024 });
  const out = (r.stdout || '') + (r.stderr || '');
  let ok = r.status === 0;
  let detail = '';
  if (pass) { const v = pass(out, r.status); ok = v.ok; detail = v.detail || ''; }
  if (!ok && !detail) detail = out.trim().split('\n').slice(-3).join(' | ').slice(0, 300);
  rec(name, ok, detail);
}

// ---------------------------------------------------------------- static checks
console.log('\n-- what is published --');
for (const f of SURFACES) {
  const p = DIST(f);
  if (!fs.existsSync(p)) { rec(`${f} exists`, false); continue; }
  const s = fs.readFileSync(p, 'utf8');
  rec(`${f}: no host skeleton baked in`, !/^<!doctype/i.test(s) && !s.includes('<meta charset=utf8><meta name=viewport'),
      'publish adds its own; a baked one renders twice');
  const b = fs.statSync(p).size;
  rec(`${f}: under the 16 MB artifact cap`, b < CAP, `${(b / 1048576).toFixed(2)} MiB, ${(100 * b / CAP).toFixed(0)}% of cap`);
  const n = (s.match(/\nconst LIVE = /g) || []).length;
  if (f !== 'named_ice.html') {
    rec(`${f}: exactly one living-layer payload`, n === 1, `${n}`);
    if (n === 1) {
      const i = s.indexOf('\nconst LIVE = ') + 14, j = s.indexOf('\n', i);
      const L = JSON.parse(s.slice(i, j).replace(/;\s*$/, ''));
      const age = (Date.now() - Date.parse(L.meta.built)) / 864e5;
      rec(`${f}: living layer rebuilt within 7 days`, age < 7, `built ${L.meta.built}, ${age.toFixed(1)} d ago — run ingest/build_events.py`);
    }
  }
}
{
  const s = fs.readFileSync(DIST('deck.html'), 'utf8');
  const m = s.match(/const LAYERS=\[([\s\S]*?)\n\];/);
  const simOn = m ? m[1].split('\n').filter((l) => /sim:true/.test(l) && /on:true/.test(l)).map((l) => (l.match(/id:"(\w+)"/) || [])[1]) : ['?'];
  rec('deck opens on what is measured (no SIM layer on at open)', m && simOn.length === 0, simOn.join(', '));
  // the opening view (24 Sep 2026): globe, Temp, season, over the Pacific, El Niño featured
  rec('deck opens on the globe, coloured by temperature, season on',
      /const st=\{ S:true, mode:"GLOBE"/.test(s) && /flowCol:"temp", flowSeason:true/.test(s)
      && /data-mode="GLOBE" aria-pressed="true"/.test(s) && /data-fc="temp"\s+aria-pressed="true"/.test(s));
  {
    const i = s.indexOf('\nconst LIVE = ') + 14, j = s.indexOf('\n', i);
    const L = JSON.parse(s.slice(i, j).replace(/;\s*$/, ''));
    const E = L.enso;
    rec('the featured event carries NOAA data', !!E && !!E.status && /^(Final )?(El Niño|La Niña) (Advisory|Watch)$|^Not Active$/.test(E.status.alert),
        E ? `${E.status.alert}, issued ${E.status.issued}` : 'no LIVE.enso');
    if (E) {
      const age = (Date.now() - Date.parse(E.weekly.week + 'T12:00:00Z')) / 864e5;
      rec('the weekly Niño-3.4 is at most three weeks old', age < 21, `week of ${E.weekly.week}, ${age.toFixed(0)} d`);
      rec('the anomaly field reproduces CPC\'s weekly Niño-3.4', Math.abs(E.field.n34_check - E.weekly.trad34) <= 0.25,
          `box ${E.field.n34_check} vs CPC ${E.weekly.trad34}`);
      rec('the anomaly field has contours to draw', E.field.contours.some((c) => c.lines.length > 0),
          E.field.contours.map((c) => `${c.level > 0 ? '+' : ''}${c.level}: ${c.lines.length}`).join(', '));
    }
  }
  const retired = ['Ines Halvorsen', 'Uncertainty is drawn, not hidden', 'last 18 h', 'the engine is visible'];
  const found = retired.filter((t) => s.includes(t));
  rec('deck carries none of the retired claims', found.length === 0, found.join(', '));
}

// ---------------------------------------------------------------- probes
console.log('\n-- probes --');
const tally = (re) => (out) => { const m = out.match(re); return { ok: !!m && +m[2] === 0, detail: m ? `${m[1]} passed, ${m[2]} failed` : 'no tally' }; };
run('projection: js agrees with python', ['scripts/probe_proj.cjs'], (o, s) => ({ ok: s === 0 && /PASS/.test(o) }));
run('learning layer: deck', ['scripts/probe_learn.cjs', 'dist/deck.html'], (o, s) => ({ ok: s === 0 && /\nPASS/.test(o) }));
run('learning layer: atlas', ['scripts/probe_learn.cjs', 'dist/atlas.html'], (o, s) => ({ ok: s === 0 && /\nPASS/.test(o) }));
run('atlas touch and pointer paths', ['probe_atlas_touch.cjs', 'dist/atlas.html'], (o, s) => ({ ok: s === 0 && /all checks passed/.test(o) }));
run('ocean plane', ['scripts/probe_ocean.cjs', 'dist/deck.html', path.join(ROOT, 'build', 'shots')], tally(/(\d+) passed, (\d+) failed/));
run('no deep-limb vertex on land', ['scripts/land_check.cjs', 'dist/deck.html'], (o) => ({ ok: /CLEAN/.test(o) }));
run('every layer switch changes the picture', ['scripts/probe_layers.cjs', 'dist/deck.html'], (o) => {
  const j = o.slice(o.indexOf('{'), o.lastIndexOf('}') + 1);
  let R; try { R = JSON.parse(j.replace(/\nERRORS:[\s\S]*$/, '')); } catch (e) { return { ok: false, detail: 'unparsable output' }; }
  const errs = /ERRORS: \[\]/.test(o);
  const S = R.S || R[Object.keys(R)[0]];
  // the ground track is a globe-less placeholder; El Niño is tropical and lives on the globe
  const inert = Object.entries(S.layers).filter(([k, v]) => v <= (S.noise || 0) && k !== 'track' && k !== 'enso').map(([k]) => k);
  const G = R.GLOBE || {};
  const ensoInk = G.layers ? G.layers.enso : undefined;
  const ok = errs && inert.length === 0 && (ensoInk === undefined || ensoInk > (G.noise || 0));
  return { ok, detail: (inert.length ? `inert on the Antarctic disc: ${inert.join(', ')}` : `${Object.keys(S.layers).length - 2} draw on the Antarctic disc`)
                     + (ensoInk !== undefined ? `; El Niño contours on the globe: ${ensoInk} px` : '') };
});
run('disc and globe zoom', ['scripts/probe_zoom.cjs', 'dist/deck.html'], (o) => ({ ok: /"errors": \[\]/.test(o) && /"pct_G_reset": "100%"/.test(o) }));

// ---------------------------------------------------------------- phones
console.log('\n-- on a phone --');
(async () => {
  let chromium;
  try { ({ chromium } = require('playwright-core')); } catch (e) { ({ chromium } = require('playwright')); }
  const SK = (body) => `<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:light}body{margin:0;padding:0}img{max-width:100%}[hidden]{display:none!important}</style></head><body>${body}\n</body></html>`;
  const b = await chromium.launch({ executablePath: CHROME, args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  for (const f of SURFACES) {
    const tmp = path.join(ROOT, 'build', `_phone_${f}`);
    fs.writeFileSync(tmp, SK(fs.readFileSync(DIST(f), 'utf8')));
    const ctx = await b.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
    const pg = await ctx.newPage();
    await pg.route(/fonts\.(googleapis|gstatic)/, (r) => r.abort());
    const errs = []; pg.on('pageerror', (e) => errs.push(String(e)));
    const t0 = Date.now();
    await pg.goto('file://' + tmp, { waitUntil: 'load', timeout: 120000 });
    const tl = Date.now() - t0;
    await pg.waitForTimeout(2500);
    const m = await pg.evaluate(() => new Promise((res) => { let n = 0; const t0 = performance.now();
      (function f() { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else res({ fps: n / 2, w: document.documentElement.scrollWidth }); })(); }));
    rec(`${f}: fits a 390 px phone`, m.w <= 390, `document ${m.w} px wide`);
    rec(`${f}: loads and animates on the build host`, tl < 15000 && m.fps >= 5 && errs.length === 0,
        `load ${tl} ms, ${m.fps.toFixed(0)} fps (software raster)${errs.length ? ', ' + errs[0] : ''}`);
    await ctx.close(); fs.unlinkSync(tmp);
  }
  await b.close();
  const bad = results.filter((r) => !r.ok);
  console.log(`\n${results.length - bad.length} passed, ${bad.length} failed`);
  process.exit(bad.length ? 1 : 0);
})();
