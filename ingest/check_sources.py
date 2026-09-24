#!/usr/bin/env python3
"""
check_sources — re-derive what the deck carries from the files it came from.

The deck log shows these results beside the values they check, dated, so a
reader can see which numbers were reproduced from source and when. Every check
here reads the publisher's own file; none of them reads the deck's earlier
output as its reference.

  1. extent method  For a few months, the extent of OSI SAF's monthly-mean
                    concentration file (the deck's method) and the mean of the
                    same month's daily extents (OSI SAF's and NSIDC's method),
                    beside OSI SAF's published index for that month.
  2. fast track     Whether the provisional file for the newest month has been
                    replaced by a consolidated one, and by how much it moved.
  3. RAPID          Every monthly value on the AMOC gauge, recomputed from
                    moc_transports.nc.
  4. ENSO           The RONI and weekly relative Nino-3.4 series in the living
                    layer, compared value for value with NOAA CPC's files.

  python ingest/check_sources.py dist/deck.html data/checks/sources.json

Needs numpy and netCDF4 (OPeNDAP), and network access to thredds.met.no,
rapid.ac.uk and cpc.ncep.noaa.gov.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import urllib.request

import numpy as np
import netCDF4 as nc

TDS = "https://thredds.met.no/thredds"
REP = TDS + "/dodsC/osisaf/met.no/reprocessed/ice"
CAT = TDS + "/catalog/osisaf/met.no/reprocessed/ice"
TREE = {"cdr-v3p0": "conc_450a_files", "icdr-v3p0": "conc_cra_files",
        "icdr-v3p0-amsr": "conc_438_files", "icdrft-v3p0-amsr": "conc_438_files"}
RAPID = "https://rapid.ac.uk/sites/default/files/rapid_data/moc_transports.nc"
RONI = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
WEEKLY = "https://www.cpc.ncep.noaa.gov/data/indices/rel_wksst9120.txt"
SII = "data/osi/sie_index_v3p0.json"

# One month from each record, chosen where the two methods disagree most, plus
# one in the Arctic that the deck's explainers quote.
EXTENT_MONTHS = [("sh", "cdr-v3p0", "201912"), ("nh", "cdr-v3p0", "201209"),
                 ("nh", "icdr-v3p0-amsr", "202606"), ("sh", "icdr-v3p0-amsr", "202606")]


def payload(page, name):
    s = open(page, encoding="utf-8").read()
    m = re.search(r"\nconst " + name + r"\s*=\s*", s)
    j = s.find("\n", m.end())
    return json.loads(s[m.end():j].rstrip().rstrip(";"))


def get(url):
    with urllib.request.urlopen(url, timeout=180) as r:
        return r.read()


def conc(url):
    for attempt in range(3):
        try:
            d = nc.Dataset(url)
            try:
                c = np.ma.filled(d["ice_conc"][0].astype("f8"), np.nan)
                created = getattr(d, "date_created", None)
            finally:
                d.close()
            return c, created
        except Exception as e:                                    # noqa: BLE001
            err = e
    raise err


def ext(c, gt=False):
    ok = np.isfinite(c) & ((c > 15.0) if gt else (c >= 15.0))
    return float(np.count_nonzero(ok) * 625.0 / 1e6)


def extent_method(sii):
    out = []
    for h, rec, ym in EXTENT_MONTHS:
        y, m = ym[:4], ym[4:]
        tree = TREE[rec]
        xml = get(f"{CAT}/{tree}/{y}/{m}/catalog.xml").decode()
        names = sorted(set(re.findall(rf'name="(ice_conc_{h}_ease2-250_{rec}_{ym}\d{{6}}\.nc)"', xml)))
        # one file at a time: the netCDF-C library under netCDF4 is not thread-safe
        daily = [conc(f"{REP}/{tree}/{y}/{m}/{n}")[0] for n in names]
        monthly, _ = conc(f"{REP}/{tree}/monthly/{y}/ice_conc_{h}_ease2-250_{rec}_{ym}.nc")
        H = sii["hemi"][h]
        k = (int(ym[:4]) * 12 + int(ym[4:])) - (int(H["m0"][:4]) * 12 + int(H["m0"][4:]))
        pub = H["v"][k] if 0 <= k < len(H["v"]) else None
        row = {"hemi": h, "ym": ym, "record": rec, "days": len(names),
               "monthly_field": round(ext(monthly), 3),
               "daily_mean_ge15": round(float(np.mean([ext(c) for c in daily])), 3),
               "daily_mean_gt15": round(float(np.mean([ext(c, True) for c in daily])), 3),
               "published_index": None if pub is None else round(pub / 1e6, 3)}
        out.append(row)
        print(f"  extent {h} {ym} {rec}: field {row['monthly_field']}  daily mean {row['daily_mean_gt15']}  published {row['published_index']}")
    return out


def fast_track(osi):
    out = []
    for h in ("nh", "sh"):
        H = osi["hemi"][h]
        last = H["runs"][-1]
        if not last[3]:
            continue
        t = int(H["m0"][:4]) * 12 + int(H["m0"][4:]) - 1 + H["ymo"][-1]
        ym = f"{t // 12}{t % 12 + 1:02d}"
        y = ym[:4]
        ft, ft_made = conc(f"{REP}/{TREE[last[2]]}/monthly/{y}/ice_conc_{h}_ease2-250_{last[2]}_{ym}.nc")
        cons = last[2].replace("icdrft", "icdr")
        row = {"hemi": h, "ym": ym, "fast_track_file": f"ice_conc_{h}_ease2-250_{last[2]}_{ym}.nc",
               "fast_track": round(ext(ft), 3), "fast_track_created": ft_made, "deck": H["ext"][-1]}
        try:
            c, made = conc(f"{REP}/{TREE[cons]}/monthly/{y}/ice_conc_{h}_ease2-250_{cons}_{ym}.nc")
            row.update({"consolidated_file": f"ice_conc_{h}_ease2-250_{cons}_{ym}.nc",
                        "consolidated": round(ext(c), 3), "consolidated_created": made})
        except Exception:                                         # noqa: BLE001
            row.update({"consolidated_file": None})
        out.append(row)
        print(f"  fast track {h} {ym}: {row}")
    return out


def rapid(ex):
    raw = get(RAPID)
    with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as f:
        f.write(raw)
        path = f.name
    d = nc.Dataset(path)
    t = nc.num2date(d["time"][:], d["time"].units, only_use_cftime_datetimes=False)
    ym = np.array([f"{x.year}{x.month:02d}" for x in t])
    A = ex["amoc"]
    res = {"url": RAPID, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
           "version": getattr(d, "version", None), "created": getattr(d, "Creation_date", None),
           "doi": getattr(d, "DOI", None), "samples": int(len(t)),
           "first": str(t[0])[:10], "last": str(t[-1])[:10], "vars": {}}
    for k, v in {"moc": "moc_mar_hc10", "gs": "t_gs10", "ek": "t_ek10", "umo": "t_umo10"}.items():
        x = np.ma.filled(d[v][:].astype("f8"), np.nan)
        x[np.abs(x) > 1e3] = np.nan                     # _FillValue is -99999
        bad = [m for i, m in enumerate(A["months"])
               if abs(round(float(np.nanmean(x[ym == m])), 3) - A[k][i]) > 0.0005]
        res["vars"][k] = {"source": v, "months": len(A["months"]), "equal": len(A["months"]) - len(bad),
                          "fill_samples": int(np.count_nonzero(np.isnan(x))), "mismatch": bad[:12]}
    d.close()
    os.unlink(path)
    print(f"  RAPID {res['version']}: " + ", ".join(f"{k} {v['equal']}/{v['months']}" for k, v in res["vars"].items()))
    return res


def enso(live):
    E = live["enso"]
    rows = [l.split() for l in get(RONI).decode().splitlines() if l.strip() and not l.startswith("SEAS")]
    vals = [float(r[-1]) for r in rows if len(r) >= 3]
    n = len(E["roni"]["v"])
    roni = {"url": RONI, "values": n, "equal": sum(a == b for a, b in zip(vals[:n], E["roni"]["v"])),
            "source_values": len(vals)}
    wk = {}
    for l in get(WEEKLY).decode().splitlines():
        f = l.split()
        if len(f) == 5 and f[0][:2].isdigit():
            wk[dt.datetime.strptime(f[0], "%d%b%Y").date()] = float(f[3])
    t0 = dt.date.fromisoformat(E["weekly"]["series_t0"])
    s = E["weekly"]["series34"]
    weekly = {"url": WEEKLY, "values": len(s),
              "equal": sum(wk.get(t0 + dt.timedelta(days=7 * i)) == v for i, v in enumerate(s)),
              "first": str(t0), "last": str(t0 + dt.timedelta(days=7 * (len(s) - 1)))}
    print(f"  RONI {roni['equal']}/{roni['values']}, weekly {weekly['equal']}/{weekly['values']}")
    return {"roni": roni, "weekly": weekly, "live_built": live["meta"]["built"]}


def main():
    page = sys.argv[1] if len(sys.argv) > 1 else "dist/deck.html"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/checks/sources.json"
    sii = json.load(open(SII, encoding="utf-8"))
    doc = {"checked_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "by": "ingest/check_sources.py",
           "extent_method": extent_method(sii),
           "fast_track": fast_track(payload(page, "OSI")),
           "rapid": rapid(payload(page, "EX")),
           "enso": enso(payload(page, "LIVE"))}
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(doc, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
