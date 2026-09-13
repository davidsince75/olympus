"""
patch_deck_projection — move the deck onto the real projection.

Three substitutions into `src/deck.html`, in one pass, each anchored on text
that must be present exactly once:

  1. the projection block   spherical disc  ->  ellipsoidal EPSG:3413 / EPSG:3976
  2. `const GEO=`           50 m coastline  ->  10 m, rebuilt on the new grids
  3. `const OSI=`           the 220-cell ice field, re-binned through the new
                            projection by ingest/ingest_osisaf.py

They are one change, not three. The field is forward-binned onto the disc at
ingest time, so a projection that moves without the field moving is a deck whose
coastline no longer sits where its ice does — by 0.2 % radially everywhere and
by 45 degrees of rotation in the Arctic, because EPSG:3413's central meridian is
-45 where the old spherical disc effectively used 0.

What is deliberately NOT changed: the unit-disc contract. `proj(lon,lat,S)`
still returns [x,y] with r = 1 at +-45 degrees and the caller still does
`cx + x*s, cy - y*s`. Seventeen call sites depend on that and none of them needs
to know the projection changed underneath.

Usage
    python3 build/patch_deck_projection.py \
        --deck src/deck.html --out dist/deck.html
"""

import argparse
import base64
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NEW_PROJ = r'''const RE=6371.0088;
const D=Math.PI/180;

/* ---------------- projection ----------------
   Ellipsoidal polar stereographic on WGS-84 — the grid the data is actually
   published on, not a spherical stand-in for it.

     north  EPSG:3413   standard parallel +70, central meridian -45
     south  EPSG:3976   standard parallel -70, central meridian   0

   Normalised so r = 1 at +-45 degrees, which is the contract the rest of this
   file is written against. Mirrors ingest/olympus_proj.{py,js} exactly: the
   same formulas placed every ice cell, every coastline vertex and every station
   at ingest time, so nothing here can drift away from where the data was put.

   EPSG:3976 is the southern grid, not EPSG:3031. They differ by 6.6 km at 70 S.
   3976 is what the measured field is published on; GIBS imagery, which is on
   3031, is resampled into it rather than the other way round.
*/
const WGS_A=6378137.0;
const WGS_F=1/298.257223563;
const WGS_E=Math.sqrt(2*WGS_F-WGS_F*WGS_F);
function psT(phi){
  const s=Math.sin(phi);
  return Math.tan(Math.PI/4-phi/2)/Math.pow((1-WGS_E*s)/(1+WGS_E*s),WGS_E/2);
}
const PS=(function(){
  const mk=(latTs,lon0,north)=>{
    const phic=Math.abs(latTs)*Math.PI/180;
    const mc=Math.cos(phic)/Math.sqrt(1-WGS_E*WGS_E*Math.sin(phic)*Math.sin(phic));
    const tc=psT(phic);
    const rn=WGS_A*mc*psT(45*Math.PI/180)/tc;   // radius of the 45th parallel
    return {latTs:latTs,lon0:lon0,north:north,mc:mc,tc:tc,rn:rn};
  };
  return {N:mk(70,-45,true), S:mk(-70,0,false)};
})();
function psFor(S){ return S?PS.S:PS.N; }

function proj(lon,lat,S){ // S=true -> south polar
  const p=psFor(S);
  const phi=Math.abs(lat)*D, lam=(lon-p.lon0)*D;
  const r=(phi>=Math.PI/2-1e-12)?0:(WGS_A*p.mc*psT(phi)/p.tc)/p.rn;
  return [r*Math.sin(lam), (p.north?-1:1)*r*Math.cos(lam)];
}
function invLat(r,S){
  const p=psFor(S);
  if(r<1e-12) return p.north?90:-90;
  const t=(r*p.rn)*p.tc/(WGS_A*p.mc);
  let phi=Math.PI/2-2*Math.atan(t);
  for(let i=0;i<32;i++){
    const s=Math.sin(phi);
    const nx=Math.PI/2-2*Math.atan(t*Math.pow((1-WGS_E*s)/(1+WGS_E*s),WGS_E/2));
    if(Math.abs(nx-phi)<1e-13){ phi=nx; break; }
    phi=nx;
  }
  return (phi/D)*(p.north?1:-1);
}
function invLon(x,y,S){
  const p=psFor(S);
  const lam=Math.atan2(x, p.north?-y:y);
  let lon=lam/D+p.lon0;
  lon=((lon+180)%360+360)%360-180;
  return lon;
}
// true ground area, km^2, per unit of map area at disc radius r. A polar
// stereographic grid is conformal, not equal-area: k = 1 only at the standard
// parallel, so this is the scale factor doing its job rather than a constant.
function areaW(r,S){
  const p=psFor(S===undefined?true:S);
  const lat=invLat(r<1e-4?1e-4:r,p===PS.S);
  const phi=Math.abs(lat)*D;
  const m=Math.cos(phi)/Math.sqrt(1-WGS_E*WGS_E*Math.sin(phi)*Math.sin(phi));
  const rho=WGS_A*p.mc*psT(phi)/p.tc;
  const k=rho/(WGS_A*m);
  return (p.rn/1000)*(p.rn/1000)/(k*k);
}'''

