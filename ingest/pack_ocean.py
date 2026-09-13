"""
Olympus — pack the ocean circulation plane into one emitted JS constant.

  python pack_ocean.py <gdp_annual.nc> <parkfronts.nc> <out.js>

Follows the deck's convention: everything is baked at build time, nothing is
fetched at runtime, and every object carries the mode and source it was
stamped with at ingest.
"""
import sys, os, io, json, math, glob, base64
import numpy as np
import netCDF4 as nc
from PIL import Image

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import ocean_common as C
import ocean_deep as D


def _box(a, f):
    """Box-average to 1/f resolution, ignoring cells with no observation."""
    h, w = a.shape
    h2, w2 = h // f, w // f
    b = a[:h2 * f, :w2 * f].reshape(h2, f, w2, f)
    with np.errstate(invalid="ignore"):
        return np.nanmean(b, axis=(1, 3))


def pack_sst(path, ann_ok):
    """Sea-surface temperature from the same drifters that gave the velocity.

    This is the thermo in thermohaline, and without it the deck showed only the
    haline half: every filament the same colour whether it was the Gulf Stream
    carrying 24 C north or the Labrador Current bringing 3 C back. Half
    resolution is ample — SST is a smooth field, and the gradient that matters
    (the Gulf Stream front, the Polar Front) survives it.

    Eighty cells read below -1.9 C, the freezing point of seawater, down to
    -11.6 C: drifters that beached or whose thermistor failed. They are dropped,
    not clamped. The deck says nothing where it knows nothing.
    """
    F = 2
    TMIN, TMAX = -2.0, 34.0
    d = nc.Dataset(path)
    T = np.ma.filled(d.variables["SST"][:], np.nan).T
    impossible = np.isfinite(T) & (T < -1.9)
    T = np.where(impossible, np.nan, T)
    ok = np.isfinite(T) & ann_ok

    with np.errstate(invalid="ignore"):
        Tf = _box(np.where(ok, T, np.nan), F)
        okf = _box(ok.astype(float), F) > 0.35
    Tf = np.where(okf, np.nan_to_num(Tf), 0.0)

    h2, w2 = Tf.shape
    img = np.zeros((h2, w2, 4), np.uint8)
    img[..., 0] = np.clip(np.round((Tf - TMIN) / (TMAX - TMIN) * 255), 0, 255).astype(np.uint8)
    img[..., 3] = np.where(okf, 255, 0)
    buf = io.BytesIO()
    Image.fromarray(img[::-1]).save(buf, "PNG", optimize=True, compress_level=9)
    png = buf.getvalue()

    back = np.array(Image.open(io.BytesIO(png)))[::-1]
    dec = back[..., 0].astype(np.float64) / 255 * (TMAX - TMIN) + TMIN
    err = float(np.abs(dec[okf] - Tf[okf]).max())

    return {
        "w": w2, "h": h2, "d": 0.25 * F,
        "lon0": -179.875 + 0.25 * (F - 1) / 2,
        "lat0": -72.875 + 0.25 * (F - 1) / 2,
        "tmin": TMIN, "tmax": TMAX,
        "png": "data:image/png;base64," + base64.b64encode(png).decode(),
    }, {"cells": int(okf.sum()), "bytes": len(png),
        "dropped_below_freezing": int(impossible.sum()),
        "encode_max_err_c": round(err, 4),
        "range_c": [round(float(np.nanmin(T)), 2), round(float(np.nanmax(T)), 2)]}


