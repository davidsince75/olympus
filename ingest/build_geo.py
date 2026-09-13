"""
build_geo — coastlines, ice shelves and northern land, projected the way the
data is projected.

Why this exists, twice
----------------------
This script was written once before, produced the 10 m geometry the expansion
plan records as A1 "done", and was then lost with its container. The geometry
never reached `src/deck.html`, which still carries the **50 m** set: 853 points
for all of Antarctica and 3,414 for the Arctic. So A1 was not done; it was done
and lost, which is not the same thing.

It is rewritten here against `olympus_proj`, so that for the first time the
coastline, the stations and the measured ice field are all placed by the same
projection — the ellipsoidal polar stereographic the data is actually published
on, not the spherical disc the deck has been drawing.

The unit-disc contract
----------------------
The deck draws everything in a unit disc: `proj(lon,lat) -> [x,y]` with r = 1 at
latitude +/-45, then `px = cx + x*s, py = cy - y*s`. That contract is kept —
seventeen call sites depend on it — and only the projection underneath changes.
So this script emits the same shape of payload the deck already consumes, with
every coordinate now the true ellipsoidal position divided by the projected
radius of the 45th parallel.

One consequence worth stating plainly: **EPSG:3413 has a central meridian of
-45 degrees**, where the old spherical disc effectively used 0. The Arctic map
therefore rotates by 45 degrees. Everything drawn through `proj()` rotates with
it; anything positioned by a hard-coded screen coordinate does not, and must be
checked.

Output
    data/geo/geo.json    {"ant":[ring,...], "shelf":[...], "arc":[...], "meta":{...}}
    where a ring is a flat [x0,y0,x1,y1,...] list, 4 decimal places, the format
    `const GEO=` in the deck already uses.

Usage
    python3 ingest/build_geo.py
    python3 ingest/build_geo.py --tolerance-ant 900 --tolerance-arc 1200
"""

import argparse
import hashlib
import io
import json
import math
import os
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olympus_proj import GRIDS  # noqa: E402

NE = "https://naciscdn.org/naturalearth/10m/physical"
LAYERS = {
    "land": f"{NE}/ne_10m_land.zip",
    "shelves": f"{NE}/ne_10m_antarctic_ice_shelves_polys.zip",
}
USER_AGENT = "olympus-geo-ingest/2.0 (+build-time ingest, no runtime fetch)"

# The normalising parallel. Kept at 45 because the deck's framing, zoom limits
# and label placement are all calibrated to it; changing the projection is
# already enough change for one build.
NORM_LAT = 45.0

# Which projection each hemisphere is drawn in, and why:
#   north  EPSG:3413  — the grid ASI AMSR2 publishes on, and the grid NASA GIBS
#                       publishes Arctic tiles on. One grid, no resampling.
#   south  EPSG:3976  — the grid ASI AMSR2 publishes on. NOT 3031, which GIBS
#                       uses for Antarctic tiles and which sits 6.6 km away at
#                       70 S. The measured field keeps its own grid; imagery is
#                       resampled into it, never the other way round.
HEMI = {
    "north": {"epsg": 3413, "sign": 1},
    "south": {"epsg": 3976, "sign": -1},
}


# ---------------------------------------------------------------- fetching

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
        last_modified = r.headers.get("Last-Modified")
    return body, {
        "url": url,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "http_last_modified": last_modified,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def read_shapes(zip_bytes):
    """Every polygon part in a Natural Earth zip, as lists of (lon, lat)."""
    import shapefile

    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    base = next(n[:-4] for n in zf.namelist() if n.endswith(".shp"))
    rdr = shapefile.Reader(
        shp=io.BytesIO(zf.read(base + ".shp")),
        dbf=io.BytesIO(zf.read(base + ".dbf")),
        shx=io.BytesIO(zf.read(base + ".shx")),
    )
    out = []
    for shp in rdr.shapes():
        pts = shp.points
        parts = list(shp.parts) + [len(pts)]
        for a, b in zip(parts, parts[1:]):
            if b - a >= 4:
                out.append([(float(x), float(y)) for x, y in pts[a:b]])
    return out


# ---------------------------------------------------------------- geometry

def unit_projector(epsg):
    """lon/lat -> unit disc, r = 1 at NORM_LAT, through the real projection."""
    p = GRIDS[epsg]
    lat_norm = NORM_LAT if p.north else -NORM_LAT
    rn = math.hypot(*p.forward(lat_norm, p.lon0))
    if rn <= 0:
        raise SystemExit("normalising radius came out zero")

    def f(lon, lat):
        x, y = p.forward(lat, lon)
        return (x / rn, y / rn)

    return f, rn


def clip_to_disc(ring, sides=512):
    """Sutherland-Hodgman against the unit circle, as a regular polygon.

    A rectangular clip would draw a box across the hemisphere where a landmass
    leaves the frame — which is exactly what the previous build had to fix.
    """
    poly = ring
    for k in range(sides):
        a = 2.0 * math.pi * k / sides
        nx, ny = math.cos(a), math.sin(a)          # outward normal
        d = math.cos(math.pi / sides)              # inscribed-polygon offset
        out = []
        n = len(poly)
        if n == 0:
            return []
        for i in range(n):
            cx, cy = poly[i]
            px, py = poly[i - 1]
            ci = cx * nx + cy * ny - d             # <= 0 is inside
            pi = px * nx + py * ny - d
            if ci <= 0:
                if pi > 0:
                    t = pi / (pi - ci)
                    out.append((px + (cx - px) * t, py + (cy - py) * t))
                out.append((cx, cy))
            elif pi <= 0:
                t = pi / (pi - ci)
                out.append((px + (cx - px) * t, py + (cy - py) * t))
        poly = out
    return poly


def rdp(points, eps):
    """Douglas-Peucker, iterative, in PROJECTED space.

    Simplifying in lon/lat would apply a tolerance that means something
    different at every latitude — tight at the equator, absurdly loose at 85
    degrees, which is where all of this geometry lives. In projected metres the
    tolerance is uniform in what the reader actually sees.
    """
    n = len(points)
    if n < 3:
        return list(points)
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack = [(0, n - 1)]
    while stack:
        a, b = stack.pop()
        if b <= a + 1:
            continue
        ax, ay = points[a]
        bx, by = points[b]
        dx, dy = bx - ax, by - ay
        den = math.hypot(dx, dy)
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            px, py = points[i]
            if den < 1e-15:
                d = math.hypot(px - ax, py - ay)
            else:
                d = abs(dy * px - dx * py + bx * ay - by * ax) / den
            if d > best:
                best, bi = d, i
        if best > eps:
            keep[bi] = True
            stack.append((a, bi))
            stack.append((bi, b))
    return [points[i] for i in range(n) if keep[i]]


def signed_area(ring):
    s = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i - 1]
        x1, y1 = ring[i]
        s += x0 * y1 - x1 * y0
    return s / 2.0


