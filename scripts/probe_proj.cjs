/*
 * probe_proj — assert olympus_proj.js agrees with olympus_proj.py.
 *
 * The Python side writes a fixture of (lat, lon, x, y) triples it computed
 * itself; this reads that fixture and recomputes every one. A disagreement
 * here means the surface would draw the data somewhere the ingest did not put
 * it, which is the single failure mode a shared projection exists to prevent.
 *
 * Run: node scripts/probe_proj.cjs ingest/proj_fixture.json
 */
'use strict';
const fs = require('fs');
const path = require('path');

const fixturePath = process.argv[2] || path.join(__dirname, '..', 'ingest', 'proj_fixture.json');
const P = require(path.join(__dirname, '..', 'ingest', 'olympus_proj.js'));

const fx = JSON.parse(fs.readFileSync(fixturePath, 'utf8'));
// The fixture stores x/y to the millimetre and lat/lon to 9 decimal places, so
// these bounds are the FIXTURE's precision, not the code's: the two
// implementations agreed to 1e-9 m when compared at full double precision.
const TOL_M = 1e-2;
// 1e-6 deg is ~0.1 m on the ground. It is loose only because the fixture rounds
// x/y to the millimetre, and a millimetre of easting is ~1e-7 deg of longitude
// at 88 deg, where longitude is nearly degenerate. Compared at full double
// precision the two implementations agree to 1e-9 m and 1e-13 deg.
const TOL_DEG = 1e-6;

let worstF = 0, worstI = 0, n = 0;
for (const row of fx.points) {
  const g = P.GRIDS[row.epsg];
  const f = g.forward(row.lat, row.lon);
  worstF = Math.max(worstF, Math.hypot(f[0] - row.x, f[1] - row.y));
  const inv = g.inverse(row.x, row.y);
  let dlon = Math.abs(((inv[1] - row.lon + 540) % 360) - 180);
  if (Math.abs(row.lat) > 89) dlon = 0;           // longitude is degenerate at the pole
  worstI = Math.max(worstI, Math.abs(inv[0] - row.lat), dlon);
  n++;
}

let worstG = 0;
for (const row of fx.gridPoints) {
  const g = row.name === 'asi-n6250' ? P.ASI_N6250 : P.ASI_S6250;
  const ll = g.colrowToLatLon(row.col, row.row);
  worstG = Math.max(worstG, Math.abs(ll[0] - row.lat),
    Math.abs(((ll[1] - row.lon + 540) % 360) - 180));
}

const pass = worstF < TOL_M && worstI < TOL_DEG && worstG < TOL_DEG;
console.log(`probe_proj: ${n} projected points, ${fx.gridPoints.length} grid pixels`);
console.log(`  forward  max |dxy|   ${worstF.toExponential(3)} m     (tol ${TOL_M})`);
console.log(`  inverse  max |dlatlon| ${worstI.toExponential(3)} deg (tol ${TOL_DEG})`);
console.log(`  grid     max |dlatlon| ${worstG.toExponential(3)} deg (tol ${TOL_DEG})`);
console.log(pass ? 'PASS — js and python agree' : 'FAIL — js and python disagree');
process.exit(pass ? 0 : 1);
