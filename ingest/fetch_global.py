"""
fetch_global — the equirectangular sheet the globe needs.

The disc views draw baked polar squares. The globe is orthographic and shows the
whole sphere at once, so it needs one plate carree sheet per layer rather than
two polar squares.

Why the true-colour sheet is a composite
----------------------------------------
On the polar squares a single day of MODIS Terra is complete, because the orbits
converge and overlap at high latitude. Globally it is not: adjacent orbits leave
un-imaged wedges between them, widest at the equator, and on a globe those read
as a broken render rather than as data. Measured here, at 2048 x 1024:

    one day     23S-23N   11.1 % un-imaged
    two days    23S-23N    0.0 %

So the global sheet is composited over --days days, most recent day first, each
pixel taken from the most recent day that imaged it. Two days is the default
because two is what it takes; more would only age the picture. What stays black
after that is polar night, which no number of days will fill and which the deck
explains rather than hides.

The manifest records every day used and the bytes fetched for each.

    python3 ingest/fetch_global.py --day 2026-09-11 --out data/imagery
"""
import argparse, hashlib, io, json, os, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
import numpy as np
from PIL import Image

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
UA = "olympus-imagery-ingest/2.0 (+build-time ingest, no runtime fetch)"

# A GIBS true-colour pixel with no observation comes back as black. Real night
# is black too, which is why the composite fills swath gaps and leaves polar
# night alone: a gap is imaged on an adjacent day, polar night is not.
DARK = 14

LAYERS = [
    {"key": "relief", "gibs": "BlueMarble_ShadedRelief_Bathymetry", "timed": False},
    {"key": "today",  "gibs": "MODIS_Terra_CorrectedReflectance_TrueColor", "timed": True},
]


def getmap(layer, w, h, day):
    q = {"SERVICE": "WMS", "VERSION": "1.3.0", "REQUEST": "GetMap", "LAYERS": layer,
         "CRS": "EPSG:4326", "BBOX": "-90.0,-180.0,90.0,180.0",
         "WIDTH": str(w), "HEIGHT": str(h), "FORMAT": "image/jpeg"}
    if day:
        q["TIME"] = day
    return WMS + "?" + urllib.parse.urlencode(q)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return body, {"url": url, "bytes": len(body),
                  "sha256": hashlib.sha256(body).hexdigest(),
                  "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}


def as_array(body):
    return np.asarray(Image.open(io.BytesIO(body)).convert("RGB"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None)
    ap.add_argument("--days", type=int, default=2,
                    help="days composited into the timed sheet, most recent first")
    ap.add_argument("--out", default="data/imagery")
    ap.add_argument("--fetch-px", type=int, default=4096)
    ap.add_argument("--out-px", type=int, default=2048)
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()

    day0 = a.day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(a.out, exist_ok=True)
    d0 = datetime.strptime(day0, "%Y-%m-%d")
    recs = []

    for L in LAYERS:
        days = ([(d0 - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(a.days)]
                if L["timed"] else [None])
        comp = None
        dark = None
        stamps = []
        for d in days:
            body, stamp = fetch(getmap(L["gibs"], a.fetch_px, a.fetch_px // 2, d))
            stamp["day"] = d
            stamps.append(stamp)
            arr = as_array(body)
            this_dark = arr.astype(np.int16).sum(2) < DARK
            if comp is None:
                comp, dark = arr.copy(), this_dark.copy()
            else:
                fill = dark & ~this_dark
                comp[fill] = arr[fill]
                dark &= this_dark

        # what is still black, reported by band, so the claim can be checked
        h = comp.shape[0]
        lat = 90.0 - (np.arange(h) + 0.5) / h * 180.0
        trop = (lat >= -23) & (lat <= 23)
        unimaged = {"tropics_23S_23N": round(float(dark[trop].mean()), 4),
                    "whole_sheet": round(float(dark.mean()), 4)}

        im = Image.fromarray(comp)
        if im.width != a.out_px:
            im = im.resize((a.out_px, a.out_px // 2), Image.LANCZOS)
        name = f"{L['key']}_G.jpg"
        path = os.path.join(a.out, name)
        im.save(path, quality=a.quality, optimize=True, progressive=True)
        size = os.path.getsize(path)
        print(f"{L['key']}: {im.width}x{im.height}  {size/1024:.0f} KB  "
              f"{len(days)} day(s)  tropics unimaged {unimaged['tropics_23S_23N']*100:.1f} %")
        recs.append({"layer": L["key"], "file": name, "bytes": size,
                     "width": im.width, "height": im.height,
                     "gibs_layer": L["gibs"],
                     "time": days[0], "days": [d for d in days if d],
                     "composite": ("most recent day first; each pixel from the most recent "
                                   "day that imaged it" if len(days) > 1 else None),
                     "unimaged_fraction": unimaged,
                     "projection": "EPSG:4326 plate carree, -180..180 / -90..90",
                     "sources": stamps})

    mp = os.path.join(a.out, "manifest_global.json")
    json.dump({"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "day": day0, "days": a.days, "images": recs},
              io.open(mp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(mp, f"{sum(r['bytes'] for r in recs)/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()
