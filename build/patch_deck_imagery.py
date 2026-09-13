"""
patch_deck_imagery — put the base imagery back, on the grids the deck now draws.

Runs on a deck that has already been migrated by patch_deck_projection.py. Three
substitutions, each required:

  1. `const SATIMG = ` — the withdrawn stub replaced by the rebuilt images
  2. the `sat` layer entry — switched back on, with an honest source line
  3. the `reprojection` explainer — its closing sentence said the imagery had
     been withdrawn. It has not been withdrawn any more, so that sentence goes.

The third is not tidying. The explainer is the part the reader turns on in order
to be told the truth; leaving it describing a previous build is the failure this
project has already had once.

Usage
    python3 build/patch_deck_imagery.py --deck src/deck.html --out dist/deck.html
"""

import argparse
import base64
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SAT_OLD = ('{id:"sat",  nm:"Satellite imagery", src:"withdrawn — awaiting rebuild on '
           'EPSG:3413/3976", on:false, ex:"reprojection"},')
SAT_NEW = ('{id:"sat",  nm:"Satellite imagery", src:"NASA GIBS · EPSG:3413 native · '
           '3031→3976 south", on:true,  ex:"reprojection"},')

EXPLAIN_OLD = (' The baked imagery from the previous build was resampled into the old spherical '
               'disc and has been withdrawn rather than drawn 45° out of place.')
EXPLAIN_NEW = (' The base imagery is rebuilt on these grids: in the north it is GIBS EPSG:3413 '
               'placed by a scale and an offset, with <b>no reprojection at all</b>; in the south '
               'it is GIBS EPSG:3031 reprojected into 3976. GIBS’ polar tile matrices stop '
               'at ±4,194,304 m — <b>latitude 52.6°</b> on this frame — so the '
               'ring outside that is filled from plate carrée. <b>82 % of the drawn disc is '
               'polar-native</b>; the manifest records the figure per image rather than asserting '
               'it here.')


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")


def build_satimg(img_dir):
    man = json.load(io.open(os.path.join(img_dir, "manifest.json"), encoding="utf-8"))
    layers = {}
    for rec in man["images"]:
        L = layers.setdefault(rec["layer"], {
            "key": rec["layer"], "nm": rec["nm"], "data": {},
            "gibs": rec["gibs_layer"], "time": rec["time"],
        })
        L["data"][rec["hemisphere"]] = data_uri(os.path.join(img_dir, rec["file"]))

    # The globe cannot use either polar square: they stop at r = rmax, latitude
    # 33 N and 26 S, which on a sphere is a bare band across the tropics. It
    # draws one global plate carree sheet per layer instead, built by
    # ingest/fetch_global.py. Absent, the globe simply draws no photograph.
    gman_path = os.path.join(img_dir, "manifest_global.json")
    if os.path.exists(gman_path):
        gman = json.load(io.open(gman_path, encoding="utf-8"))
        for rec in gman["images"]:
            L = layers.get(rec["layer"])
            if not L:
                continue
            L["g"] = data_uri(os.path.join(img_dir, rec["file"]))
            L["gw"] = rec["width"]
            L["gh"] = rec["height"]
            L["gsrc"] = {"projection": rec["projection"], "time": rec["time"],
                         "bytes": rec["bytes"], "source": rec["source"]}
    else:
        print("  no manifest_global.json — the globe will draw no imagery")

    order = ["relief", "today"]
    return {
        "built": man["generated_utc"],
        "day": man["day"],
        "out": man["out"],
        "rmax": man["rmax"],
        "note": man["note"],
        "layers": [layers[k] for k in order if k in layers],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default=os.path.join(ROOT, "src", "deck.html"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "deck.html"))
    ap.add_argument("--imagery", default=os.path.join(ROOT, "data", "imagery"))
    args = ap.parse_args()

    src = io.open(args.deck, encoding="utf-8").read()
    print(f"in  {args.deck}  {len(src)/1024/1024:.2f} MB")

    pat = re.compile(r"^const SATIMG = .*?;\s*$", re.M)
    hits = list(pat.finditer(src))
    if len(hits) != 1:
        raise SystemExit(f"expected one SATIMG declaration, found {len(hits)}")
    sat = build_satimg(args.imagery)
    sj = json.dumps(sat, separators=(",", ":"))
    m = hits[0]
    src = src[:m.start()] + f"const SATIMG = {sj};" + src[m.end():]
    print(f"  SATIMG: {(m.end()-m.start())/1024:.0f} KB -> {len(sj)/1024/1024:.2f} MB "
          f"({len(sat['layers'])} layers x 2 hemispheres)")

    for label, old, new in (("sat layer", SAT_OLD, SAT_NEW),
                            ("reprojection explainer", EXPLAIN_OLD, EXPLAIN_NEW)):
        if src.count(old) != 1:
            raise SystemExit(f"{label}: expected one match, found {src.count(old)}")
        src = src.replace(old, new)
        print(f"  {label}: updated")

    for stale in ("awaiting rebuild", "has been withdrawn rather than drawn"):
        if stale in src:
            raise SystemExit(f"the page still says the imagery is withdrawn: {stale}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        f.write(src)
    size = os.path.getsize(args.out)
    print(f"out {args.out}  {size/1024/1024:.2f} MB")
    if size > 16 * 1024 * 1024:
        print("WARNING: over the 16 MB artifact ceiling", file=sys.stderr)


if __name__ == "__main__":
    main()
