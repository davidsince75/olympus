/* probe_atlas_touch.cjs — behavioural probe for the patched Atlas interaction.
 *
 * Extracts the interaction section out of the patched atlas.html and runs it
 * under jsdom against stubs for layout/draw/discFor/select. This tests the
 * GESTURE STATE MACHINE, not the projection: the stubbed layout() is a
 * simplified single-disc model, so pan and zoom values are self-consistent but
 * are not the real numbers. What it can prove is that the right branches fire,
 * that state is cleaned up, and that tap-to-select survives.
 *
 * Run: node probe_atlas_touch.cjs atlas_test.html
 */
const fs = require('fs');
const { JSDOM } = require('jsdom');

const file = process.argv[2] || 'atlas_test.html';
const html = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');

const START = '/* ---------------- interaction ---------------- */';
const END = '/* ---------------- routing ---------------- */';
const i = html.indexOf(START), j = html.indexOf(END);
if (i < 0 || j < 0) { console.error('could not locate the interaction section'); process.exit(2); }
const section = html.slice(i, j);

const PRELUDE = `
const LOG = { selects: [], draws: 0 };
const st = { discs:[], w:1000, h:600, sel:null,
  zoom:{S:1,N:1}, pan:{S:{x:0,y:0},N:{x:0,y:0}}, drag:null,
  ptrs:new Map(), pinch:null };
const map = document.getElementById('map');
map.getBoundingClientRect = () => ({left:0, top:0, right:1000, bottom:600, width:1000, height:600});
map.setPointerCapture = () => {};
map.releasePointerCapture = () => {};
const TIP = { style:{}, innerHTML:'' };
function $(sel){ return sel === '#tip' ? TIP : { style:{}, innerHTML:'' }; }
let HOT = [{ id:'aq-concordia', x:400, y:300, r:10 }];
const BY = new Map([['aq-concordia', {name:'Concordia', operator:'IPEV', seasonality:'Year-Round', _kind:'station'}]]);
function esc(s){ return String(s); }
function invLat(){ return -75; }
function invLon(){ return 123; }
function layout(){
  const z = st.zoom.S, r = 250, k = r*z;
  st.discs = [{ S:true, cx:500 - st.pan.S.x*k, cy:300 + st.pan.S.y*k, r, k, z, x0:0, x1:1000 }];
}
function draw(){ LOG.draws++; }
function discFor(S){ return st.discs.find(d => d.S === S) || null; }
function select(id){ st.sel = id; LOG.selects.push(id); }
layout();
window.__P = { st, LOG, TIP, layout };
`;

const dom = new JSDOM('<!doctype html><html><body><canvas id="map"></canvas></body></html>',
  { pretendToBeVisual: true, runScripts: 'outside-only' });
const { window } = dom;
window.eval(PRELUDE + '\n' + section);

// `const` inside the evaluated source is scoped to that evaluation, so the
// prelude publishes what the probe needs onto window explicitly.
const P = window.__P;
const st = P.st, LOG = P.LOG, TIP = P.TIP;
const map = window.document.getElementById('map');
const PE = window.PointerEvent;

function fire(type, id, x, y, kind) {
  map.dispatchEvent(new PE(type, {
    bubbles: true, cancelable: true, pointerId: id,
    pointerType: kind || 'touch', clientX: x, clientY: y, isPrimary: id === 1
  }));
}
function reset() {
  st.ptrs.clear(); st.pinch = null; st.drag = null; st.sel = null;
  st.zoom.S = 1; st.pan.S = { x: 0, y: 0 };
  LOG.selects.length = 0;
  P.layout();
}

let fails = 0;
function check(name, cond, detail) {
  if (cond) console.log('  PASS  ' + name);
  else { fails++; console.log('  FAIL  ' + name + (detail !== undefined ? '  — ' + detail : '')); }
}

// --- 1. touch tap on a hot target selects it -------------------------------
reset();
fire('pointerdown', 1, 400, 300);
fire('pointerup', 1, 400, 300);
console.log('touch tap on a station');
check('selects the station', LOG.selects[0] === 'aq-concordia', JSON.stringify(LOG.selects));

// --- 2. touch tap with fingertip jitter still selects -----------------------
// This is the regression the patch had to avoid: before it, no pointermove
// fired on touch so `moved` stayed 0. Once pointermove fires, path-length
// accumulation past 4 px would have killed selection.
reset();
fire('pointerdown', 1, 400, 300);
fire('pointermove', 1, 402, 301);
fire('pointermove', 1, 399, 303);
fire('pointermove', 1, 403, 302);
fire('pointerup', 1, 403, 302);
console.log('touch tap with 6 px of accumulated jitter');
check('still selects', LOG.selects[0] === 'aq-concordia', JSON.stringify(LOG.selects));