def pack_seasonal(annual_path, month_paths, ann_ok, Ua, Va):
    """The seasonal signal, as an anomaly on the annual mean.

    Twelve full-resolution months would be 12 MB against the artifact's
    remaining headroom. They are also mostly redundant: the seasonal residual
    has an RMS of 7 cm/s against a field that reaches 1.5 m/s, and what
    structure it has is large-scale — the monsoon reversal, the equatorial
    bands, the seasonal swing of the western boundary currents. So the annual
    mean is carried at full resolution and twelve anomaly frames at half,
    tiled into one sheet. The artifact reconstructs u = u_annual + du(month).

    Alpha marks where that month has its own observation. Where it does not —
    about 4% of the annual field's cells — the anomaly is zero and the deck
    falls back to the annual mean and says so in the readout, rather than
    pretending the month was observed.
    """
    # Resolution was chosen by measurement, not by taste. Using the annual mean
    # alone costs 4.82 cm/s RMS against the true monthly field. A 1-degree
    # anomaly recovers that to 1.77 cm/s for 726 KB; a half-degree one reaches
    # 1.12 cm/s but costs 2.51 MB — 3.4x the payload for 0.65 cm/s, which is
    # well inside the field's own standard error. So: 1 degree.
    F = 4
    AMAX = 1.6                      # p99.99 of the anomaly is 0.99 m/s; outliers clip
    COLS, ROWS = 4, 3
    frames, stats = [], []
    for mi, path in enumerate(month_paths):
        d = nc.Dataset(path)
        cm = int(np.asarray(d.variables["ClimatologicalMonth"][:]).ravel()[0])
        if cm != mi:
            raise SystemExit(f"[seasonal] {path} carries ClimatologicalMonth {cm}, expected {mi}")
        U = np.squeeze(np.ma.filled(d.variables["U"][:], np.nan)).T
        V = np.squeeze(np.ma.filled(d.variables["V"][:], np.nan)).T
        ok = np.isfinite(U) & np.isfinite(V) & ann_ok
        du = np.where(ok, U - Ua, np.nan)
        dv = np.where(ok, V - Va, np.nan)
        okf = _box(ok.astype(float), F) > 0.35
        duf = np.where(okf, np.nan_to_num(_box(du, F)), 0.0)
        dvf = np.where(okf, np.nan_to_num(_box(dv, F)), 0.0)
        frames.append((duf, dvf, okf))
        stats.append({"month": mi + 1, "cells": int(ok.sum()),
                      "max": round(float(np.nanmax(np.maximum(np.abs(du), np.abs(dv)))), 3)})

    h2, w2 = frames[0][0].shape
    sheet = np.zeros((ROWS * h2, COLS * w2, 4), np.uint8)

    def enc(a):
        s_ = np.sign(a); m = np.clip(np.abs(a) / AMAX, 0, 1)
        return np.clip(np.round(s_ * np.sqrt(m) * 127) + 128, 0, 255).astype(np.uint8)

    for mi, (duf, dvf, okf) in enumerate(frames):
        r, c = divmod(mi, COLS)
        y0, x0 = r * h2, c * w2
        tile = np.zeros((h2, w2, 4), np.uint8)
        tile[..., 0] = enc(duf); tile[..., 1] = enc(dvf)
        tile[..., 3] = np.where(okf, 255, 0)
        tile[~okf, 0] = 128; tile[~okf, 1] = 128
        sheet[y0:y0 + h2, x0:x0 + w2] = tile[::-1]        # north up, same as the base

    buf = io.BytesIO()
    Image.fromarray(sheet).save(buf, "PNG", optimize=True, compress_level=9)
    png = buf.getvalue()

    # byte-exact check on the round trip, at full reconstruction
    back = np.array(Image.open(io.BytesIO(png)))
    worst = 0.0
    for mi, (duf, dvf, okf) in enumerate(frames):
        r, c = divmod(mi, COLS)
        t = back[r * h2:(r + 1) * h2, c * w2:(c + 1) * w2][::-1]
        e = (t[..., 0].astype(np.float64) - 128) / 127.0
        dec = np.sign(e) * e * e * AMAX
        worst = max(worst, float(np.abs(dec[okf] - duf[okf]).max()))

    # what the annual mean alone costs, and what this recovers
    err_ann, err_rec = [], []
    for mi, (duf, dvf, okf) in enumerate(frames):
        d = nc.Dataset(month_paths[mi])
        U = np.squeeze(np.ma.filled(d.variables["U"][:], np.nan)).T
        ok = np.isfinite(U) & ann_ok
        up = np.kron(duf, np.ones((F, F)))[:Ua.shape[0], :Ua.shape[1]]
        err_ann.append(np.abs(Ua[ok] - U[ok]))
        err_rec.append(np.abs((Ua + up)[ok] - U[ok]))
    rms_ann = float(np.concatenate(err_ann).mean())
    rms_rec = float(np.concatenate(err_rec).mean())

    return {
        "w": w2, "h": h2, "cols": COLS, "rows": ROWS, "nm": 12,
        "d": 0.25 * F,
        "lon0": -179.875 + 0.25 * (F - 1) / 2,
        "lat0": -72.875 + 0.25 * (F - 1) / 2,
        "amax": AMAX,
        "png": "data:image/png;base64," + base64.b64encode(png).decode(),
    }, {"frames": stats, "bytes": len(png),
        "encode_max_err_ms": round(worst, 5),
        "rms_annual_only_ms": round(rms_ann, 5),
        "rms_with_season_ms": round(rms_rec, 5)}


