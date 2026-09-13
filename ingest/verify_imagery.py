"""
verify_imagery — is the photograph on the same grid as the coastline?

A base image is the easiest layer in the deck to get wrong and the hardest to
notice: rotate it and it is still a photograph of a polar region, still pretty,
still silently 45 degrees out. The previous build's imagery was exactly that
after the projection changed, which is why it was withdrawn.

The check uses a property of the imagery itself rather than anything it was
built from: **ocean is blue and land is not.** In Blue Marble and in MODIS true
colour the blue-minus-red difference is strongly positive over water and near
zero or negative over land. So if the image is registered to the coastline, the
mean blue-minus-red inside the land rings must be far below the mean outside
them — and rotating the coastline against the image must make that separation
worse, with the best separation at exactly zero.

Run: python3 ingest/verify_imagery.py
"""

import io
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GEO = os.environ.get("OLYMPUS_GEO", "data/geo/geo.json")
IMG = os.environ.get("OLYMPUS_IMAGERY", "data/imagery")
fails = []


def check(label, cond, detail=""):
    print(("  ok    " if cond else "  FAIL  ") + label + ("" if cond else f"  {detail}"))
    if not cond:
        fails.append(label)


def rings_of(payload, key, deg=0.0):
    th = math.radians(deg)
    c, s = math.cos(th), math.sin(th)
    out = []
    for r in payload[key]:
        pts = []
        for i in range(0, len(r), 2):
            x, y = r[i], r[i + 1]
            pts.append((x * c - y * s, x * s + y * c))
        out.append(pts)
    return out


def land_mask(rings, n, rmax):
    """Boolean mask on the image's own pixel grid."""
    m = np.zeros((n, n), dtype=bool)
    xs = (np.arange(n) + 0.5) / n * 2.0 * rmax - rmax
    ys = rmax - (np.arange(n) + 0.5) / n * 2.0 * rmax
    for ring in rings:
        arr = np.asarray(ring)
        rx, ry = arr[:, 0], arr[:, 1]
        cols = np.where((xs >= rx.min()) & (xs <= rx.max()))[0]
        rows = np.where((ys >= ry.min()) & (ys <= ry.max()))[0]
        if cols.size == 0 or rows.size == 0:
            continue
        qx, qy = np.roll(rx, 1), np.roll(ry, 1)
        for j in rows:
            yy = ys[j]
            st = (ry > yy) != (qy > yy)
            if not st.any():
                continue
            xint = rx[st] + (yy - ry[st]) * (qx[st] - rx[st]) / (qy[st] - ry[st])
            for i in cols:
                if not m[j, i] and np.count_nonzero(xint > xs[i]) % 2 == 1:
                    m[j, i] = True
    return m


def blueness(path):
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB"), dtype="float32")
    return a[:, :, 2] - a[:, :, 0]


def main():
    man = json.load(io.open(os.path.join(IMG, "manifest.json"), encoding="utf-8"))
    geo = json.load(io.open(GEO, encoding="utf-8"))
    n = man["out"]

    for rec in man["images"]:
        if rec["layer"] != "relief":
            continue          # one layer is enough; both are built by the same code
        hemi = rec["hemisphere"]
        key = "arc" if hemi == "N" else "ant"
        rmax = rec["rmax"]
        b = blueness(os.path.join(IMG, rec["file"]))
        xs = (np.arange(n) + 0.5) / n * 2.0 * rmax - rmax
        ys = rmax - (np.arange(n) + 0.5) / n * 2.0 * rmax
        inside_disc = (xs[None, :] ** 2 + ys[:, None] ** 2) <= 1.0

        print(f"\n{rec['file']}  ({rec['polar_path']})")
        print("  rotation   sea minus land, blue-red")
        best, curve = None, {}
        for deg in (-4, -2, 0, 2, 4):
            m = land_mask(rings_of(geo, key, deg), n, rmax) & inside_disc
            sea = inside_disc & ~m
            if m.sum() < 500 or sea.sum() < 500:
                continue
            sep = float(b[sea].mean() - b[m].mean())
            curve[deg] = sep
            mark = "   <- as built" if deg == 0 else ""
            print(f"  {deg:+4d} deg    {sep:8.2f}{mark}")
            if best is None or sep > best[1]:
                best = (deg, sep)

        check(f"{rec['file']}: sea reads bluer than land", curve.get(0, -1) > 4.0,
              f"separation {curve.get(0, float('nan')):.2f}")
        check(f"{rec['file']}: best alignment is at zero rotation",
              best is not None and best[0] == 0,
              f"best at {best[0] if best else '?'} deg")
        check(f"{rec['file']}: rotating by two degrees measurably degrades it",
              all(curve[d] < curve[0] - 0.25 for d in curve if d != 0),
              f"curve {[round(curve[d], 2) for d in sorted(curve)]}")

    print()
    if fails:
        print(f"{len(fails)} FAILED: " + ", ".join(fails))
        sys.exit(1)
    print("all assertions held")


if __name__ == "__main__":
    main()
