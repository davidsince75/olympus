#!/usr/bin/env python3
"""
Olympus — the living layer, rebuilt.

The script that produced the deck's and the Atlas's `LIVE` payload
(`build_events.py`, 4 Sep 2026) died with its container. Everything since then
has been re-publishing one frozen snapshot taken at 2026-09-04T10:31Z, and on
24 Sep the header was still showing it with green dots. This is that script,
written again against the payload shape the surfaces already read, so nothing
downstream changes.

Four sources, no account and no key on any of them:

  aurora  NOAA SWPC OVATION-Prime latest            ~30 min   MODEL
  kp      NOAA SWPC planetary K index, 1-minute     ~1 min    MEAS
  drift   EUMETSAT OSI SAF OSI-405 low-res drift    ~2 days   MEAS  (flag 30 only)
  sar     Copernicus Data Space, Sentinel-1         ~3 h      MEAS  (footprints)
  enso    NOAA CPC + OISST v2.1 — the featured event, see ingest/enso.py

Every layer carries its own observation time. The build time is recorded once,
in `meta.built`, and is never shown as the age of anything.

  python ingest/build_events.py data/events/live.json [--prev dist/deck.html]

`--prev` carries forward blocks this script does not own (the `gibs`
descriptor) from the payload currently in a surface, byte for byte.

Output is compact JSON written with allow_nan=False: a bare NaN is valid
JavaScript and an all-NaN layer draws nothing while passing every count check.
"""
import argparse
import base64
import datetime as dt
import io
import json
import math
import os
import re
import sys
import tempfile
import urllib.parse
import urllib.request

UA = {"User-Agent": "Olympus/1.0 (polar data deck; build-time ingest)"}
NOW = dt.datetime.now(dt.timezone.utc)


