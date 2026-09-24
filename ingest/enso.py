#!/usr/bin/env python3
"""
Olympus — the featured event: El Niño, from NOAA's own numbers.

Called by build_events.py so it refreshes with the rest of the living layer.
Everything here is fetched at build time and stamped; nothing is typed.

  status     NOAA CPC ENSO Diagnostic Discussion — alert status, date, synopsis,
             date of the next discussion (monthly)
  weekly     CPC weekly Niño indices from OISST v2.1: the RELATIVE series (the
             official one since Feb 2026) for all four regions, and the
             traditional Niño-3.4 beside it, so the gap between them can be shown
  roni       CPC Relative Oceanic Niño Index, every 3-month season since 1950
  field      NOAA OISST v2.1 daily SST anomaly (vs 1991-2020), averaged over the
             same seven days as CPC's latest weekly index, block-averaged to 1°
             over the tropical Pacific, contoured at -1, +1, +2, +3 °C

The field is checked against CPC before it is used: the mean anomaly we compute
over the Niño-3.4 box must reproduce CPC's traditional weekly Niño-3.4 value for
the same week to within 0.25 °C, or the build stops. A map that disagreed with
the index printed beside it would be worse than no map.

  python ingest/enso.py            # standalone check: prints what it would bake
"""
import datetime as dt
import html
import os
import re
import tempfile
import urllib.request

CPC = "https://www.cpc.ncep.noaa.gov"
DISC = CPC + "/products/analysis_monitoring/enso_advisory/ensodisc.shtml"
REL_WK = CPC + "/data/indices/rel_wksst9120.txt"
TRAD_WK = CPC + "/data/indices/wksst9120.for"
RONI = CPC + "/data/indices/RONI.ascii.txt"
OISST = "https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr"
UA = {"User-Agent": "Olympus/1.0 (polar data deck; build-time ingest)"}

# The Pacific window the contours are drawn in, continuous in longitude (east),
# so the dateline is not a seam: 120°E .. 290°E (= 70°W), 20°S .. 20°N — the tropics,
# because El Niño is a tropical event and a marine heatwave off California is not it.
LON0, LON1, LAT0, LAT1 = 120, 290, -20, 20
LEVELS = [-1.0, 1.0, 2.0, 3.0]
MON = {m: i + 1 for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"])}


def get(url, timeout=120):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.read()


def text_of(h):
    t = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", "", h)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def status():
    t = text_of(get(DISC).decode("utf-8", "replace"))
    m = re.search(r"CLIMATE PREDICTION CENTER/NCEP/NWS\s+(\d{1,2} \w+ \d{4})\s+ENSO Alert System Status:\s*(.+?)\s*\n", t)
    if not m:
        raise SystemExit("ABORT enso: could not find the alert status in the CPC discussion")
    issued = dt.datetime.strptime(m.group(1), "%d %B %Y").date().isoformat()
    alert = m.group(2).strip()
    known = ("El Niño Advisory", "El Niño Watch", "La Niña Advisory", "La Niña Watch",
             "Not Active", "Final El Niño Advisory", "Final La Niña Advisory")
    if alert not in known:
        raise SystemExit(f"ABORT enso: unrecognised alert status {alert!r}")
    s = re.search(r"Synopsis:\s*(.+?)\n", t)
    # NOAA's probabilistic statements, quoted verbatim and never reworded: every
    # sentence of the discussion body that states a chance, minus the synopsis
    body = t[t.find("Synopsis:"):t.find("This discussion is a consolidated")]
    chances = []
    for sent in re.split(r"(?<=[.])\s+", body):
        sent = re.sub(r"\s*\[Figs?\.[^\]]*\]", "", sent).strip()
        if "% chance" in sent and not sent.startswith("Synopsis") and not sent.startswith("In summary"):
            chances.append(re.sub(r"\s+([.,)])", r"\1", sent))
    nxt = re.search(r"next ENSO Diagnostics? Discussion is scheduled for (\d{1,2} \w+ \d{4})", t)
    return {
        "alert": alert,
        "issued": issued,
        "synopsis": s.group(1).strip() if s else "",
        "next": dt.datetime.strptime(nxt.group(1), "%d %B %Y").date().isoformat() if nxt else None,
        "outlook": chances[:2],
        "url": DISC,
    }


def week_date(tok):
    # "16SEP2026" -> date
    return dt.date(int(tok[5:9]), MON[tok[2:5]], int(tok[0:2]))


def weekly():
    rel = []
    for line in get(REL_WK).decode().splitlines():
        p = line.split()
        if len(p) == 5 and re.match(r"\d{2}[A-Z]{3}\d{4}$", p[0]):
            rel.append((week_date(p[0]), [float(x) for x in p[1:]]))
    trad = {}
    for line in get(TRAD_WK).decode().splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)$", line)
        if not m:
            continue
        nums = re.findall(r"-?\d+\.\d", m.group(2))   # SST SSTA pairs, fixed width, no spaces before minus
        if len(nums) == 8:
            trad[week_date(m.group(1))] = float(nums[5])  # Niño-3.4 SSTA
    last_d, last_v = rel[-1]
    if last_d not in trad:
        raise SystemExit(f"ABORT enso: traditional weekly index has no week {last_d}")
    keep = rel[-157:]  # three years of weeks
    return {
        "week": last_d.isoformat(),
        "rel": {"nino12": last_v[0], "nino3": last_v[1], "nino34": last_v[2], "nino4": last_v[3]},
        "trad34": trad[last_d],
        "series_t0": keep[0][0].isoformat(),
        "series34": [v[2] for _, v in keep],
        "url": REL_WK,
    }


