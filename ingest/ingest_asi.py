"""
ingest_asi — daily sea-ice concentration at 6.25 km, from the primary source.

What this replaces
------------------
The deck's ice field is a 220 x 220 raster covering a whole hemisphere: the
marginal ice zone, the part that is actually changing, is about four cells
wide. That was the largest fidelity constraint on the platform and the
expansion plan proposed fixing it by upsampling to 440 x 440, which would have
made a number look like more than it is.

This is the real field instead: the ARTIST Sea Ice (ASI) algorithm on AMSR2, at
6.25 km, published daily by the Institute of Environmental Physics, University
of Bremen. 1216 x 1792 in the north, 1264 x 1328 in the south — 30x and 21x the
cells of the current field, from the institute that wrote the algorithm.

Source, and why this one
------------------------
    https://data.seaice.uni-bremen.de/amsr2/asi_daygrid_swath/{n,s}6250/netcdf/

meereisportal.de mirrors the same product as 8.3 MB GeoTIFFs reprojected to the
Hughes-ellipsoid NSIDC grids (EPSG:3411/3412). We take it from IUP Bremen
instead: it is the originating institute, the files are 650 KB of CF-1.5
NetCDF, they are published on WGS-84 (EPSG:3413 north, EPSG:3976 south), and
robots.txt there permits automated retrieval. Fewer hops, smaller files, and
the grid the rest of the world publishes on.

  Spreen, G., L. Kaleschke and G. Heygster (2008), Sea ice remote sensing using
  AMSR-E 89 GHz channels, J. Geophys. Res. 113, C02S03, doi:10.1029/2005JC003384

Two things this script refuses to assume
----------------------------------------
1. **Orientation.** The NetCDF y axis ASCENDS — the file was written through
   `grdmath ... FLIPUD` — while its own GeoTransform describes a north-up
   raster. Read the axes, derive the transform from them, orient the array, and
   assert the result against the declared transform. An unchecked flip here
   draws the Arctic upside down and nothing in the rendering would complain.

2. **Cell area.** A polar stereographic grid is conformal, not equal-area. A
   6.25 km cell is 6.25 km on a side only at the standard parallel. Extent and
   area are computed with the true per-row scale factor, not by multiplying a
   cell count by a nominal size.

Output
------
    data/asi/<frame-id>.png      8-bit, 0.5 % steps, 255 = no value in source
    data/asi/manifest.json       one record per frame, with full provenance

Every frame is verified after packing by decoding the PNG back and comparing it
to the source array: the no-value mask must match exactly, and no cell may
differ by more than half a quantisation step.

Usage
-----
    python3 ingest_asi.py --hemisphere n --dates 2026-09-11
    python3 ingest_asi.py --hemisphere s --dates 2026-09-01:2026-09-11
    python3 ingest_asi.py --hemisphere n --minima 2013:2026
"""

import argparse
import hashlib
import io
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olympus_proj import ASI_N6250, ASI_S6250  # noqa: E402

BASE = "https://data.seaice.uni-bremen.de/amsr2/asi_daygrid_swath"
VERSION = "v5.4"
USER_AGENT = "olympus-asi-ingest/1.0 (+build-time ingest, no runtime fetch)"

# 0.5 % steps: code = round(concentration * 2), so 0..200 spans 0..100 %.
# 255 means the source carried no value for that cell — land, outside the
# swath, or the pole hole. The source does not distinguish those and neither
# do we; inventing the distinction would be inventing data.
SCALE = 2.0
CODE_MAX = 200
NO_VALUE = 255

HEMI = {
    "n": {"grid": ASI_N6250, "dir": "n6250", "epsg": 3413, "name": "Arctic"},
    "s": {"grid": ASI_S6250, "dir": "s6250", "epsg": 3976, "name": "Antarctic"},
}

# The concentration at and above which a cell counts toward extent. 15 % is the
# convention every sea-ice extent series in the literature uses; it is a
# convention, not a measurement, and it is stated on the frame rather than
# buried here.
EXTENT_THRESHOLD = 15.0


