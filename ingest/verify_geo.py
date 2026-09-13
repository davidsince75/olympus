"""
verify_geo — assert the rebuilt geometry before it goes anywhere near the deck.

A coastline is the one layer whose errors are invisible: it is drawn, it looks
like a coastline, and nothing complains if it is rotated, mirrored, on the wrong
ellipsoid or clipped to a box. So it is checked against things that are true
independently of the file.

Run: python3 ingest/verify_geo.py
Exit code 0 = every assertion held.
"""

import io
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olympus_proj import GRIDS  # noqa: E402

GEO_PATH = os.environ.get("OLYMPUS_GEO", "data/geo/geo.json")
NORM_LAT = 45.0

fails = []


def check(label, cond, detail=""):
    print(("  ok    " if cond else "  FAIL  ") + label + ("" if cond else f"  {detail}"))
    if not cond:
        fails.append(label)


def rings_of(payload, key):
    return [[(r[i], r[i + 1]) for i in range(0, len(r), 2)] for r in payload[key]]


def in_ring(ring, px, py):
    inside = False
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i - 1]
        x1, y1 = ring[i]
        if (y0 > py) != (y1 > py):
            xi = x0 + (py - y0) * (x1 - x0) / (y1 - y0)
            if px < xi:
                inside = not inside
    return inside


def in_any(rings, px, py):
    return any(in_ring(r, px, py) for r in rings)


def unit(epsg):
    p = GRIDS[epsg]
    lat = NORM_LAT if p.north else -NORM_LAT
    rn = math.hypot(*p.forward(lat, p.lon0))

    def f(lon, la):
        x, y = p.forward(la, lon)
        return (x / rn, y / rn)
    return f


payload = json.load(io.open(GEO_PATH, encoding="utf-8"))
ant = rings_of(payload, "ant")
shelf = rings_of(payload, "shelf")
arc = rings_of(payload, "arc")
fn = unit(3413)
fs = unit(3976)

print(f"{GEO_PATH}: ant {len(ant)} rings, shelf {len(shelf)}, arc {len(arc)}")

# ---- 1. Nothing may sit outside the disc the deck draws.
worst = 0.0
for group in (ant, shelf, arc):
    for r in group:
        for x, y in r:
            worst = max(worst, math.hypot(x, y))
check("every vertex is inside the unit disc", worst <= 1.0009, f"worst r = {worst:.6f}")

# ---- 2. The normalising parallel must land exactly on r = 1.
for name, f, lat in (("north", fn, NORM_LAT), ("south", fs, -NORM_LAT)):
    rr = [math.hypot(*f(lon, lat)) for lon in range(-180, 180, 13)]
    check(f"{name}: latitude {lat:+.0f} sits on r = 1",
          max(abs(v - 1.0) for v in rr) < 1e-12,
          f"spread {min(rr):.9f}..{max(rr):.9f}")

# ---- 3. Orientation, checked on places whose position is not in dispute.
#         The south pole is on land; the north pole is on ocean.
check("the south pole is inside Antarctic land", in_any(ant, 0.0, 0.0))
check("the north pole is NOT inside northern land", not in_any(arc, 0.0, 0.0))

# Four Antarctic places, by bearing from the pole. In EPSG:3976 (central
# meridian 0) +y points at lon 0, +x at lon +90.
places_s = [
    ("McMurdo 77.85S 166.67E", -77.85, 166.67, lambda x, y: y < 0 and x > 0),
    ("Rothera 67.57S 68.13W", -67.57, -68.13, lambda x, y: x < 0),
    ("Neumayer III 70.67S 8.27W", -70.67, -8.27, lambda x, y: y > 0 and x < 0),
    ("Mawson 67.60S 62.87E", -67.60, 62.87, lambda x, y: x > 0),
]
for label, la, lo, test in places_s:
    x, y = fs(lo, la)
    check(f"south: {label} on the expected side", test(x, y), f"({x:+.4f},{y:+.4f})")