OLD_PROJ_START = "const R0=Math.tan(Math.PI/4-45*Math.PI/360);"
OLD_PROJ_END = "  return 2*RE*RE*Math.cos(chi)*c*c*R0/r;\n}"



# ---------------------------------------------------------------- honesty pass
#
# A projection change that leaves the page describing the old projection is the
# failure the learning-layer audit already caught once: the explainer is the part
# the reader turned on in order to be told the truth, so a stale one does not go
# quietly out of date — it lies with authority.

READOUT_OLD = """    : st.mode==="PAIR" ? "EASE2 25 km \u2192 TWIN POLAR DISCS \u00b7 TRUE AT \u00b145\u00b0"
    : st.S ? "EASE2 25 km \u2192 POLAR STEREOGRAPHIC DISC \u00b7 TRUE AT 45\u00b0S"
           : "EASE2 25 km \u2192 POLAR STEREOGRAPHIC DISC \u00b7 TRUE AT 45\u00b0N";"""

READOUT_NEW = """    : st.mode==="PAIR" ? "EASE2 25 km \u2192 EPSG:3413 / EPSG:3976 \u00b7 FRAMED TO \u00b145\u00b0"
    : st.S ? "EASE2 25 km \u2192 EPSG:3976 \u00b7 WGS-84 \u00b7 SP 70\u00b0S \u00b7 FRAMED TO 45\u00b0S"
           : "EASE2 25 km \u2192 EPSG:3413 \u00b7 WGS-84 \u00b7 SP 70\u00b0N \u00b7 FRAMED TO 45\u00b0N";"""

EXPLAIN_OLD = ('b:"GIBS publishes polar imagery in EPSG:3413 and EPSG:3031. This deck does not '
               'draw either of them')

EXPLAIN_NEW_BODY = (
    'b:"This deck now draws the grids the data is published on: <b>EPSG:3413</b> in the north '
    'and <b>EPSG:3976</b> in the south \u2014 ellipsoidal polar stereographic on WGS-84, '
    'standard parallel 70\u00b0, framed so that \u00b145\u00b0 sits at the rim of the disc. '
    'The ice field is forward-binned onto that disc at ingest through the same formulas that '
    'place the coastline and the stations, so registration is by construction rather than by '
    'coincidence. GIBS publishes Arctic tiles on EPSG:3413 \u2014 the same grid, no resampling '
    'needed \u2014 but its Antarctic tiles are on <b>EPSG:3031</b>, which is <i>not</i> 3976: '
    'the standard parallels differ by one degree, which is <b>6.6 km at 70\u00b0S</b>. The '
    'measured field keeps its own grid and imagery is resampled into it, never the other way '
    'round. The baked imagery from the previous build was resampled into the old spherical disc '
    'and has been withdrawn rather than drawn 45\u00b0 out of place.",\n'
    ' p:"ingest/olympus_proj.py and ingest/olympus_proj.js \u2014 verified against pyproj, and '
    'against each other, before anything was drawn with them."},'
)

