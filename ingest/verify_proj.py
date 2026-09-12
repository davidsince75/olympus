"""
verify_proj — assert olympus_proj against pyproj, and against the source grids.

pyproj is a BUILD-TIME dependency only. The point of this script is that
olympus_proj.py and olympus_proj.js can then be shipped with no dependency at
all and still be trusted, because an independent implementation of the same
EPSG definitions agrees with them to well under a metre.

Run: python3 verify_proj.py
Exit code 0 = every assertion held.
"""

import math
import sys

from pyproj import CRS, Transformer

from olympus_proj import GRIDS, ASI_N6250, ASI_S6250

TOL_M = 0.05          # metres — agreement with pyproj
TOL_DEG = 1e-9        # degrees — round-trip closure

fails = []


def check(label, cond, detail=""):
    if cond:
        print(f"  ok    {label}")
    else:
        print(f"  FAIL  {label}  {detail}")
        fails.append(label)


def sample_lats(grid):
    """Latitudes that actually occur on this grid, per hemisphere."""
    if grid.north:
        return [89.9, 85, 80, 75, 70, 65, 60, 55, 50, 45]
    return [-89.9, -85, -80, -75, -71, -70, -65, -60, -55, -50]


print("olympus_proj vs pyproj (WGS-84 ellipsoidal polar stereographic)")
for epsg, grid in GRIDS.items():
    fwd = Transformer.from_crs(CRS.from_epsg(4326), CRS.from_epsg(epsg), always_xy=True)
    inv = Transformer.from_crs(CRS.from_epsg(epsg), CRS.from_epsg(4326), always_xy=True)
    worst_f = 0.0
    worst_i = 0.0
    worst_rt = 0.0
    n = 0
    for lat in sample_lats(grid):
        for lon in range(-180, 180, 7):
            gx, gy = grid.forward(lat, lon)
            px, py = fwd.transform(lon, lat)
            worst_f = max(worst_f, math.hypot(gx - px, gy - py))

            glat, glon = grid.inverse(px, py)
            plon, plat = inv.transform(px, py)
            dlon = abs(((glon - plon + 180) % 360) - 180)
            worst_i = max(worst_i, abs(glat - plat), dlon if lat < 89 else 0.0)

            rlat, rlon = grid.inverse(gx, gy)
            drt = abs(((rlon - lon + 180) % 360) - 180)
            worst_rt = max(worst_rt, abs(rlat - lat), drt if abs(lat) < 89 else 0.0)
            n += 1
    print(f"EPSG:{epsg}  ({n} points)")
    check(f"EPSG:{epsg} forward agrees with pyproj", worst_f < TOL_M, f"worst {worst_f:.6f} m")
    check(f"EPSG:{epsg} inverse agrees with pyproj", worst_i < 1e-7, f"worst {worst_i:.3e} deg")
    check(f"EPSG:{epsg} round-trip closes", worst_rt < TOL_DEG, f"worst {worst_rt:.3e} deg")

print("\nThe two ASI grids, against their own declared geometry")
for grid in (ASI_N6250, ASI_S6250):
    p = grid.proj
    # The pole must land inside the raster, and at the pixel the GeoTransform implies.
    pole_lat = 90.0 if p.north else -90.0
    col, row = grid.latlon_to_colrow(pole_lat, 0.0)
    x0, dx, _, y0, _, dy = grid.gt
    exp_col = (0 - x0) / dx - 0.5
    exp_row = (0 - y0) / dy - 0.5
    check(
        f"{grid.name}: pole at the GeoTransform origin pixel",
        abs(col - exp_col) < 1e-6 and abs(row - exp_row) < 1e-6,
        f"got ({col:.4f},{row:.4f}) expected ({exp_col:.4f},{exp_row:.4f})",
    )
    check(
        f"{grid.name}: pole inside the raster",
        0 <= col < grid.width and 0 <= row < grid.height,
        f"({col:.1f},{row:.1f}) in {grid.width}x{grid.height}",
    )
    # Corner latitudes must be sane for the hemisphere.
    corners = [grid.colrow_to_latlon(c, r)
               for c, r in ((0, 0), (grid.width - 1, 0),
                            (0, grid.height - 1), (grid.width - 1, grid.height - 1))]
    ok = all((lat > 25) if p.north else (lat < -25) for lat, _ in corners)
    check(f"{grid.name}: corners stay in the right hemisphere", ok,
          " ".join(f"({la:.2f},{lo:.2f})" for la, lo in corners))
    # Every pixel centre must round-trip through lat/lon back to itself.
    worst = 0.0
    for c in range(0, grid.width, 97):
        for r in range(0, grid.height, 97):
            la, lo = grid.colrow_to_latlon(c, r)
            c2, r2 = grid.latlon_to_colrow(la, lo)
            worst = max(worst, abs(c2 - c), abs(r2 - r))
    check(f"{grid.name}: pixel centres round-trip", worst < 1e-6, f"worst {worst:.3e} px")

print("\n3976 and 3031 are not interchangeable")
d = []
for lat in (-60, -65, -70, -75, -80):
    a = GRIDS[3976].forward(lat, 0.0)
    b = GRIDS[3031].forward(lat, 0.0)
    d.append((lat, math.hypot(a[0] - b[0], a[1] - b[1])))
for lat, dist in d:
    print(f"  lat {lat:>4}  3976 vs 3031 differ by {dist:8.1f} m")
check("3976 != 3031 at the ice edge", max(x for _, x in d) > 500.0,
      "if these agreed, one of the definitions would be wrong")

print()
if fails:
    print(f"{len(fails)} FAILED: " + ", ".join(fails))
    sys.exit(1)
print("all assertions held")