def roni():
    rows = []
    for line in get(RONI).decode().splitlines()[1:]:
        p = line.split()
        if len(p) == 3:
            rows.append((p[0], int(p[1]), float(p[2])))
    peak = max(rows, key=lambda r: r[2])
    return {
        "t0": f"{rows[0][0]} {rows[0][1]}",
        "last": f"{rows[-1][0]} {rows[-1][1]}",
        "latest": rows[-1][2],
        "peak": {"season": f"{peak[0]} {peak[1]}", "value": peak[2]},
        "v": [r[2] for r in rows],
        "url": RONI,
    }


def field(center):
    """Weekly-mean OISST anomaly for the 7 days centred on `center`, 1°, Pacific."""
    import numpy as np
    import netCDF4 as nc
    days = [center + dt.timedelta(days=k) for k in range(-3, 4)]
    acc, cnt, used = None, None, []
    for d in days:
        grid = None
        for suffix in ("", "_preliminary"):
            url = f"{OISST}/{d:%Y%m}/oisst-avhrr-v02r01.{d:%Y%m%d}{suffix}.nc"
            try:
                raw = get(url, timeout=180)
            except Exception:
                continue
            with tempfile.NamedTemporaryFile(suffix=".nc", delete=False) as fh:
                fh.write(raw)
                path = fh.name
            try:
                ds = nc.Dataset(path)
                a = np.ma.filled(ds["anom"][0, 0].astype("f8"), np.nan)
                ice = np.ma.filled(ds["ice"][0, 0].astype("f8"), 0.0)
                lat = ds["lat"][:].astype("f8")
                lon = ds["lon"][:].astype("f8")
                ds.close()
            finally:
                os.unlink(path)
            a[ice > 0.15] = np.nan
            grid = (a, lat, lon)
            used.append(f"{d:%Y%m%d}{suffix}")
            break
        if grid is None:
            continue
        a, lat, lon = grid
        if acc is None:
            acc = np.zeros_like(a); cnt = np.zeros_like(a)
        ok = np.isfinite(a)
        acc[ok] += a[ok]; cnt[ok] += 1
    if len(used) < 5:
        raise SystemExit(f"ABORT enso: only {len(used)} OISST days available around {center}")
    wk = np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)

    # Niño-3.4 box mean on the 0.25° grid, cosine-weighted, against CPC's own value
    la = (lat >= -5) & (lat <= 5)
    lo = (lon >= 190) & (lon <= 240)
    box = wk[np.ix_(la, lo)]
    w = np.cos(np.deg2rad(lat[la]))[:, None] * np.isfinite(box)
    n34 = float(np.nansum(np.nan_to_num(box) * w) / w.sum())

    # 1° block means over the Pacific window (lon in 0..360 on this grid)
    li = (lat >= LAT0) & (lat < LAT1)
    lj = (lon >= LON0) & (lon < LON1)
    sub = wk[np.ix_(li, lj)]
    ny, nx = sub.shape[0] // 4, sub.shape[1] // 4
    blk = sub[:ny * 4, :nx * 4].reshape(ny, 4, nx, 4)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)   # all-land blocks are NaN, by design
        g1 = np.nanmean(np.nanmean(blk, axis=3), axis=1)
    glat = LAT0 + 0.5 + np.arange(ny)
    glon = LON0 + 0.5 + np.arange(nx)
    return g1, glat, glon, n34, used