SAT_LAYER_OLD = ('{id:"sat",  nm:"Satellite imagery", src:"NASA GIBS \u00b7 reprojected at build", '
                 'on:true,  ex:"reprojection"},')
SAT_LAYER_NEW = ('{id:"sat",  nm:"Satellite imagery", src:"withdrawn \u2014 awaiting rebuild on '
                 'EPSG:3413/3976", on:false, ex:"reprojection"},')

SHELF_LAYER_OLD = ('src:"Natural Earth 50m \u00b7 BAS ADD"')
SHELF_LAYER_NEW = ('src:"Natural Earth 10 m \u00b7 projected on the data\u2019s own grid"')

# The shelf explainer names its own geometry, and that sentence stopped being
# true the moment the 10 m set went in.
SHELF_PROV_OLD = 'p:"Geometry: Natural Earth 50m and the BAS Antarctic Digital Database."'
SHELF_PROV_NEW = ('p:"Geometry: Natural Earth 10 m ice-shelf polygons, 5,542 points, projected '
                  'on EPSG:3976 by ingest/build_geo.py. The grounding line is not drawn from a '
                  'measured product and is not claimed as one."')


def honesty_pass(src):
    """Every substitution here is mandatory; a miss means the page now misdescribes itself."""
    out = src
    steps = [
        ("projection readout", READOUT_OLD, READOUT_NEW),
        ("imagery layer", SAT_LAYER_OLD, SAT_LAYER_NEW),
        ("shelf layer source", SHELF_LAYER_OLD, SHELF_LAYER_NEW),
        ("shelf explainer provenance", SHELF_PROV_OLD, SHELF_PROV_NEW),
    ]
    for label, old, new in steps:
        if out.count(old) != 1:
            raise SystemExit(f"honesty pass, {label}: expected one match, found {out.count(old)}")
        out = out.replace(old, new)
        print(f"  {label}: updated")

    # The explainer body runs to the end of its entry; replace from its start to
    # the closing of the entry.
    i = out.find(EXPLAIN_OLD)
    if i < 0:
        raise SystemExit("honesty pass, reprojection explainer: anchor not found")
    j = out.find("},", out.find(' p:"', i))
    if j < 0:
        raise SystemExit("honesty pass, reprojection explainer: end of entry not found")
    out = out[:i] + EXPLAIN_NEW_BODY + out[j + 2:]
    print("  reprojection explainer: rewritten")

    # The baked imagery was resampled into the OLD disc. Withdraw it rather than
    # draw it 45 degrees out; the guard at its call site already handles an empty
    # layer list. This also returns roughly 850 KB of payload.
    pat = re.compile(r"^const SATIMG = .*?;\s*$", re.M)
    hits = list(pat.finditer(out))
    if len(hits) != 1:
        raise SystemExit(f"honesty pass, SATIMG: found {len(hits)} declarations")
    m = hits[0]
    withdrawn = json.dumps({
        "withdrawn": ("resampled into the spherical disc this build replaced; it would sit 45 "
                      "degrees out in the north. Rebuild on EPSG:3413 (GIBS native, no "
                      "resampling) and EPSG:3976 (resampled from 3031)."),
        "layers": [],
    }, separators=(",", ":"))
    out = out[:m.start()] + f"const SATIMG = {withdrawn};" + out[m.end():]
    print(f"  baked imagery: withdrawn ({(m.end() - m.start())/1024/1024:.2f} MB removed)")
    return out


def replace_once(text, start_marker, end_marker, new, label):
    i = text.find(start_marker)
    if i < 0:
        raise SystemExit(f"{label}: start anchor not found")
    if text.find(start_marker, i + 1) >= 0:
        raise SystemExit(f"{label}: start anchor is not unique")
    j = text.find(end_marker, i)
    if j < 0:
        raise SystemExit(f"{label}: end anchor not found after the start")
    j += len(end_marker)
    return text[:i] + new + text[j:], (j - i)


