"""
build_imagery — rebuild the deck's base imagery on the grids it now draws.

Why it had to be rebuilt
------------------------
The previous imagery was fetched as plate carree and resampled into the deck's
*spherical* disc. When the deck moved to EPSG:3413 / EPSG:3976 that imagery
became 45 degrees out of place in the north, so it was withdrawn rather than
drawn wrong. This puts it back, on the real grids.

Two sources, because one does not cover the frame
-------------------------------------------------
GIBS publishes polar imagery on EPSG:3413 (north) and EPSG:3031 (south), and
**those tile matrices stop at +/-4,194,304 m**. Measured, not assumed: a WMS
request for a larger box comes back black outside that square. On this deck's
disc, 4,194,304 m is r = 0.817, which is **latitude 52.6** — and the disc is
framed to 45. So the polar tiles cannot fill it.

Therefore each output image is built from two sources:

  inside  r <= 0.817   the native polar tiles. In the NORTH this is the deck's
                       own grid, EPSG:3413, so the transform is a pure scale and
                       offset: no reprojection, no warp. In the SOUTH the source
                       is EPSG:3031 and the target EPSG:3976 — one degree of
                       standard parallel apart, 6.6 km at 70 S — so it is
                       genuinely reprojected.
  outside r >  0.817   EPSG:4326 plate carree, reprojected. This is the
                       mid-latitude ring: open ocean and the northern edge of
                       the continents, context rather than subject.

The manifest records the fraction of each image that came from each path, so the
claim "the north is not reprojected" can be checked rather than believed.

Output
    data/imagery/<layer>_<hemi>.jpg   out x out, the square the deck draws
    data/imagery/manifest.json        per-image provenance

Usage
    python3 ingest/build_imagery.py --day 2026-09-11
"""

import argparse
import hashlib
import io
import json
import math
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from olympus_proj import GRIDS  # noqa: E402

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg{epsg}/best/wms.cgi"
USER_AGENT = "olympus-imagery-ingest/2.0 (+build-time ingest, no runtime fetch)"

# Measured, in this script's own probe: beyond this the polar tile matrices
# return black.
POLAR_EXTENT_M = 4194304.0

OUT = 1180
RMAX = {"N": 1.3, "S": 1.5}
NORM_LAT = 45.0

HEMI = {
    # target grid (what the deck draws) and the polar source GIBS publishes
    "N": {"target": 3413, "polar_epsg": 3413, "lat_sign": 1},
    "S": {"target": 3976, "polar_epsg": 3031, "lat_sign": -1},
}