def pack_flow(path):
    d = nc.Dataset(path)
    U = np.ma.filled(d.variables["U"][:], np.nan).T      # -> (lat, lon)
    V = np.ma.filled(d.variables["V"][:], np.nan).T
    N = np.ma.filled(d.variables["N"][:], np.nan).T
    h, w = U.shape
    ok = np.isfinite(U) & np.isfinite(V)

    def enc(a):
        s = np.sign(a); m = np.clip(np.abs(a) / C.VMAX, 0, 1)
        return np.clip(np.round(s * np.sqrt(m) * 127) + 128, 0, 255).astype(np.uint8)

    img = np.zeros((h, w, 4), np.uint8)
    img[..., 0] = enc(np.nan_to_num(U))
    img[..., 1] = enc(np.nan_to_num(V))
    img[..., 2] = np.clip(np.log1p(np.nan_to_num(N)) / np.log1p(C.NMAX) * 255, 0, 255).astype(np.uint8)
    img[..., 3] = np.where(ok, 255, 0)
    img[~ok, 0] = 128; img[~ok, 1] = 128          # neutral so a stray sample reads zero

    buf = io.BytesIO()
    Image.fromarray(img[::-1]).save(buf, "PNG", optimize=True, compress_level=9)   # north up
    png = buf.getvalue()

    sp = np.hypot(U, V)
    stats = {
        "cells": int(ok.sum()),
        "max": round(float(np.nanmax(sp)), 4),
        "mean": round(float(np.nanmean(sp)), 4),
        "p99": round(float(np.nanpercentile(sp[np.isfinite(sp)], 99)), 4),
    }
    # byte-exact check: decode the PNG we just wrote and compare against the source
    back = np.array(Image.open(io.BytesIO(png)))[::-1]
    ue = (back[..., 0].astype(np.float64) - 128) / 127.0
    ud = np.sign(ue) * ue * ue * C.VMAX
    err = np.abs(ud[ok] - U[ok])
    stats["encode_max_err_ms"] = round(float(err.max()), 5)
    stats["encode_rms_err_ms"] = round(float(np.sqrt((err ** 2).mean())), 6)

    return ({
        "w": w, "h": h,
        "lon0": -179.875, "lat0": -72.875, "d": 0.25,
        "vmax": C.VMAX, "nmax": C.NMAX,
        "png": "data:image/png;base64," + base64.b64encode(png).decode(),
    }, stats, len(png), (ok, U, V))


def pack_fronts(path):
    d = nc.Dataset(path)
    meta = [("NB",    "Northern branch of the Subantarctic Front", "#7FD0E3"),
            ("SAF",   "Subantarctic Front",                        "#5FB6D8"),
            ("PF",    "Polar Front",                               "#8FA8E8"),
            ("SACCF", "Southern ACC Front",                        "#A98FE0"),
            ("SB",    "Southern Boundary of the ACC",              "#C68FD4")]
    out = []
    for key, label, col in meta:
        lat = np.asarray(d.variables["Lat" + key][:], float)
        lon = np.asarray(d.variables["Lon" + key][:], float)
        # each front carries a single non-finite terminator; carrying it through
        # the arc-length resample turns the whole polyline into NaN
        good = np.isfinite(lat) & np.isfinite(lon)
        lat, lon = lat[good], lon[good]
        lon = ((lon + 180) % 360) - 180
        n0 = int(good.size)
        flat = []
        for a, b in zip(lon, lat):
            flat.append(float(a)); flat.append(float(b))
        flat = C.resample(flat, 760)
        bad = [v for v in flat if not math.isfinite(v)]
        if bad:
            raise SystemExit(f"[fronts] {key}: {len(bad)} non-finite vertices after resample")
        out.append({"id": "front_" + key.lower(), "k": key, "label": label,
                    "col": col, "n0": n0, "pts": flat})
    return out


