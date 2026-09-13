"""
verify_registration — does the ice sit on the ocean?

The failure this exists to catch
--------------------------------
The deck's ice field is binned onto the unit disc through the deck's projection,
and the coastline is stored pre-projected through the same one. Change the
projection in one and not the other and the picture still looks like a polar
map: ice, coastline, stations, all drawn, nothing throwing an error. It is just
wrong, by 45 degrees in the Arctic.

No structural probe catches that, because nothing is structurally broken. What
catches it is a physical fact: **sea ice is not on land.** If a field and a
coastline are registered to each other, almost no ice cell falls inside a
landmass. If they are not, a great many do.

So the test is a percentage, run on four combinations, and it is only meaningful
because the wrong ones are included:

    old field + old geometry     the published deck — the baseline
    new field + new geometry     the patched deck — must be no worse
    new field + old geometry     deliberately mismatched — must be far worse
    old field + new geometry     deliberately mismatched — must be far worse

A test that only ever sees the correct case cannot tell you it is correct.

The absolute percentage is not comparable between coastline datasets
--------------------------------------------------------------------
At 220 cells across a hemisphere each cell is about 45 km, so any cell straddling
a coast counts as both. Natural Earth 10 m resolves more coast than the 50 m set
the deck used to carry, so it legitimately reads a point or two higher on the
same, correctly registered field. Comparing the two numbers directly would
therefore fail a build that is right.

What is comparable is the SHAPE of the curve. Rotate the coastline against the
field and the ice-on-land percentage must be at its minimum at exactly zero. A
two-degree error is visible; a forty-five degree one is unmissable. That is the
assertion.

Usage
    python3 ingest/verify_registration.py --deck src/deck.html
"""

import argparse
import base64
import io
import json
import math
import os
import re
import sys

import numpy as np

NG = 220
PER = 100
THRESHOLD = 15

fails = []


def check(label, cond, detail=""):
    print(("  ok    " if cond else "  FAIL  ") + label + ("" if cond else f"  {detail}"))
    if not cond:
        fails.append(label)


def decode_sheet(uri):
    from PIL import Image
    raw = base64.b64decode(uri.split(",", 1)[1])
    return np.asarray(Image.open(io.BytesIO(raw)).convert("L"), dtype=np.uint8)


def frame_from_sheets(sheets, k):
    sh, f = k // PER, k % PER
    atlas = decode_sheet(sheets[sh])
    gr, gc = f // 10, f % 10
    return atlas[gr * NG:(gr + 1) * NG, gc * NG:(gc + 1) * NG]


def rings_of(payload, key):
    return [[(r[i], r[i + 1]) for i in range(0, len(r), 2)] for r in payload[key]]


def land_mask(rings):
    """One boolean per disc cell: is this cell's centre inside any land ring?"""
    m = np.zeros((NG, NG), dtype=bool)
    xs = (np.arange(NG) + 0.5) / NG * 2.0 - 1.0
    ys = 1.0 - (np.arange(NG) + 0.5) / NG * 2.0
    for ring in rings:
        arr = np.asarray(ring)
        rx, ry = arr[:, 0], arr[:, 1]
        x0, x1 = rx.min(), rx.max()
        y0, y1 = ry.min(), ry.max()
        cols = np.where((xs >= x0) & (xs <= x1))[0]
        rows = np.where((ys >= y0) & (ys <= y1))[0]
        if cols.size == 0 or rows.size == 0:
            continue
        px = rx
        py = ry
        qx = np.roll(px, 1)
        qy = np.roll(py, 1)
        for j in rows:
            yy = ys[j]
            straddle = (py > yy) != (qy > yy)
            if not straddle.any():
                continue
            a_x = px[straddle]
            a_y = py[straddle]
            b_x = qx[straddle]
            b_y = qy[straddle]
            xint = a_x + (yy - a_y) * (b_x - a_x) / (b_y - a_y)
            for i in cols:
                if m[j, i]:
                    continue
                if np.count_nonzero(xint > xs[i]) % 2 == 1:
                    m[j, i] = True
    return m


def rotated_mask(geo, key, deg):
    """The land mask with the coastline turned by `deg` degrees about the pole."""
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    rr = []
    for r in geo[key]:
        pts = []
        for i in range(0, len(r), 2):
            x, y = r[i], r[i + 1]
            pts.append(x * c - y * s)
            pts.append(x * s + y * c)
        rr.append(pts)
    return land_mask(rings_of({key: rr}, key))