# The Arctic is rotated, and in a direction worth being explicit about.
# EPSG:3413's central meridian is -45, and the polar stereographic convention
# puts the central meridian DOWN the page (Snyder 21-5: y = -rho cos(lam)).
# So Greenland sits at the bottom of the disc and Siberia at the top. The old
# spherical disc put lon 0 at the bottom; this is a 45 degree rotation, not a
# flip. Confirmed against pyproj, which is why this is asserted rather than
# assumed.
x, y = fn(-45.0, 70.0)
check("north: the central meridian (-45) runs straight DOWN the page",
      abs(x) < 1e-9 and y < 0, f"({x:+.6f},{y:+.6f})")
x, y = fn(135.0, 70.0)
check("north: lon +135 runs straight up",
      abs(x) < 1e-9 and y > 0, f"({x:+.6f},{y:+.6f})")
x, y = fn(45.0, 70.0)
check("north: lon +45 is 90 degrees round from the central meridian",
      x > 0 and abs(y) < 1e-9, f"({x:+.6f},{y:+.6f})")

# Land where there is land, water where there is water. Points are chosen well
# inside a feature: at a 6 km simplification tolerance a fjord head such as
# Longyearbyen legitimately falls outside the drawn outline, and testing there
# would be testing the tolerance rather than the projection.
check("north: Greenland interior (72N 40W) is land", in_any(arc, *fn(-40.0, 72.0)))
check("north: Greenland Sea (75N 0E) is not land", not in_any(arc, *fn(0.0, 75.0)))
check("north: Spitsbergen interior (78.7N 16E) is land", in_any(arc, *fn(16.0, 78.7)))
check("north: Nordaustlandet (79.8N 23E) is land", in_any(arc, *fn(23.0, 79.8)))
check("north: Novaya Zemlya (74N 56E) is land", in_any(arc, *fn(56.0, 74.0)))
check("north: Iceland (64.9N 18.5W) is land", in_any(arc, *fn(-18.5, 64.9)))
check("north: the central Arctic Ocean (87N 90E) is not land",
      not in_any(arc, *fn(90.0, 87.0)))

# ---- 4. The ellipsoid is doing work: the new radii must differ from the
#         spherical disc this replaces, by an amount that is small but real.
R0 = math.tan(math.pi / 4 - 45 * math.pi / 360)


def spherical_r(lat):
    return math.tan(math.pi / 4 - abs(lat) * math.pi / 360) / R0


rows = []
for lat in (85, 80, 75, 70, 65, 60, 55, 50):
    r_new = math.hypot(*fn(-45.0, lat))
    r_old = spherical_r(lat)
    rows.append((lat, r_old, r_new, (r_new - r_old) / r_old * 100.0))
print("\n  latitude   spherical   ellipsoidal   difference")
for lat, o, n, d in rows:
    print(f"  {lat:>5}      {o:8.5f}    {n:8.5f}     {d:+6.3f} %")
check("ellipsoidal radii differ from the old spherical disc",
      any(abs(d) > 0.05 for *_, d in rows),
      "if these agreed the projection change did nothing")
check("the difference stays small enough to be a correction, not a redesign",
      all(abs(d) < 2.0 for *_, d in rows))

# ---- 5. Ice shelves must sit against the Antarctic coast, not float free.
#         Every shelf ring's centroid should be south of 60 S.
p = GRIDS[3976]
rn_s = math.hypot(*p.forward(-NORM_LAT, 0.0))
bad = 0
for r in shelf:
    cx = sum(x for x, _ in r) / len(r)
    cy = sum(y for _, y in r) / len(r)
    lat, _ = p.inverse(cx * rn_s, cy * rn_s)
    if lat > -60.0:
        bad += 1
check("every ice shelf centroid is south of 60 S", bad == 0, f"{bad} outside")

# ---- 6. No ring may be a clipping box artefact: a ring of exactly four points
#         with two axis-aligned edges is what a rectangular clip leaves behind.
boxes = 0
for group in (ant, shelf, arc):
    for r in group:
        if len(r) == 4:
            xs = sorted(set(round(x, 6) for x, _ in r))
            ys = sorted(set(round(y, 6) for _, y in r))
            if len(xs) == 2 and len(ys) == 2:
                boxes += 1
check("no rectangular clip artefacts", boxes == 0, f"{boxes} found")

print()
if fails:
    print(f"{len(fails)} FAILED: " + ", ".join(fails))
    sys.exit(1)
print("all assertions held")