def pack_limbs():
    out = []
    for lid, label, cls, ctrl in D.LIMBS:
        # unwrap longitude, then Catmull-Rom through (lon, lat, depth)
        p = [list(v) for v in ctrl]
        for i in range(1, len(p)):
            while p[i][0] - p[i - 1][0] > 180:  p[i][0] -= 360
            while p[i][0] - p[i - 1][0] < -180: p[i][0] += 360
        q = [p[0]] + p + [p[-1]]
        per = 8
        pts = []
        for i in range(1, len(q) - 2):
            p0, p1, p2, p3 = q[i - 1], q[i], q[i + 1], q[i + 2]
            for s in range(per):
                t = s / per; t2 = t * t; t3 = t2 * t
                for k in (0, 1, 2):
                    v = 0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t
                               + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                               + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3)
                    pts.append(round(v, 2) if k < 2 else round(max(0.0, v)))
        pts += [round(q[-2][0], 2), round(q[-2][1], 2), round(max(0.0, q[-2][2]))]
        out.append({"id": lid, "label": label, "cls": cls, "pts": pts,
                    "nctrl": len(ctrl), "n": len(pts) // 3})
    return out


def pack_nodes():
    return [{"id": i, "at": [lo, la], "depth": dp, "label": lb, "kind": kd, "cite": ct}
            for (i, lo, la, dp, lb, kd, ct) in D.NODES]


def main():
    gdp, fronts_nc, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    months = sorted(glob.glob(os.path.join(os.path.dirname(gdp), "gdp_i??.nc")))
    if len(months) != 12:
        raise SystemExit(f"[seasonal] found {len(months)} monthly files, need 12 "
                         f"(run ingest/fetch_ocean.sh)")
    flow, stats, pngbytes, (ann_ok, Ua, Va) = pack_flow(gdp)
    seas, seas_stats = pack_seasonal(gdp, months, ann_ok, Ua, Va)
    sst_path = os.path.join(os.path.dirname(gdp), "gdp_sst.nc")
    sst, sst_stats = pack_sst(sst_path, ann_ok)
    fronts = pack_fronts(fronts_nc)
    limbs = pack_limbs()
    nodes = pack_nodes()

    obj = {
        "src": C.SOURCES,
        "depth": {"scale_m": C.DEPTH_SCALE_M, "radius": C.DEPTH_RADIUS, "exag": C.VERT_EXAG},
        "flow": flow,
        "flow_stats": stats,
        "seasonal": seas,
        "seasonal_stats": seas_stats,
        "sst": sst,
        "sst_stats": sst_stats,
        "fronts": fronts,
        "limbs": limbs,
        "nodes": nodes,
    }
    # nothing non-finite may reach the artifact: json.dumps writes NaN/Infinity,
    # which is valid JavaScript and silently produces an invisible layer
    def scan(o, path="OCEAN"):
        if isinstance(o, float):
            if not math.isfinite(o):
                raise SystemExit(f"non-finite value at {path}: {o!r}")
        elif isinstance(o, dict):
            for k, v in o.items(): scan(v, f"{path}.{k}")
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o): scan(v, f"{path}[{i}]")
    scan(obj)

    js = "const OCEAN=" + json.dumps(obj, separators=(",", ":"), ensure_ascii=False,
                                     allow_nan=False) + ";"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(js)

    print(f"flow      {flow['w']}x{flow['h']}  png {pngbytes/1024:8.1f} KB")
    print(f"seasonal  {seas['cols']}x{seas['rows']} tiles of {seas['w']}x{seas['h']}  "
          f"png {seas_stats['bytes']/1024:8.1f} KB  "
          f"anomaly encode err max {seas_stats['encode_max_err_ms']*100:.3f} cm/s")
    print(f"          seasonal error vs the true month: annual mean alone "
          f"{seas_stats['rms_annual_only_ms']*100:.2f} cm/s -> with the anomaly "
          f"{seas_stats['rms_with_season_ms']*100:.2f} cm/s")
    print(f"          cells {stats['cells']}  max |V| {stats['max']} m/s  "
          f"encode err max {stats['encode_max_err_ms']*100:.3f} cm/s  rms {stats['encode_rms_err_ms']*100:.4f} cm/s")
    print(f"sst       {sst['w']}x{sst['h']}  png {sst_stats['bytes']/1024:8.1f} KB  "
          f"{sst_stats['range_c'][0]} to {sst_stats['range_c'][1]} C  "
          f"step {sst_stats['encode_max_err_c']*1000:.0f} mC  "
          f"dropped {sst_stats['dropped_below_freezing']} cells below freezing")
    print(f"fronts    {len(fronts)} fronts, {sum(len(f['pts'])//2 for f in fronts)} vertices "
          f"(from {sum(f['n0'] for f in fronts)})")
    print(f"limbs     {len(limbs)} limbs, {sum(l['n'] for l in limbs)} vertices")
    print(f"nodes     {len(nodes)}")
    print(f"emitted   {out_path}  {len(js)/1024/1024:.3f} MB")


if __name__ == "__main__":
    main()