LAYERS = [
    {"key": "relief", "nm": "Blue Marble relief & bathymetry",
     "gibs": "BlueMarble_ShadedRelief_Bathymetry", "timed": False},
    {"key": "today", "nm": "MODIS Terra true colour",
     "gibs": "MODIS_Terra_CorrectedReflectance_TrueColor", "timed": True},
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return body, {
        "url": url,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def getmap(epsg, layer, bbox, width, height, day=None):
    q = {
        "SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap",
        "LAYERS": layer, "CRS": f"EPSG:{epsg}",
        "BBOX": ",".join(f"{v:.1f}" for v in bbox),
        "WIDTH": str(width), "HEIGHT": str(height),
        "FORMAT": "image/jpeg",
    }
    if day:
        q["TIME"] = day
    return WMS.format(epsg=epsg) + "?" + urllib.parse.urlencode(q)


def as_array(body):
    from PIL import Image
    return np.asarray(Image.open(io.BytesIO(body)).convert("RGB"), dtype=np.uint8)


def bilinear(src, fx, fy):
    """Sample src (H,W,3) at float pixel coords, clamped at the edges."""
    h, w = src.shape[:2]
    x0 = np.clip(np.floor(fx).astype(np.int64), 0, w - 1)
    y0 = np.clip(np.floor(fy).astype(np.int64), 0, h - 1)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    dx = np.clip(fx - x0, 0.0, 1.0)[..., None]
    dy = np.clip(fy - y0, 0.0, 1.0)[..., None]
    a = src[y0, x0].astype("float32")
    b = src[y0, x1].astype("float32")
    c = src[y1, x0].astype("float32")
    d = src[y1, x1].astype("float32")
    return (a * (1 - dx) * (1 - dy) + b * dx * (1 - dy)
            + c * (1 - dx) * dy + d * dx * dy)


def norm_radius(epsg):
    p = GRIDS[epsg]
    lat = NORM_LAT if p.north else -NORM_LAT
    return math.hypot(*p.forward(lat, p.lon0))


def inverse_grid(epsg, mx, my):
    """Vectorised inverse of olympus_proj for whole arrays of metres."""
    p = GRIDS[epsg]
    xs = mx
    ys = my if p.north else -my
    rho = np.hypot(xs, ys)
    t = rho * p._tc / (p.a * p._mc)
    e = p.e
    phi = np.pi / 2.0 - 2.0 * np.arctan(t)
    for _ in range(12):
        s = np.sin(phi)
        phi = np.pi / 2.0 - 2.0 * np.arctan(
            t * ((1.0 - e * s) / (1.0 + e * s)) ** (e / 2.0))
    lat = np.degrees(phi) * (1.0 if p.north else -1.0)
    lat = np.where(rho < 1e-9, 90.0 if p.north else -90.0, lat)
    lon = np.degrees(np.arctan2(xs, -ys)) + p.lon0
    lon = (lon + 180.0) % 360.0 - 180.0
    return lat, lon


def forward_grid(epsg, lat, lon):
    p = GRIDS[epsg]
    phi = np.radians(np.abs(lat))
    lam = np.radians(lon - p.lon0)
    e = p.e
    s = np.sin(phi)
    t = np.tan(np.pi / 4.0 - phi / 2.0) / (((1.0 - e * s) / (1.0 + e * s)) ** (e / 2.0))
    rho = p.a * p._mc * t / p._tc
    x = rho * np.sin(lam)
    y = (-1.0 if p.north else 1.0) * rho * np.cos(lam)
    return x, y


def build_one(hemi, layer, polar_img, global_img, day):
    cfg = HEMI[hemi]
    target = cfg["target"]
    rn = norm_radius(target)
    rmax = RMAX[hemi]

    # Output pixel centres, in the deck's unit-disc coordinates.
    u = (np.arange(OUT) + 0.5) / OUT * 2.0 * rmax - rmax
    ux = u[None, :] * np.ones((OUT, 1))
    uy = (rmax - (np.arange(OUT) + 0.5) / OUT * 2.0 * rmax)[:, None] * np.ones((1, OUT))
    mx = ux * rn
    my = uy * rn

    out = np.zeros((OUT, OUT, 3), dtype="float32")

    # ---- the polar path ----
    if cfg["polar_epsg"] == target:
        # Same grid. Pure scale and offset — the image is not reprojected at all.
        px, py = mx, my
        native = True
    else:
        lat, lon = inverse_grid(target, mx, my)
        px, py = forward_grid(cfg["polar_epsg"], lat, lon)
        native = False

    inside = (np.abs(px) <= POLAR_EXTENT_M) & (np.abs(py) <= POLAR_EXTENT_M)
    ph, pw = polar_img.shape[:2]
    fx = (px + POLAR_EXTENT_M) / (2 * POLAR_EXTENT_M) * pw - 0.5
    fy = (POLAR_EXTENT_M - py) / (2 * POLAR_EXTENT_M) * ph - 0.5
    sampled = bilinear(polar_img, fx, fy)
    out[inside] = sampled[inside]

    # ---- the global fill, for the ring the polar tiles do not reach ----
    outside = ~inside
    if outside.any():
        lat, lon = inverse_grid(target, mx, my)
        gh, gw = global_img.shape[:2]
        gx = (lon + 180.0) / 360.0 * gw - 0.5
        gy = (90.0 - lat) / 180.0 * gh - 0.5
        gsamp = bilinear(global_img, gx, gy)
        out[outside] = gsamp[outside]

    # The square's corners are clipped away by the deck, which draws only r <= 1.
    # Reporting the fraction over the whole square would understate how much of
    # what the reader actually sees came from the polar tiles.
    drawn = (ux * ux + uy * uy) <= 1.0
    frac_native = float(inside.mean())
    frac_drawn = float(inside[drawn].mean())
    return np.clip(out, 0, 255).astype(np.uint8), {
        "polar_source_epsg": cfg["polar_epsg"],
        "target_epsg": target,
        "polar_path": ("scale and offset only — same grid, not reprojected"
                       if native else
                       f"reprojected EPSG:{cfg['polar_epsg']} -> EPSG:{target}"),
        "fraction_from_polar_tiles": round(frac_native, 4),
        "fraction_from_plate_carree": round(1.0 - frac_native, 4),
        "fraction_from_polar_tiles_within_drawn_disc": round(frac_drawn, 4),
        "rmax": rmax,
        "normalising_radius_m": rn,
        "polar_extent_m": POLAR_EXTENT_M,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None, help="YYYY-MM-DD for the true-colour layer")
    ap.add_argument("--out", default="data/imagery")
    ap.add_argument("--polar-px", type=int, default=2048)
    ap.add_argument("--global-px", type=int, default=4096)
    ap.add_argument("--quality", type=int, default=80)
    args = ap.parse_args()

    day = args.day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(args.out, exist_ok=True)
    from PIL import Image

    manifest = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "day": day,
        "out": OUT,
        "rmax": RMAX,
        "note": ("GIBS polar tile matrices stop at +/-4,194,304 m, which is r = 0.817 "
                 "on this disc, latitude 52.6. The disc is framed to 45, so the ring "
                 "beyond that is filled from EPSG:4326 plate carree."),
        "images": [],
    }

    for layer in LAYERS:
        gday = day if layer["timed"] else None
        gurl = getmap(4326, layer["gibs"], (-90, -180, 90, 180),
                      args.global_px, args.global_px // 2, gday)
        gbody, gstamp = fetch(gurl)
        global_img = as_array(gbody)
        print(f"{layer['key']}: global {global_img.shape} "
              f"{gstamp['bytes']/1024:.0f} KB")

        for hemi in ("N", "S"):
            epsg = HEMI[hemi]["polar_epsg"]
            purl = getmap(epsg, layer["gibs"],
                          (-POLAR_EXTENT_M, -POLAR_EXTENT_M, POLAR_EXTENT_M, POLAR_EXTENT_M),
                          args.polar_px, args.polar_px, gday)
            pbody, pstamp = fetch(purl)
            polar_img = as_array(pbody)

            img, info = build_one(hemi, layer, polar_img, global_img, gday)
            name = f"{layer['key']}_{hemi}.jpg"
            path = os.path.join(args.out, name)
            Image.fromarray(img).save(path, quality=args.quality, optimize=True,
                                      progressive=True)
            size = os.path.getsize(path)
            print(f"  {hemi}: {name} {size/1024:.0f} KB  "
                  f"{info['fraction_from_polar_tiles_within_drawn_disc']*100:.1f} % of the "
                  f"drawn disc from EPSG:{epsg} ({info['polar_path']})")
            manifest["images"].append({
                "layer": layer["key"], "nm": layer["nm"], "hemisphere": hemi,
                "file": name, "bytes": size,
                "gibs_layer": layer["gibs"], "time": gday,
                "sources": {"polar": pstamp, "global": gstamp},
                **info,
            })

    mp = os.path.join(args.out, "manifest.json")
    with io.open(mp, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    total = sum(i["bytes"] for i in manifest["images"])
    print(f"\n{mp}\n  {len(manifest['images'])} images, {total/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
