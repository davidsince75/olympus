"""
ingest_spine.py — the global forcing-and-response spine.

Three records, three separate marks. They are never merged, never averaged,
never substituted for one another:

  CO2_GLOBAL  NOAA GML global monthly mean marine surface CO2, with the
              published monte-carlo uncertainty. Jan 1979 -> present.
  T_GLOBAL    NASA GISTEMP v4 land-ocean monthly anomaly, 1951-1980 base.
  T_ZONAL     NASA GISTEMP v4 annual anomaly by latitude band. Annual only --
              GISTEMP does not publish monthly zonal means; deriving them
              would mean processing the gridded NetCDF. The mismatch in
              cadence is recorded in the stamp rather than papered over.

Output: spine.json
"""

import csv
import io
import json

from common import (CAL_END, CAL_START, align, fetch, header_creation_date,
                    month_axis, write_json)

CO2_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_gl.csv"
GLB_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/GLB.Ts+dSST.csv"
ZON_URL = "https://data.giss.nasa.gov/gistemp/tabledata_v4/ZonAnn.Ts+dSST.csv"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# GISTEMP marks absent months with asterisks. NOAA has historically used
# -99.99 as a sentinel; the global file is currently gap-free but the guard
# stays so a future gap becomes a null rather than a plausible-looking number.
GISS_MISSING = {"***", "****", "*****", ""}
NOAA_SENTINEL = -99.0


def _num(tok):
    tok = tok.strip()
    if tok in GISS_MISSING:
        return None
    try:
        return float(tok)
    except ValueError:
        return None


def read_co2():
    body, stamp = fetch(CO2_URL, "NOAA GML global monthly mean CO2")
    text = body.decode("utf-8")
    stamp["file_creation"] = header_creation_date(text)
    rows = [r for r in text.splitlines() if r and not r.startswith("#")]
    rdr = csv.DictReader(io.StringIO("\n".join(rows)))

    mean, unc, trend = {}, {}, {}
    for r in rdr:
        key = f"{int(r['year']):04d}-{int(r['month']):02d}"
        v = _num(r["average"])
        if v is None or v < NOAA_SENTINEL:
            continue
        mean[key] = round(v, 2)
        u = _num(r["average_unc"])
        if u is not None:
            unc[key] = round(u, 2)
        t = _num(r["trend"])
        if t is not None and t > NOAA_SENTINEL:
            trend[key] = round(t, 2)
    return mean, unc, trend, stamp


def read_gistemp_monthly():
    body, stamp = fetch(GLB_URL, "NASA GISTEMP v4 global land-ocean monthly anomaly")
    text = body.decode("utf-8")
    lines = text.splitlines()
    # Line 0 is a title ("Land-Ocean: Global Means"); line 1 is the header.
    rdr = csv.DictReader(io.StringIO("\n".join(lines[1:])))
    out = {}
    for r in rdr:
        if not r["Year"].strip().isdigit():
            continue
        y = int(r["Year"])
        for i, mn in enumerate(MONTHS, start=1):
            v = _num(r.get(mn, ""))
            if v is not None:
                out[f"{y:04d}-{i:02d}"] = round(v, 2)
    return out, stamp


def read_gistemp_zonal():
    body, stamp = fetch(ZON_URL, "NASA GISTEMP v4 zonal annual anomaly")
    text = body.decode("utf-8")
    rdr = csv.DictReader(io.StringIO(text))
    bands = [b for b in (rdr.fieldnames or []) if b != "Year"]
    out = {b: {} for b in bands}
    for r in rdr:
        if not r["Year"].strip().isdigit():
            continue
        y = int(r["Year"])
        for b in bands:
            v = _num(r.get(b, ""))
            if v is not None:
                out[b][y] = round(v, 2)
    return out, bands, stamp


def ols_per_decade(series, y0, y1):
    """Least-squares trend in K/decade over an inclusive year range."""
    pts = [(y, v) for y, v in series.items() if y0 <= y <= y1]
    if len(pts) < 3:
        return None
    n = len(pts)
    mx = sum(y for y, _ in pts) / n
    my = sum(v for _, v in pts) / n
    den = sum((y - mx) ** 2 for y, _ in pts)
    if den == 0:
        return None
    num = sum((y - mx) * (v - my) for y, v in pts)
    return round((num / den) * 10, 4)