def ice_on_land(field, mask):
    ice = field >= THRESHOLD
    n = int(ice.sum())
    if n == 0:
        return 0.0, 0
    return float((ice & mask).sum()) / n * 100.0, n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default="src/deck.html", help="the PUBLISHED deck, for the old payload")
    ap.add_argument("--geo", default="data/geo/geo.json")
    ap.add_argument("--osi", default="data/osi")
    ap.add_argument("--hemisphere", default="nh")
    ap.add_argument("--frame", type=int, default=None,
                    help="frame index; default is the last one")
    args = ap.parse_args()

    hemi = args.hemisphere
    src = io.open(args.deck, encoding="utf-8").read()

    old_osi = json.loads(re.search(r"const OSI=(\{.*?\});\n", src, re.S).group(1))
    old_geo = json.loads(re.search(r"const GEO=(\{.*?\});\n", src, re.S).group(1))
    new_geo = json.load(io.open(args.geo, encoding="utf-8"))
    man = json.load(io.open(os.path.join(args.osi, f"manifest_{hemi}.json"), encoding="utf-8"))

    k = args.frame if args.frame is not None else man["n"] - 1
    y0 = int(man["m0"][:4]) * 12 + int(man["m0"][4:]) - 1
    t = y0 + man["ymo"][k]
    ym = f"{t // 12}-{t % 12 + 1:02d}"
    print(f"{hemi} frame {k} = {ym}")

    old_field = frame_from_sheets(old_osi["hemi"][hemi]["sheets"], k)
    from PIL import Image
    sheet_path = os.path.join(args.osi, man["sheets"][k // PER])
    atlas = np.asarray(Image.open(sheet_path).convert("L"), dtype=np.uint8)
    f = k % PER
    gr, gc = f // 10, f % 10
    new_field = atlas[gr * NG:(gr + 1) * NG, gc * NG:(gc + 1) * NG]

    key = "ant" if hemi == "sh" else "arc"
    print("  building land masks…")
    old_mask = land_mask(rings_of(old_geo, key))
    new_mask = land_mask(rings_of(new_geo, key))
    print(f"  land cells: old geometry {int(old_mask.sum())}, new {int(new_mask.sum())}")

    combos = {
        "old field + old geometry  (the published deck)": (old_field, old_mask),
        "new field + new geometry  (the patched deck)": (new_field, new_mask),
        "new field + OLD geometry  (deliberately mismatched)": (new_field, old_mask),
        "old field + NEW geometry  (deliberately mismatched)": (old_field, new_mask),
    }
    res = {}
    print("\n  combination                                            ice on land   ice cells")
    for label, (fld, msk) in combos.items():
        pct, n = ice_on_land(fld, msk)
        res[label] = pct
        print(f"  {label:<52}  {pct:8.2f} %   {n:>7}")

    baseline = res["old field + old geometry  (the published deck)"]
    patched = res["new field + new geometry  (the patched deck)"]
    mis1 = res["new field + OLD geometry  (deliberately mismatched)"]
    mis2 = res["old field + NEW geometry  (deliberately mismatched)"]

    print("\n  rotating the coastline against the field (the registration test)")
    print("  rotation   published deck   patched deck")
    curve = {}
    for deg in (-4, -2, 0, 2, 4):
        a = ice_on_land(old_field, rotated_mask(old_geo, key, deg))[0]
        b = ice_on_land(new_field, rotated_mask(new_geo, key, deg))[0]
        curve[deg] = (a, b)
        mark = "   <- correct pairing" if deg == 0 else ""
        print(f"  {deg:+4d} deg    {a:8.2f} %      {b:8.2f} %{mark}")

    # The margins are RELATIVE, because the two hemispheres live at different
    # scales: Antarctica is a continent ringed by open ocean, so almost no sea
    # ice falls on land there under any rotation, and an absolute threshold
    # calibrated on the Arctic would fail a correct southern build.
    def climbs(c, i):
        return (c[-2][i] > c[0][i] * 1.3 and c[2][i] > c[0][i] * 1.3
                and c[-4][i] > c[0][i] * 1.5 and c[4][i] > c[0][i] * 1.5)

    print()
    check("the patched deck's registration is minimised at zero rotation",
          climbs(curve, 1), f"curve {[round(curve[d][1], 2) for d in sorted(curve)]}")
    check("so is the published deck's, which is what makes the test meaningful",
          climbs(curve, 0), f"curve {[round(curve[d][0], 2) for d in sorted(curve)]}")
    check("little ice sits on land in the patched deck",
          patched < 10.0, f"{patched:.2f} %")

    # The four-way table above is printed as context, not asserted on. In the
    # south it cannot discriminate: EPSG:3976 and the old spherical disc share a
    # central meridian, so the southern geometry barely moves and a "mismatched"
    # pairing is not in fact mismatched. The rotation sweep is the assertion
    # because it is a controlled perturbation of a known size.
    if max(mis1, mis2) > max(baseline, patched) + 8.0:
        print(f"  note  a mismatched pairing reads {max(mis1, mis2):.1f} % against "
              f"{patched:.1f} % — the projection change is large in this hemisphere")
    else:
        print(f"  note  mismatched and correct pairings read alike here "
              f"({mis1:.2f} / {mis2:.2f} vs {baseline:.2f} / {patched:.2f} %): this "
              f"hemisphere's projection barely moved, which is expected in the south")

    print()
    if fails:
        print(f"{len(fails)} FAILED: " + ", ".join(fails))
        sys.exit(1)
    print("all assertions held")


if __name__ == "__main__":
    main()
