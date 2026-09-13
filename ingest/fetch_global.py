"""
fetch_global — the equirectangular sheet the globe needs.

The disc views draw baked polar squares. The globe is orthographic and shows the
whole sphere at once, so it needs one plate carree sheet per layer rather than
two polar squares. This fetches it from the same GIBS WMS build_imagery.py
already uses, at the same day, and records the bytes it got.

    python3 scripts/fetch_global.py --day 2026-09-11 --out data/imagery
"""
import argparse, hashlib, io, json, os, urllib.parse, urllib.request
from datetime import datetime, timezone
from PIL import Image

WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
UA = "olympus-imagery-ingest/2.0 (+build-time ingest, no runtime fetch)"
LAYERS = [
    {"key": "relief", "gibs": "BlueMarble_ShadedRelief_Bathymetry", "timed": False},
    {"key": "today",  "gibs": "MODIS_Terra_CorrectedReflectance_TrueColor", "timed": True},
]

def getmap(layer, w, h, day):
    q = {"SERVICE":"WMS","VERSION":"1.3.0","REQUEST":"GetMap","LAYERS":layer,
         "CRS":"EPSG:4326","BBOX":"-90.0,-180.0,90.0,180.0",
         "WIDTH":str(w),"HEIGHT":str(h),"FORMAT":"image/jpeg"}
    if day: q["TIME"] = day
    return WMS + "?" + urllib.parse.urlencode(q)

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        body = r.read()
    return body, {"url": url, "bytes": len(body),
                  "sha256": hashlib.sha256(body).hexdigest(),
                  "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--day", default=None)
    ap.add_argument("--out", default="data/imagery")
    ap.add_argument("--fetch-px", type=int, default=4096)
    ap.add_argument("--out-px", type=int, default=2048)
    ap.add_argument("--quality", type=int, default=80)
    a = ap.parse_args()
    day = a.day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    os.makedirs(a.out, exist_ok=True)
    recs = []
    for L in LAYERS:
        gday = day if L["timed"] else None
        url = getmap(L["gibs"], a.fetch_px, a.fetch_px // 2, gday)
        body, stamp = fetch(url)
        im = Image.open(io.BytesIO(body)).convert("RGB")
        if im.width != a.out_px:
            im = im.resize((a.out_px, a.out_px // 2), Image.LANCZOS)
        name = f"{L['key']}_G.jpg"
        path = os.path.join(a.out, name)
        im.save(path, quality=a.quality, optimize=True, progressive=True)
        size = os.path.getsize(path)
        print(f"{L['key']}: {im.width}x{im.height}  {size/1024:.0f} KB  (fetched {stamp['bytes']/1024:.0f} KB)")
        recs.append({"layer": L["key"], "file": name, "bytes": size,
                     "width": im.width, "height": im.height,
                     "gibs_layer": L["gibs"], "time": gday,
                     "projection": "EPSG:4326 plate carree, -180..180 / -90..90",
                     "source": stamp})
    mp = os.path.join(a.out, "manifest_global.json")
    json.dump({"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "day": day, "images": recs}, io.open(mp, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(mp, sum(r["bytes"] for r in recs) / 1024 / 1024, "MB")

if __name__ == "__main__":
    main()
