"""
ingest_osisaf — rebuild the deck's sea-ice field on the real projection.

Why this had to be rebuilt rather than patched
----------------------------------------------
The deck's ice field is not a picture of a grid; it is OSI SAF's EASE2 25 km
cells forward-binned onto the deck's unit disc *through the deck's projection*.
Change the projection and the field silently stops matching the coastline drawn
over it — by 0.2 % radially everywhere, and by a 45 degree rotation in the
Arctic, because EPSG:3413's central meridian is -45 where the old spherical disc
effectively used 0.

So the projection swap and this ingest are one job. The original pipeline
(`index.py`, `ingest.py`, `pack.py`) did not survive its container; what
survived was the published payload, and that turns out to be enough to rebuild
it faithfully — see *The frame list is not guessed* below.

Source
------
met.no THREDDS over OPeNDAP, no account, exactly as before:

    OSI-450-a  CDR v3.0        1978-11 -> 2020-12   conc_450a_files/monthly/
    OSI-430-a  ICDR v3.0       2021-01 -> 2025-09   conc_cra_files/monthly/
    OSI-438-a  ICDR v3.0 AMSR  2021    -> present   conc_438_files/monthly/

All three share the EASE2 25 km equal-area grid, 432 x 432, which is why extent
is an exact cell count times 625 km2 and carries no projection error at all.

The frame list is not guessed
-----------------------------
The published deck carries, per hemisphere, `ymo` (the true calendar offset of
every frame) and `runs` (which record each frame came from). Those two
reconstruct the exact 570-file list the original ingest used. This matters more
than convenience: the record has genuine outages — April-June 1986 and December
1987 are missing from both hemispheres — so 570 frames span 574 calendar months
and a frame index is not a month offset. Re-deriving the list from a catalogue
walk risks silently producing a *different* 570.

How it is checked
-----------------
Extent is computed on the source grid, where it is exact, and the source grid is
unaffected by anything the deck draws. So the extents this run computes must
equal the extents already in the published deck, frame for frame. That is a
1,140-value equality check against a number the deck has been showing for days,
and it is the assertion that says the right files were read.

Usage
    python3 ingest/ingest_osisaf.py --hemisphere nh --out data/osi
    python3 ingest/ingest_osisaf.py --hemisphere nh --limit 12      # smoke test
"""

import argparse
import concurrent.futures
import io
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olympus_proj import GRIDS  # noqa: E402

THREDDS = "https://thredds.met.no/thredds/dodsC/osisaf/met.no/reprocessed/ice"
TREE = {
    "cdr-v3p0": "conc_450a_files",
    "icdr-v3p0": "conc_cra_files",
    "icdr-v3p0-amsr": "conc_438_files",
    "icdrft-v3p0-amsr": "conc_438_files",
}

NG = 220                 # cells across the deck's unit disc, unchanged
PER = 100                # frames per atlas sheet, 10 x 10
LEVELS = 100             # 1 % steps
NP = NG * NG
EXTENT_THRESHOLD = 15.0  # percent
CELL_KM2 = 625.0         # EASE2 25 km, exactly
NORM_LAT = 45.0

HEMI = {
    "nh": {"epsg": 3413, "sign": 1},
    "sh": {"epsg": 3976, "sign": -1},
}


def unit_projector(epsg):
    p = GRIDS[epsg]
    lat = NORM_LAT if p.north else -NORM_LAT
    rn = (p.forward(lat, p.lon0)[0] ** 2 + p.forward(lat, p.lon0)[1] ** 2) ** 0.5
    return p, rn