// --- 3. touch drag pans and does not select --------------------------------
reset();
fire('pointerdown', 1, 400, 300);
fire('pointermove', 1, 440, 300);
fire('pointermove', 1, 500, 320);
fire('pointerup', 1, 500, 320);
console.log('touch drag');
check('pan.x moved', Math.abs(st.pan.S.x) > 1e-6, String(st.pan.S.x));
check('pan.y moved', Math.abs(st.pan.S.y) > 1e-6, String(st.pan.S.y));
check('no selection', LOG.selects.length === 0, JSON.stringify(LOG.selects));
check('drag state cleared', st.drag === null);

// --- 4. pinch out zooms in -------------------------------------------------
reset();
fire('pointerdown', 1, 400, 300);
fire('pointerdown', 2, 500, 300);
const z0 = st.zoom.S;
fire('pointermove', 2, 560, 300);
console.log('pinch out');
check('pinch state opened', st.pinch !== null);
check('zoom increased', st.zoom.S > z0, z0 + ' -> ' + st.zoom.S);

// --- 5. pinch in zooms out -------------------------------------------------
const z1 = st.zoom.S;
fire('pointermove', 2, 460, 300);
console.log('pinch in');
check('zoom decreased', st.zoom.S < z1, z1 + ' -> ' + st.zoom.S);

// --- 6. releasing a pinch does not select ----------------------------------
fire('pointerup', 2, 460, 300);
console.log('one contact lifted out of the pinch');
check('pinch closed', st.pinch === null);
check('survivor re-seated as a pan origin', st.drag !== null && st.drag.noTap === true);
fire('pointerup', 1, 400, 300);
check('no selection from either release', LOG.selects.length === 0, JSON.stringify(LOG.selects));
check('all contacts cleared', st.ptrs.size === 0 && st.drag === null);

// --- 7. zoom clamps hold under a violent pinch -----------------------------
reset();
fire('pointerdown', 1, 480, 300);
fire('pointerdown', 2, 520, 300);
for (let k = 0; k < 40; k++) fire('pointermove', 2, 520 + k * 40, 300);
console.log('runaway pinch out');
check('zoom clamped at 14', st.zoom.S === 14, String(st.zoom.S));
for (let k = 40; k >= 0; k--) fire('pointermove', 2, 521 + k, 300);
console.log('runaway pinch in');
check('zoom clamped at 0.55', st.zoom.S === 0.55, String(st.zoom.S));
fire('pointerup', 2, 521, 300); fire('pointerup', 1, 480, 300);

// --- 8. pointercancel cleans up -------------------------------------------
reset();
fire('pointerdown', 1, 400, 300);
fire('pointerdown', 2, 500, 300);
fire('pointercancel', 2, 500, 300);
fire('pointercancel', 1, 400, 300);
console.log('pointercancel');
check('everything cleared', st.ptrs.size === 0 && st.pinch === null && st.drag === null);

// --- 9. the mouse path is unchanged ----------------------------------------
reset();
fire('pointerdown', 1, 400, 300, 'mouse');
fire('pointerup', 1, 401, 300, 'mouse');
console.log('mouse click');
check('selects', LOG.selects[0] === 'aq-concordia', JSON.stringify(LOG.selects));

reset();
fire('pointerdown', 1, 400, 300, 'mouse');
fire('pointermove', 1, 470, 320, 'mouse');
fire('pointerup', 1, 470, 320, 'mouse');
console.log('mouse drag');
check('pans', Math.abs(st.pan.S.x) > 1e-6, String(st.pan.S.x));
check('no selection', LOG.selects.length === 0);

reset();
fire('pointermove', 1, 400, 300, 'mouse');
console.log('mouse hover with no button down');
check('tooltip shown for mouse', TIP.style.opacity === 1,
  String(TIP.style.opacity));
reset();
TIP.style.opacity = 0;
fire('pointermove', 1, 400, 300, 'touch');
check('tooltip NOT shown for touch', TIP.style.opacity === 0,
  String(TIP.style.opacity));

console.log('\n' + (fails ? fails + ' FAILURE(S)' : 'all checks passed'));
process.exit(fails ? 1 : 0);