def build(shapes, epsg, lat_filter, tol_m, min_area_unit, rn):
    """Project, clip, simplify, and drop what is too small to draw."""
    f, _ = unit_projector(epsg)
    tol_unit = tol_m / rn
    rings = []
    for pts in shapes:
        if not any(lat_filter(lat) for _, lat in pts):
            continue
        proj = [f(lon, lat) for lon, lat in pts]
        # Drop the antimeridian seam artefacts Natural Earth carries as
        # straight runs; the disc clip handles the rest.
        clipped = clip_to_disc(proj)
        if len(clipped) < 4:
            continue
        simp = rdp(clipped, tol_unit)
        if len(simp) < 4:
            continue
        if abs(signed_area(simp)) < min_area_unit:
            continue
        rings.append(simp)
    rings.sort(key=lambda r: -abs(signed_area(r)))
    return rings


def flatten(rings, dp=4):
    out = []
    for r in rings:
        flat = []
        for x, y in r:
            flat.append(round(x, dp))
            flat.append(round(y, dp))
        out.append(flat)
    return out


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/geo/geo.json")
    ap.add_argument("--tolerance-ant", type=float, default=900.0,
                    help="Douglas-Peucker tolerance in metres, Antarctic land")
    ap.add_argument("--tolerance-shelf", type=float, default=900.0)
    ap.add_argument("--tolerance-arc", type=float, default=1200.0)
    args = ap.parse_args()

    print("fetching Natural Earth 10 m")
    sources = {}
    raw = {}
    for key, url in LAYERS.items():
        body, stamp = fetch(url)
        raw[key] = body
        sources[key] = stamp
        print(f"  {key}: {stamp['bytes']/1024/1024:.2f} MB  sha256 {stamp['sha256'][:16]}…")

    land = read_shapes(raw["land"])
    shelves = read_shapes(raw["shelves"])
    print(f"  land parts {len(land)}, shelf parts {len(shelves)}")

    _, rn_n = unit_projector(3413)
    _, rn_s = unit_projector(3976)
    print(f"normalising radius: north {rn_n/1000:.1f} km, south {rn_s/1000:.1f} km  (lat {NORM_LAT})")

    # A ring smaller than about a pixel at full extent is not geometry, it is noise.
    min_area = (2.0 / 900.0) ** 2 * 2.0

    print("projecting")
    ant = build(land, 3976, lambda la: la < -55, args.tolerance_ant, min_area, rn_s)
    shelf = build(shelves, 3976, lambda la: la < -55, args.tolerance_shelf, min_area, rn_s)
    arc = build(land, 3413, lambda la: la > 40, args.tolerance_arc, min_area, rn_n)

    payload = {
        "ant": flatten(ant),
        "shelf": flatten(shelf),
        "arc": flatten(arc),
        "meta": {
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source": "Natural Earth 10 m physical, public domain",
            "sources": sources,
            "projection": {
                "north": {"epsg": 3413, "normalising_latitude": NORM_LAT,
                          "normalising_radius_m": rn_n},
                "south": {"epsg": 3976, "normalising_latitude": -NORM_LAT,
                          "normalising_radius_m": rn_s},
            },
            "note": (
                "Unit disc: r = 1 at the normalising parallel. EPSG:3413 has central "
                "meridian -45, so the Arctic is rotated 45 degrees relative to the "
                "spherical disc this replaces. The southern grid is 3976, not 3031."
            ),
            "simplification": {
                "method": "Douglas-Peucker in projected metres",
                "tolerance_m": {"ant": args.tolerance_ant,
                                "shelf": args.tolerance_shelf,
                                "arc": args.tolerance_arc},
            },
            "clip": "Sutherland-Hodgman against a 512-gon inscribed in the unit circle",
        },
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))

    def count(rings):
        return sum(len(r) for r in rings) // 2

    print("\n            rings   points")
    for key in ("ant", "shelf", "arc"):
        print(f"  {key:<8} {len(payload[key]):>5} {count(payload[key]):>8}")
    print(f"\n{args.out}  {os.path.getsize(args.out)/1024:.0f} KB")
    print("  was (50 m, in src/deck.html): ant 853, shelf 677, arc 3414 points")


if __name__ == "__main__":
    main()