def fetch(url, label):
    """Fetch once, at build time, and return bytes plus a provenance stamp."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=180) as r:
        body = r.read()
        last_modified = r.headers.get("Last-Modified")
    return body, {
        "label": label,
        "url": url,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "http_last_modified": last_modified,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }


def read_nc(body, grid):
    """Read z, x, y; orient north-up; assert the geometry we were promised."""
    import netCDF4 as nc

    ds = nc.Dataset("inmemory", mode="r", memory=body)
    try:
        z = np.ma.filled(ds["z"][:].astype("float64"), np.nan)
        x = np.asarray(ds["x"][:], dtype="float64")
        y = np.asarray(ds["y"][:], dtype="float64")
        crs = ds["polar_stereographic"]
        declared = {
            "grid_mapping_name": str(crs.grid_mapping_name),
            "standard_parallel": float(crs.standard_parallel),
            "straight_vertical_longitude_from_pole": float(
                crs.straight_vertical_longitude_from_pole
            ),
            "semi_major_axis": float(crs.semi_major_axis),
            "inverse_flattening": float(crs.inverse_flattening),
            "GeoTransform": str(crs.GeoTransform).strip(),
        }
        history = str(getattr(ds, "history", ""))
        info = str(getattr(ds, "info", ""))
        author = str(getattr(ds, "author", ""))
    finally:
        ds.close()

    # Derive the transform from the axes themselves.
    dx = float(np.round(np.median(np.diff(x)), 6))
    dy_asc = float(np.round(np.median(np.diff(y)), 6))
    flipped = dy_asc > 0                      # y ascending => row 0 is the south edge
    if flipped:
        z = z[::-1, :]
        y = y[::-1]
    dy = float(np.round(np.median(np.diff(y)), 6))
    gt = (x[0] - dx / 2.0, dx, 0.0, y[0] - dy / 2.0, 0.0, dy)

    problems = []
    if z.shape != (grid.height, grid.width):
        problems.append(f"shape {z.shape} != declared {(grid.height, grid.width)}")
    for i, (a, b) in enumerate(zip(gt, grid.gt)):
        if abs(a - b) > 1e-6:
            problems.append(f"GeoTransform[{i}] {a} != declared {b}")
    if abs(declared["standard_parallel"] - grid.proj.lat_ts) > 1e-9:
        problems.append(
            f"standard parallel {declared['standard_parallel']} != "
            f"{grid.proj.lat_ts} (EPSG:{grid.proj.epsg})"
        )
    if abs(declared["semi_major_axis"] - grid.proj.a) > 1e-6:
        problems.append("semi-major axis is not the one this grid is defined on")
    if problems:
        raise SystemExit("source geometry does not match the declared grid:\n  " +
                         "\n  ".join(problems))

    return z, {
        "declared_crs": declared,
        "y_axis_was_ascending": flipped,
        "source_history": history,
        "source_info": info,
        "source_author": author,
    }


def quantise(z):
    """float concentration -> uint8 codes, and the no-value mask."""
    missing = ~np.isfinite(z)
    codes = np.full(z.shape, NO_VALUE, dtype=np.uint8)
    good = ~missing
    vals = np.clip(z[good], 0.0, 100.0)
    codes[good] = np.rint(vals * SCALE).astype(np.uint8)
    if codes[good].max() > CODE_MAX:
        raise SystemExit("quantisation overflowed the reserved code range")
    return codes, missing


def statistics(codes, missing, grid):
    """Extent and area in km^2, on the ellipsoid, not on nominal cells."""
    conc = codes.astype("float64") / SCALE
    area_row = np.array([grid.pixel_area_km2(r) for r in range(grid.height)])
    valid = ~missing
    iced = valid & (conc >= EXTENT_THRESHOLD)
    extent = float(area_row[iced].sum())
    area = float((area_row[valid] * conc[valid] / 100.0)[conc[valid] >= EXTENT_THRESHOLD].sum())
    return {
        "extent_km2": round(extent, 1),
        "area_km2": round(area, 1),
        "extent_threshold_pct": EXTENT_THRESHOLD,
        "cells_with_value": int(valid.sum()),
        "cells_no_value": int(missing.sum()),
        "nominal_cell_km2": abs(grid.gt[1] * grid.gt[5]) / 1e6,
        "true_cell_km2_range": [round(float(area_row.min()), 4),
                                round(float(area_row.max()), 4)],
    }


def write_png(path, codes):
    from PIL import Image
    Image.fromarray(codes, mode="L").save(path, optimize=True, compress_level=9)
    return os.path.getsize(path)


def verify(path, z, codes, missing):
    """Decode what was written and compare it to the source array."""
    from PIL import Image
    back = np.asarray(Image.open(path).convert("L"), dtype=np.uint8)
    if back.shape != codes.shape:
        return False, f"decoded shape {back.shape} != {codes.shape}"
    if not np.array_equal(back, codes):
        return False, "decoded codes differ from the packed codes"
    mask_back = back == NO_VALUE
    if not np.array_equal(mask_back, missing):
        return False, "no-value mask does not survive the round trip"
    good = ~missing
    err = np.abs(back[good].astype("float64") / SCALE - np.clip(z[good], 0.0, 100.0))
    worst = float(err.max()) if err.size else 0.0
    half_step = 0.5 / SCALE
    if worst > half_step + 1e-9:
        return False, f"worst quantisation error {worst} exceeds half a step ({half_step})"
    return True, worst


def url_for(hemi, day):
    h = HEMI[hemi]
    return (f"{BASE}/{h['dir']}/netcdf/{day:%Y}/"
            f"asi-AMSR2-{h['dir']}-{day:%Y%m%d}-{VERSION}.nc")


def ingest_day(hemi, day, outdir, manifest):
    h = HEMI[hemi]
    grid = h["grid"]
    frame_id = f"asi-{h['dir']}-{day:%Y%m%d}"
    url = url_for(hemi, day)
    try:
        body, stamp = fetch(url, frame_id)
    except Exception as exc:                       # noqa: BLE001
        print(f"  {frame_id}: NOT AVAILABLE ({exc})")
        return None

    z, geom = read_nc(body, grid)
    codes, missing = quantise(z)
    png = os.path.join(outdir, frame_id + ".png")
    size = write_png(png, codes)
    ok, detail = verify(png, z, codes, missing)
    if not ok:
        raise SystemExit(f"{frame_id}: VERIFICATION FAILED — {detail}")
    stats = statistics(codes, missing, grid)

    rec = {
        "id": frame_id,
        "hemisphere": h["name"],
        "observed": f"{day:%Y-%m-%d}",
        "parameter": "sea ice concentration",
        "units": "percent",
        "mode": "MEAS",
        "instrument": "AMSR2 (GCOM-W1), 89 GHz",
        "algorithm": f"ARTIST Sea Ice (ASI) {VERSION}",
        "producer": "Institute of Environmental Physics, University of Bremen",
        "resolution_m": int(abs(grid.gt[1])),
        "epsg": grid.proj.epsg,
        "width": grid.width,
        "height": grid.height,
        "encoding": {
            "file": os.path.basename(png),
            "bytes": size,
            "type": "8-bit PNG, row 0 = north edge of the GeoTransform",
            "code_to_value": "concentration_percent = code / 2",
            "no_value_code": NO_VALUE,
            "quantisation_step_pct": 1.0 / SCALE,
            "worst_quantisation_error_pct": round(float(detail), 6),
        },
        "statistics": stats,
        "source": stamp,
        "geometry": geom,
        "citation": (
            "Spreen, G., L. Kaleschke and G. Heygster (2008), Sea ice remote sensing "
            "using AMSR-E 89 GHz channels, J. Geophys. Res. 113, C02S03, "
            "doi:10.1029/2005JC003384. Data: University of Bremen, "
            "https://seaice.uni-bremen.de"
        ),
    }
    manifest.append(rec)
    print(f"  {frame_id}: {size/1024:6.1f} KB  extent {stats['extent_km2']/1e6:5.2f} M km2"
          f"  worst err {float(detail):.3f} %  ok")
    return rec


def parse_dates(spec):
    if ":" in spec:
        a, b = spec.split(":", 1)
        d0 = datetime.strptime(a, "%Y-%m-%d").date()
        d1 = datetime.strptime(b, "%Y-%m-%d").date()
        step = timedelta(days=1)
        out = []
        while d0 <= d1:
            out.append(d0)
            d0 += step
        return out
    return [datetime.strptime(spec, "%Y-%m-%d").date()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--hemisphere", choices=("n", "s"), required=True)
    ap.add_argument("--dates", help="YYYY-MM-DD or YYYY-MM-DD:YYYY-MM-DD")
    ap.add_argument("--latest", action="store_true",
                    help="the most recent day the archive actually carries")
    ap.add_argument("--out", default="data/asi")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    manifest_path = os.path.join(args.out, "manifest.json")
    manifest = []
    if os.path.exists(manifest_path):
        manifest = json.load(io.open(manifest_path, encoding="utf-8"))["frames"]

    if args.latest:
        days = []
        probe = date.today()
        for back in range(1, 8):
            days.append(probe - timedelta(days=back))
    elif args.dates:
        days = parse_dates(args.dates)
    else:
        ap.error("give --dates or --latest")

    print(f"ASI {HEMI[args.hemisphere]['name']} {abs(HEMI[args.hemisphere]['grid'].gt[1])} m "
          f"-> {args.out}")
    have = {r["id"] for r in manifest}
    done = 0
    for day in days:
        frame_id = f"asi-{HEMI[args.hemisphere]['dir']}-{day:%Y%m%d}"
        if frame_id in have:
            print(f"  {frame_id}: already in manifest")
            done += 1
            continue
        if ingest_day(args.hemisphere, day, args.out, manifest):
            done += 1
            if args.latest:
                break

    manifest.sort(key=lambda r: (r["hemisphere"], r["observed"]))
    with io.open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "product": "ASI AMSR2 sea-ice concentration, 6.25 km",
            "producer": "Institute of Environmental Physics, University of Bremen",
            "source_root": BASE,
            "licence_note": (
                "Freely available for research and education; cite Spreen et al. 2008 "
                "and the University of Bremen. Confirm terms before commercial use."
            ),
            "frames": manifest,
        }, f, ensure_ascii=False, indent=1)
    print(f"{done} frame(s); manifest carries {len(manifest)}")


if __name__ == "__main__":
    main()