def main():
    axis = month_axis()

    co2, co2_unc, co2_trend, co2_stamp = read_co2()
    tglob, tglob_stamp = read_gistemp_monthly()
    zonal, bands, zon_stamp = read_gistemp_zonal()

    co2_a, co2_cov = align(co2, axis)
    unc_a, _ = align(co2_unc, axis)
    tr_a, _ = align(co2_trend, axis)
    t_a, t_cov = align(tglob, axis)

    # Trends over the satellite ice window. Endpoints are noisy; the ratio is
    # computed from fitted trends, not from first and last year.
    TREND_Y0, TREND_Y1 = 1979, 2025
    zon_years = sorted({y for s in zonal.values() for y in s})
    trend_y1 = min(TREND_Y1, max(zon_years))
    trends = {b: ols_per_decade(zonal[b], TREND_Y0, trend_y1) for b in bands}
    gtrend = trends.get("Glob")
    amp = {
        b: (round(v / gtrend, 2) if v is not None and gtrend else None)
        for b, v in trends.items()
    }

    doc = {
        "record": "olympus-global-spine",
        "built_utc": co2_stamp["retrieved_utc"],
        "calendar": {
            "start": f"{CAL_START[0]:04d}-{CAL_START[1]:02d}",
            "end": f"{CAL_END[0]:04d}-{CAL_END[1]:02d}",
            "months": len(axis),
            "note": ("Keyed by calendar month, not frame index. The ice record "
                     "has outages at 1986-04..06 and 1987-12; joins are on the "
                     "calendar key so the gaps stay gaps."),
        },
        "axis": axis,
        "series": {
            "CO2_GLOBAL": {
                "measured": True,
                "long_name": "Globally averaged marine surface CO2 dry-air mole fraction",
                "units": "ppm",
                "cadence": "monthly",
                "values": co2_a,
                "uncertainty": unc_a,
                "deseasonalised_trend": tr_a,
                "coverage": co2_cov,
                "licence": "CC0 1.0 (NOAA, public domain)",
                "citation": ("Lan, X., Tans, P. and K.W. Thoning: Trends in globally-averaged "
                             "CO2. NOAA GML. gml.noaa.gov/ccgg/trends/"),
                "provenance": co2_stamp,
            },
            "T_GLOBAL": {
                "measured": True,
                "long_name": "GISTEMP v4 global land-ocean temperature anomaly",
                "units": "K anomaly vs 1951-1980",
                "cadence": "monthly",
                "values": t_a,
                "coverage": t_cov,
                "licence": "Public domain (NASA GISS)",
                "citation": ("GISTEMP Team, 2026: GISS Surface Temperature Analysis "
                             "(GISTEMP), version 4. NASA GISS. "
                             "data.giss.nasa.gov/gistemp/"),
                "provenance": tglob_stamp,
            },
            "T_ZONAL": {
                "measured": True,
                "long_name": "GISTEMP v4 land-ocean temperature anomaly by latitude band",
                "units": "K anomaly vs 1951-1980",
                "cadence": "annual",
                "cadence_note": ("Annual only. GISTEMP publishes no monthly zonal means; "
                                 "monthly bands would require the gridded NetCDF. Do not "
                                 "render this on the monthly transport without saying so."),
                "bands": bands,
                "years": zon_years,
                "values": {b: [zonal[b].get(y) for y in zon_years] for b in bands},
                "trend_k_per_decade": trends,
                "amplification_vs_global": amp,
                "trend_window": f"{TREND_Y0}-{trend_y1}",
                "trend_method": "ordinary least squares on annual band means",
                "trend_caveat": ("Rantanen et al. 2022 report ~3.8x Arctic amplification "
                                 "using ERA5 north of 66.5degN for 1979-2021. This figure "
                                 "is GISTEMP north of 64degN. Different data, different "
                                 "boundary; both defensible. State which is on screen."),
                "licence": "Public domain (NASA GISS)",
                "provenance": zon_stamp,
            },
        },
        "constraints": [
            "Records are never merged, averaged or swapped. GISTEMP is not HadCRUT "
            "and is not ERA5; a second temperature record would carry its own mark.",
            "Outside published coverage the value is null. Render 'no observation' "
            "rather than holding the last value.",
            "The three records end on three different months. Check each series' "
            "last_observed before reading a recent month.",
        ],
    }

    write_json("spine.json", doc)

    print("axis months        ", len(axis))
    for name, s in doc["series"].items():
        if s["cadence"] == "monthly":
            c = s["coverage"]
            print(f"{name:12s} {c['months_observed']:>4d}/{c['months_on_axis']} months  "
                  f"{c['first_observed']} -> {c['last_observed']}")
        else:
            print(f"{name:12s} {len(s['years'])} years  "
                  f"{s['years'][0]} -> {s['years'][-1]}  {len(s['bands'])} bands")
    print("\ntrend / amplification, %s:" % doc["series"]["T_ZONAL"]["trend_window"])
    for b in ("Glob", "NHem", "SHem", "64N-90N", "44N-64N", "24S-24N", "64S-44S", "90S-64S"):
        if b in trends:
            print(f"  {b:10s} {trends[b]:+.3f} K/dec   {amp[b]:.2f}x global")


if __name__ == "__main__":
    main()