def get(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ------------------------------------------------------------------ aurora
def aurora():
    url = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
    d = json.loads(get(url))
    lat0, nlat, nlon = 45, 46, 360
    nh = bytearray(nlon * nlat)
    sh = bytearray(nlon * nlat)
    seen = 0
    for lon, lat, v in d["coordinates"]:
        lon = int(lon) % 360
        lat = int(lat)
        v = max(0, min(255, int(round(v))))
        if lat >= lat0:
            nh[(lat - lat0) * nlon + lon] = v
            seen += 1
        elif lat <= -lat0:
            sh[(-lat - lat0) * nlon + lon] = v
            seen += 1
    # Every cell of both caps must have been written: 2 x 46 x 360.
    if seen != 2 * nlat * nlon:
        raise SystemExit(f"ABORT aurora: expected {2*nlat*nlon} polar cells, got {seen}")
    obs = d["Observation Time"].replace(".000", "")
    fc = d["Forecast Time"].replace(".000", "")
    return {
        "observed": obs if obs.endswith("Z") else obs + "Z",
        "forecast": fc if fc.endswith("Z") else fc + "Z",
        "lat0": lat0, "nlon": nlon, "nlat": nlat,
        "nh": base64.b64encode(bytes(nh)).decode(),
        "sh": base64.b64encode(bytes(sh)).decode(),
        "source": "NOAA SWPC OVATION-Prime",
        "latency": "~30 min",
        "mode": "MODEL",
        "note": ("A model, not an image. OVATION converts solar-wind measurements into a "
                 "probability of auroral emission. It is stamped MODEL for that reason."),
        "url": url,
        "_max": {"nh": max(nh), "sh": max(sh)},
    }


# ------------------------------------------------------------------ kp
def kp():
    url = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    rows = json.loads(get(url))
    rows = [r for r in rows if r.get("estimated_kp") is not None]
    if not rows:
        raise SystemExit("ABORT kp: empty feed")
    last = rows[-1]
    # six hours at three-minute spacing, newest last — the shape the surfaces read
    series = [[r["time_tag"] + "Z", round(float(r["estimated_kp"]), 2)] for r in rows[::-1][::3]][:120][::-1]
    return {
        "latest": round(float(last["estimated_kp"]), 2),
        "time": last["time_tag"] + "Z",
        "series": series,
        "source": "NOAA SWPC planetary K index",
        "latency": "1 min",
        "mode": "MEAS",
        "url": url,
    }


# ------------------------------------------------------------------ drift
THREDDS = "https://thredds.met.no/thredds"
DRIFT_DIR = "osisaf/met.no/ice/drift_lr/merged"


def latest_drift_file(hemi):
    for back in (0, 1):
        y, m = NOW.year, NOW.month - back
        if m == 0:
            y, m = y - 1, 12
        cat = f"{THREDDS}/catalog/{DRIFT_DIR}/{y:04d}/{m:02d}/catalog.xml"
        try:
            xml = get(cat).decode("utf-8", "replace")
        except Exception:
            continue
        names = sorted(set(re.findall(
            rf'name="(ice_drift_{hemi}_polstere-625_multi-oi_\d{{12}}-\d{{12}}\.nc)"', xml)))
        if names:
            return f"{y:04d}/{m:02d}", names[-1]
    raise SystemExit(f"ABORT drift: no {hemi} file in the last two months")


def drift_one(hemi):
    import netCDF4 as nc
    import numpy as np
    ym, name = latest_drift_file(hemi)
    raw = get(f"{THREDDS}/fileServer/{DRIFT_DIR}/{ym}/{name}", timeout=180)
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as fh:
        fh.write(raw)
        path = fh.name
    try:
        d = nc.Dataset(path)
        flag = np.ma.filled(d["status_flag"][0], 0)
        lat0 = np.ma.filled(d["lat"][:], np.nan)
        lon0 = np.ma.filled(d["lon"][:], np.nan)
        lat1 = np.ma.filled(d["lat1"][0], np.nan)
        lon1 = np.ma.filled(d["lon1"][0], np.nan)
        ok = (flag == 30) & np.isfinite(lat0) & np.isfinite(lat1) & np.isfinite(lon0) & np.isfinite(lon1)
        v = [[round(float(a), 2), round(float(b), 2), round(float(c), 2), round(float(e), 2)]
             for a, b, c, e in zip(lat0[ok], lon0[ok], lat1[ok], lon1[ok])]
        d.close()
    finally:
        os.unlink(path)
    m = re.search(r"(\d{12})-(\d{12})", name)
    t0 = dt.datetime.strptime(m.group(1), "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)
    t1 = dt.datetime.strptime(m.group(2), "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)
    return {"t0": iso(t0), "t1": iso(t1), "file": name, "n": len(v), "v": v}


def drift():
    return {
        "nh": drift_one("nh"),
        "sh": drift_one("sh"),
        "source": "EUMETSAT OSI SAF low-resolution sea-ice drift (OSI-405)",
        "latency": "~2 days",
        "mode": "MEAS",
        "note": ("Each vector is where a patch of ice was 48 hours ago and where it is now, tracked "
                 "by pattern matching between passive-microwave images. Only vectors the producer "
                 "flags as nominal quality are drawn."),
        "url": f"{THREDDS}/catalog/{DRIFT_DIR}/catalog.html",
    }


# ------------------------------------------------------------------ sar
CDSE = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CAPS = [
    ("nh", "POLYGON((-180 60,0 60,0 89.9,-180 89.9,-180 60))"),
    ("nh", "POLYGON((0 60,180 60,180 89.9,0 89.9,0 60))"),
    ("sh", "POLYGON((-180 -89.9,0 -89.9,0 -60,-180 -60,-180 -89.9))"),
    ("sh", "POLYGON((0 -89.9,180 -89.9,180 -60,0 -60,0 -89.9))"),
]
PREF = ["GRDM", "GRDH", "SLC", "OCN", "RAW"]
NAME = re.compile(r"^(S1[A-D])_(EW|IW|SM|WV|S\d)_([A-Z]{3,4})_*_?\w*?_(\d{8}T\d{6})_(\d{8}T\d{6})_")


def sar(hours=18):
    since = NOW - dt.timedelta(hours=hours)
    acq = {}
    for hemi, poly in CAPS:
        flt = (f"Collection/Name eq 'SENTINEL-1' and ContentDate/Start gt "
               f"{since.strftime('%Y-%m-%dT%H:%M:%S.000Z')} and "
               f"OData.CSC.Intersects(area=geography'SRID=4326;{poly}')")
        skip = 0
        while True:
            q = urllib.parse.urlencode({"$filter": flt, "$top": "1000", "$skip": str(skip),
                                        "$orderby": "ContentDate/Start desc"})
            page = json.loads(get(f"{CDSE}?{q}")).get("value", [])
            for p in page:
                m = NAME.match(p["Name"])
                if not m:
                    continue
                sat, mode, prod, a, b = m.groups()
                if mode == "WV":          # wave-mode vignettes are not swaths
                    continue
                gf = p.get("GeoFootprint") or {}
                if gf.get("type") != "Polygon":
                    continue
                ring = gf["coordinates"][0]
                # centred poleward of 60 degrees — a swath that only clips the cap
                # from Scandinavia or Patagonia is not a polar acquisition
                clat = sum(c[1] for c in ring[:-1]) / max(1, len(ring) - 1)
                if (hemi == "nh" and clat < 60) or (hemi == "sh" and clat > -60):
                    continue
                key = (sat, mode, a, b)
                rec = acq.get(key)
                if rec is None:
                    start = p["ContentDate"]["Start"][:19] + "Z"
                    pub = (p.get("PublicationDate") or "")[:19] + "Z"
                    rec = acq[key] = {
                        "hemi": hemi, "name": p["Name"].replace(".SAFE", ""), "sat": sat,
                        "mode": mode, "product": prod, "products": [], "start": start,
                        "published": pub,
                        "poly": [[round(c[0], 2), round(c[1], 2)] for c in ring],
                    }
                if prod not in rec["products"]:
                    rec["products"].append(prod)
            if len(page) < 1000:
                break
            skip += 1000
    items = []
    for rec in acq.values():
        rec["products"].sort(key=lambda x: PREF.index(x) if x in PREF else 99)
        rec["product"] = rec["products"][0]
        items.append(rec)
    items.sort(key=lambda r: r["start"], reverse=True)
    return {
        "since": since.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "hours": hours,
        "n": len(items),
        "items": items,
        "source": "Copernicus Data Space Ecosystem — Sentinel-1 catalogue",
        "latency": "~3 h from acquisition to catalogue",
        "mode": "MEAS",
        "note": ("Real acquisition footprints, not a simulated ground track. Each is a strip the "
                 "radar actually imaged, with its own timestamp. One outline per acquisition; the "
                 "product levels made from it are listed with it."),
        "url": "https://catalogue.dataspace.copernicus.eu/",
    }


# ------------------------------------------------------------------ assemble
def prev_live(path):
    s = open(path, encoding="utf-8").read()
    i = s.find("const LIVE = ")
    if i < 0:
        return {}
    j = s.find("\n", i)
    return json.loads(s[i + len("const LIVE = "):j].rstrip().rstrip(";"))


def finite(o, where="LIVE"):
    if isinstance(o, float) and not math.isfinite(o):
        raise SystemExit(f"ABORT non-finite value at {where}")
    if isinstance(o, dict):
        for k, v in o.items():
            finite(v, f"{where}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            finite(v, f"{where}[{i}]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--prev", help="surface whose LIVE payload supplies blocks this script does not own")
    a = ap.parse_args()

    L = {"meta": {"built": iso(NOW),
                  "note": "Each layer carries its own observation time. Never the build time."}}
    au = aurora()
    mx = au.pop("_max")
    L["aurora"] = au
    L["kp"] = kp()
    L["drift"] = drift()
    L["sar"] = sar()
    # the featured event (ingest/enso.py): NOAA's status, indices and this week's
    # SST anomaly field, cross-checked against CPC before it is accepted
    from enso import enso
    L["enso"] = enso()
    if a.prev:
        P = prev_live(a.prev)
        if "gibs" in P:
            L["gibs"] = P["gibs"]
    finite(L)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    txt = json.dumps(L, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    open(a.out, "w", encoding="utf-8", newline="\n").write(txt)
    print(f"aurora  observed {L['aurora']['observed']}  max nh {mx['nh']} sh {mx['sh']}")
    print(f"kp      {L['kp']['latest']} at {L['kp']['time']}  ({len(L['kp']['series'])} points)")
    for h in ("nh", "sh"):
        D = L["drift"][h]
        print(f"drift   {h} {D['t0']} -> {D['t1']}  {D['n']} nominal vectors")
    print(f"sar     {L['sar']['n']} acquisitions since {L['sar']['since']}")
    E = L["enso"]
    print(f"enso    {E['status']['alert']} ({E['status']['issued']}) · Niño-3.4 week {E['weekly']['week']} "
          f"relative {E['weekly']['rel']['nino34']:+.1f} / traditional {E['weekly']['trad34']:+.1f} · "
          f"box check {E['field']['n34_check']:+.2f} · RONI {E['roni']['last']} {E['roni']['latest']:+.2f}")
    print(f"wrote {a.out}  {len(txt)/1e3:.0f} KB")


if __name__ == "__main__":
    main()