def project_grid(lat2d, lon2d, epsg):
    """Forward-project the source grid once; every frame reuses the result.

    Returns the target cell index for each source cell, and a validity mask for
    the cells that fall inside the disc at all.
    """
    p, rn = unit_projector(epsg)
    la = np.asarray(lat2d, dtype="float64")
    lo = np.asarray(lon2d, dtype="float64")

    phi = np.abs(np.radians(la))
    lam = np.radians(lo - p.lon0)
    e = p.e
    s = np.sin(phi)
    t = np.tan(np.pi / 4.0 - phi / 2.0) / (((1.0 - e * s) / (1.0 + e * s)) ** (e / 2.0))
    rho = p.a * p._mc * t / p._tc
    x = rho * np.sin(lam) / rn
    y = (-1.0 if p.north else 1.0) * rho * np.cos(lam) / rn

    inside = (x * x + y * y) <= 1.0
    col = np.floor((x + 1.0) / 2.0 * NG).astype("int64")
    row = np.floor((1.0 - y) / 2.0 * NG).astype("int64")
    ok = inside & (col >= 0) & (col < NG) & (row >= 0) & (row < NG)
    idx = np.where(ok, row * NG + col, -1)
    return idx, ok


def bin_frame(conc, idx, ok):
    """Forward-bin source cells into the disc: mean of the cells that land in each.

    Forward binning, not sampling: every source cell contributes exactly once, so
    no cell is read twice and none is skipped. Cells with no source coverage stay
    at zero, which is what the deck's mask then treats as ocean or land.
    """
    valid = ok & np.isfinite(conc)
    flat_idx = idx[valid]
    vals = conc[valid]
    if flat_idx.size == 0:
        return np.zeros(NP, dtype=np.uint8)
    total = np.bincount(flat_idx, weights=vals, minlength=NP)
    count = np.bincount(flat_idx, minlength=NP)
    out = np.zeros(NP, dtype="float64")
    nz = count > 0
    out[nz] = total[nz] / count[nz]
    return np.clip(np.rint(out), 0, LEVELS).astype(np.uint8)


def url_for(hemi, record, ym):
    year = ym[:4]
    return (f"{THREDDS}/{TREE[record]}/monthly/{year}/"
            f"ice_conc_{hemi}_ease2-250_{record}_{ym}.nc")


def frame_list(header, hemi):
    """Reconstruct the exact file list from ymo + runs in the published payload."""
    H = header["hemi"][hemi]
    y0 = int(H["m0"][:4]) * 12 + int(H["m0"][4:]) - 1
    runs = H["runs"]
    out = []
    for k, off in enumerate(H["ymo"]):
        rec = runs[0]
        for r in runs:
            if r[0] <= k:
                rec = r
            else:
                break
        t = y0 + off
        ym = f"{t // 12:04d}{t % 12 + 1:02d}"
        out.append({"k": k, "ym": ym, "record": rec[2], "label": rec[1],
                    "fast_track": bool(rec[3]), "url": url_for(hemi, rec[2], ym)})
    return out


def read_frame(spec, want_grid=False):
    import netCDF4 as nc
    d = nc.Dataset(spec["url"])
    try:
        conc = np.ma.filled(d["ice_conc"][0, :, :].astype("float64"), np.nan)
        grid = None
        if want_grid:
            grid = (np.asarray(d["lat"][:]), np.asarray(d["lon"][:]))
    finally:
        d.close()
    return conc, grid