def replace_const(text, name, value_json, label):
    """Replace `const NAME={...};` where the value runs to the end of its line."""
    pat = re.compile(r"^const " + name + r"=.*?;\s*$", re.M)
    hits = list(pat.finditer(text))
    if len(hits) != 1:
        raise SystemExit(f"{label}: expected one `const {name}=` line, found {len(hits)}")
    m = hits[0]
    return text[:m.start()] + f"const {name}={value_json};" + text[m.end():], (m.end() - m.start())


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")


def build_osi(osi_dir):
    """Assemble the deck's OSI payload from the two ingest manifests."""
    out = None
    for hemi in ("sh", "nh"):
        mp = os.path.join(osi_dir, f"manifest_{hemi}.json")
        man = json.load(io.open(mp, encoding="utf-8"))
        if out is None:
            out = {"ng": man["ng"], "per": man["per"], "levels": man["levels"], "hemi": {}}
        out["hemi"][hemi] = {
            "n": man["n"],
            "m0": man["m0"],
            "epsg": man["epsg"],
            "sheets": [data_uri(os.path.join(osi_dir, s)) for s in man["sheets"]],
            "ymo": man["ymo"],
            "ext": man["ext"],
            "runs": man["runs"],
            "clim": man["clim"],
            "file0": man["file0"],
            "fileN": man["fileN"],
        }
    return out


def build_geo(geo_path):
    g = json.load(io.open(geo_path, encoding="utf-8"))
    return {"ant": g["ant"], "shelf": g["shelf"], "arc": g["arc"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default=os.path.join(ROOT, "src", "deck.html"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "deck.html"))
    ap.add_argument("--geo", default=os.path.join(ROOT, "data", "geo", "geo.json"))
    ap.add_argument("--osi", default=os.path.join(ROOT, "data", "osi"))
    args = ap.parse_args()

    src = io.open(args.deck, encoding="utf-8").read()
    print(f"in  {args.deck}  {len(src)/1024/1024:.2f} MB")

    src, n1 = replace_once(src, OLD_PROJ_START, OLD_PROJ_END, NEW_PROJ, "projection block")
    print(f"  projection block: {n1} chars -> {len(NEW_PROJ)}")

    geo = build_geo(args.geo)
    gj = json.dumps(geo, separators=(",", ":"))
    src, n2 = replace_const(src, "GEO", gj, "GEO")
    print(f"  GEO: {n2/1024:.0f} KB -> {len(gj)/1024:.0f} KB  "
          f"(ant {len(geo['ant'])} rings, shelf {len(geo['shelf'])}, arc {len(geo['arc'])})")

    osi = build_osi(args.osi)
    oj = json.dumps(osi, separators=(",", ":"))
    src, n3 = replace_const(src, "OSI", oj, "OSI")
    print(f"  OSI: {n3/1024/1024:.2f} MB -> {len(oj)/1024/1024:.2f} MB  "
          f"(nh {osi['hemi']['nh']['n']} frames, sh {osi['hemi']['sh']['n']})")

    src = honesty_pass(src)

    # A projection swap that leaves the old normalising constant behind is a
    # projection swap that did not happen.
    for stale in ("R0=Math.tan", "Math.tan(Math.PI/4+lat*D/2)",
                  "POLAR STEREOGRAPHIC DISC", "Natural Earth 50m"):
        if stale in src:
            raise SystemExit(f"stale spherical projection code still present: {stale}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        f.write(src)
    print(f"out {args.out}  {os.path.getsize(args.out)/1024/1024:.2f} MB")
    if os.path.getsize(args.out) > 16 * 1024 * 1024:
        print("WARNING: over the 16 MB artifact ceiling", file=sys.stderr)


if __name__ == "__main__":
    main()