def contours(g1, glat, glon):
    import numpy as np
    import contourpy
    # a light 3x3 smoothing so the lines follow the weekly pattern, not single cells;
    # land stays NaN and breaks the lines, which is correct
    k = np.ones((3, 3))
    pad = np.pad(g1, 1, mode="edge")
    fin = np.isfinite(pad)
    num = sum(np.nan_to_num(pad)[i:i + g1.shape[0], j:j + g1.shape[1]] * k[i, j]
              for i in range(3) for j in range(3))
    den = sum(fin[i:i + g1.shape[0], j:j + g1.shape[1]] * k[i, j] for i in range(3) for j in range(3))
    sm = np.where(np.isfinite(g1), num / np.maximum(den, 1), np.nan)
    gen = contourpy.contour_generator(glon, glat, np.ma.masked_invalid(sm), name="serial")
    out = []
    for lev in LEVELS:
        lines = []
        for seg in gen.lines(lev):
            if len(seg) < 6:           # drop specks: a contour a few cells long is noise at this scale
                continue
            flat = []
            for x, y in seg:
                flat += [round(float(x), 1), round(float(y), 1)]
            lines.append(flat)
        out.append({"level": lev, "lines": lines})
    return out


def enso():
    st = status()
    wk = weekly()
    rn = roni()
    center = dt.date.fromisoformat(wk["week"])
    g1, glat, glon, n34, used = field(center)
    if abs(n34 - wk["trad34"]) > 0.25:
        raise SystemExit(f"ABORT enso: OISST Niño-3.4 box mean {n34:+.2f} does not reproduce CPC's "
                         f"traditional weekly value {wk['trad34']:+.2f} for the week of {center}")
    cs = contours(g1, glat, glon)
    return {
        "event": "El Niño" if "El Niño" in st["alert"] else "La Niña" if "La Niña" in st["alert"] else "ENSO-neutral",
        "status": st,
        "weekly": wk,
        "roni": rn,
        "field": {
            "week": wk["week"], "days": used, "n34_check": round(n34, 2),
            "window": [LON0, LON1, LAT0, LAT1], "res_deg": 1, "levels": LEVELS,
            "contours": cs, "base": "1991-2020",
            "source": "NOAA OISST v2.1 daily SST anomaly, 7-day mean",
            "url": "https://www.ncei.noaa.gov/products/optimum-interpolation-sst",
        },
        "box": {"name": "Niño-3.4", "lat": [-5, 5], "lon": [-170, -120]},
        "time": wk["week"] + "T12:00:00Z",
        "source": "NOAA Climate Prediction Center",
        "mode": "MEAS",
        "cadence_h": 168,
        "links": [
            ["NOAA CPC — ENSO diagnostic discussion", DISC],
            ["NOAA CPC — weekly ENSO update (PDF)", CPC + "/products/analysis_monitoring/lanina/enso_evolution-status-fcsts-web.pdf"],
            ["NOAA CPC — the relative index (RONI)", CPC + "/products/analysis_monitoring/enso/roni/"],
            ["IRI Columbia — model forecasts", "https://iri.columbia.edu/our-expertise/climate/forecasts/enso/current/"],
            ["WMO — El Niño / La Niña update", "https://wmo.int/themes/el-nino-la-nina-phenomena"],
            ["NOAA OISST v2.1 — the SST field", "https://www.ncei.noaa.gov/products/optimum-interpolation-sst"],
        ],
    }


if __name__ == "__main__":
    E = enso()
    s, w, r, f = E["status"], E["weekly"], E["roni"], E["field"]
    print(f"status   {s['alert']} · issued {s['issued']} · next {s['next']}")
    print(f"synopsis {s['synopsis']}")
    print(f"weekly   {w['week']}  relative Niño-3.4 {w['rel']['nino34']:+.1f}  traditional {w['trad34']:+.1f}"
          f"  (1+2 {w['rel']['nino12']:+.1f}, 3 {w['rel']['nino3']:+.1f}, 4 {w['rel']['nino4']:+.1f})")
    print(f"RONI     {r['last']} {r['latest']:+.2f}  record {r['peak']['season']} {r['peak']['value']:+.2f}  ({len(r['v'])} seasons)")
    print(f"field    days {f['days'][0]}..{f['days'][-1]} ({len(f['days'])})  box check {f['n34_check']:+.2f} vs CPC {w['trad34']:+.1f}")
    for c in f["contours"]:
        print(f"         {c['level']:+.0f} °C: {len(c['lines'])} lines, {sum(len(l)//2 for l in c['lines'])} vertices")