def extent_of(conc):
    """Exact on the source grid: a cell count times an equal-area cell."""
    return float(np.count_nonzero(np.isfinite(conc) & (conc >= EXTENT_THRESHOLD))
                 * CELL_KM2 / 1e6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hemisphere", choices=("nh", "sh"), required=True)
    ap.add_argument("--header", default="deck/osi_header_old.json",
                    help="the published deck's OSI header, for the frame list and the check")
    ap.add_argument("--out", default="data/osi")
    ap.add_argument("--limit", type=int, default=0, help="first N frames only, for a smoke test")
    ap.add_argument("--threads", type=int, default=10)
    args = ap.parse_args()

    hemi = args.hemisphere
    header = json.load(io.open(args.header, encoding="utf-8"))
    specs = frame_list(header, hemi)
    if args.limit:
        specs = specs[:args.limit]
    print(f"OSI SAF {hemi}: {len(specs)} frames, {specs[0]['ym']} -> {specs[-1]['ym']}")
    print(f"  target: {NG}x{NG} unit disc on EPSG:{HEMI[hemi]['epsg']}")

    # The grid geometry is identical across all three records; read it once.
    t0 = time.time()
    _, grid = read_frame(specs[0], want_grid=True)
    lat2d, lon2d = grid
    idx, ok = project_grid(lat2d, lon2d, HEMI[hemi]["epsg"])
    print(f"  grid {lat2d.shape}, {int(ok.sum())} of {ok.size} cells inside the disc "
          f"({time.time()-t0:.1f}s)")

    fields = [None] * len(specs)
    exts = [None] * len(specs)
    errors = []

    def work(i):
        spec = specs[i]
        for attempt in range(3):
            try:
                conc, _ = read_frame(spec)
                return i, bin_frame(conc, idx, ok), extent_of(conc)
            except Exception as exc:                       # noqa: BLE001
                if attempt == 2:
                    errors.append(f"{spec['ym']}: {type(exc).__name__} {exc}")
                    return i, None, None
                time.sleep(1.5 * (attempt + 1))

    t0 = time.time()
    done = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as ex:
        for i, field, extent in ex.map(work, range(len(specs))):
            fields[i] = field
            exts[i] = extent
            done += 1
            if done % 50 == 0 or done == len(specs):
                print(f"  {done}/{len(specs)}  {time.time()-t0:.0f}s")

    if errors:
        print("\n".join("  ERROR " + e for e in errors[:10]))
        raise SystemExit(f"{len(errors)} frames failed to read")

    # ---- the check that says the right files were read ----
    published = header["hemi"][hemi]["ext"][:len(specs)]
    diffs = [(specs[i]["ym"], published[i], round(exts[i], 3))
             for i in range(len(specs))
             if abs(published[i] - round(exts[i], 3)) > 0.0005]
    print(f"\nextent against the published deck: {len(specs) - len(diffs)}/{len(specs)} exact")
    for ym, a, b in diffs[:10]:
        print(f"  {ym}: published {a}  recomputed {b}")
    if diffs:
        raise SystemExit("extent mismatch — the frame list or the reader is wrong")

    # ---- pack ----
    from PIL import Image
    os.makedirs(args.out, exist_ok=True)
    nsheets = (len(specs) + PER - 1) // PER
    sheets = []
    for sh in range(nsheets):
        count = min(PER, len(specs) - sh * PER)
        atlas = np.zeros((NG * 10, NG * 10), dtype=np.uint8)
        for f in range(count):
            gr, gc = f // 10, f % 10
            atlas[gr * NG:(gr + 1) * NG, gc * NG:(gc + 1) * NG] = \
                fields[sh * PER + f].reshape(NG, NG)
        path = os.path.join(args.out, f"osi_{hemi}_{sh}.png")
        Image.fromarray(atlas, mode="L").save(path, optimize=True, compress_level=9)
        sheets.append(os.path.basename(path))
        print(f"  {path}  {os.path.getsize(path)/1024:.0f} KB")

    H = header["hemi"][hemi]
    manifest = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hemisphere": hemi,
        "ng": NG, "per": PER, "levels": LEVELS,
        "n": len(specs),
        "m0": H["m0"],
        "epsg": HEMI[hemi]["epsg"],
        "normalising_latitude": NORM_LAT if hemi == "nh" else -NORM_LAT,
        "binning": "forward, mean of source cells falling in each target cell",
        "extent": {
            "threshold_pct": EXTENT_THRESHOLD,
            "method": "exact cell count on the EASE2 25 km source grid x 625 km2",
            "checked_against_published_deck": len(specs) - len(diffs),
        },
        "ymo": H["ymo"][:len(specs)],
        "ext": [round(v, 3) for v in exts],
        "runs": H["runs"],
        "clim": H["clim"],
        "file0": os.path.basename(specs[0]["url"]),
        "fileN": os.path.basename(specs[-1]["url"]),
        "source_root": THREDDS,
        "sheets": sheets,
        "citation": ("EUMETSAT Ocean and Sea Ice Satellite Application Facility, "
                     "Global sea ice concentration climate data record v3.0, "
                     "OSI-450-a / OSI-430-a / OSI-438-a, via met.no THREDDS."),
    }
    mp = os.path.join(args.out, f"manifest_{hemi}.json")
    with io.open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"\n{mp}")
    print(f"  {len(specs)} frames, {nsheets} sheets, "
          f"{sum(os.path.getsize(os.path.join(args.out, s)) for s in sheets)/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
