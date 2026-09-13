"""
Olympus — ocean circulation plane, shared helpers.

Two measured sources and one schematic register, kept strictly apart:

  drifter climatology  MEASURED  near-surface velocity, in-situ, 1/4 deg
  ACC fronts           MEASURED  altimetry-derived frontal axes
  deep limbs           SCHEMATIC pathways drawn on real bathymetric gateways

Nothing here merges the three. Every emitted object carries its own
`mode` and `src`, stamped at ingest, never at render.
"""
import json, math

VMAX = 1.5          # m/s, the encoding ceiling; the field's own max is 1.50
NMAX = 1713.0       # drifter-days per square degree, the field's own max

SOURCES = {
    "drifter": {
        "mode": "MEASURED",
        "name": "NOAA Global Drifter Program — near-surface velocity climatology",
        "short": "GDP drifter climatology",
        "detail": "Satellite-tracked drifters drogued at 15 m, binned to 1/4 deg",
        "version": "3.10",
        "doi": "10.1016/j.dsr.2017.04.009",
        "cite": "Laurindo, Mariano & Lumpkin (2017), Deep-Sea Res. I 124, 73-92",
        "licence": "CC BY 4.0",
        "url": "https://erddap.aoml.noaa.gov/gdp/erddap/griddap/drifter_annualmeans",
        "coverage": "annual mean; drogued drifters, programme start to 2024-12-31",
        "grid": "0.25 deg, 1440 x 632, -179.875..179.875 E, -72.875..84.875 N",
    },
    "seasonal": {
        "mode": "MEASURED · CLIMATOLOGY",
        "name": "NOAA Global Drifter Program — monthly velocity climatology",
        "short": "GDP monthly climatology",
        "detail": ("Twelve climatological months, carried as an anomaly on the annual mean. "
                   "A climatological September is the average of every September in the record, "
                   "not September of the year on the scrubber."),
        "version": "3.10",
        "doi": "10.1016/j.dsr.2017.04.009",
        "cite": "Laurindo, Mariano & Lumpkin (2017), Deep-Sea Res. I 124, 73-92",
        "licence": "CC BY 4.0",
        "url": "https://erddap.aoml.noaa.gov/gdp/erddap/griddap/drifter_monthlymeans",
        "coverage": "12 climatological months; 491,790 cells per month, 96% of the annual field",
        "grid": "0.5 deg anomaly on the 0.25 deg annual base",
    },
    "sst": {
        "mode": "MEASURED",
        "name": "NOAA Global Drifter Program — sea-surface temperature climatology",
        "short": "GDP drifter SST",
        "detail": ("The same drifters that gave the velocity also carry a thermistor. "
                   "Annual mean; cells reading below the freezing point of seawater are dropped."),
        "version": "3.10",
        "doi": "10.1016/j.dsr.2017.04.009",
        "cite": "Laurindo, Mariano & Lumpkin (2017), Deep-Sea Res. I 124, 73-92",
        "licence": "CC BY 4.0",
        "url": "https://erddap.aoml.noaa.gov/gdp/erddap/griddap/drifter_annualmeans",
        "coverage": "annual mean, 511,096 cells",
        "grid": "0.5 deg",
    },
    "fronts": {
        "mode": "MEASURED",
        "name": "Altimetry-derived Antarctic Circumpolar Current fronts",
        "short": "Park & Durand ACC fronts",
        "detail": "Frontal axes from the CNES-CLS18 mean dynamic topography",
        "version": "2019-03-29",
        "doi": "10.17882/59800",
        "cite": "Park & Durand (2019), SEANOE; Park et al. (2019), JGR Oceans 124, 4511-4528",
        "licence": "CC BY 4.0",
        "url": "https://www.seanoe.org/data/00486/59800/",
        "coverage": "mean positions, altimetry era",
        "grid": "polylines, 3779-4253 vertices per front",
    },
    "deep": {
        "mode": "SCHEMATIC",
        "name": "Deep and bottom-water pathways",
        "short": "deep limbs — schematic",
        "detail": ("Hand-drawn corridors. The gateways, sills and formation sites they "
                   "pass through are at their true positions and true sill depths; the "
                   "path between them is illustration. There is no measured global map "
                   "of the deep circulation and there cannot be one from present instruments."),
        "version": "1",
        "doi": None,
        "cite": "Pathways after Talley (2013) and Lumpkin & Speer (2007); gateway depths cited per node",
        "licence": "n/a",
        "url": None,
        "coverage": "n/a — schematic",
        "grid": "polylines with a depth per vertex",
    },
}

# Vertical exaggeration used when the deep limbs are drawn inside the globe.
# The ocean is 0.06 % of the Earth's radius; without this nothing would be visible.
# The number is carried into the artifact and stated in the explainer.
DEPTH_SCALE_M = 6000.0     # depth mapped to the full radial excursion
DEPTH_RADIUS  = 0.155      # radial excursion at DEPTH_SCALE_M, in globe radii
VERT_EXAG     = round((DEPTH_RADIUS * 6371000.0) / DEPTH_SCALE_M)   # ~165x


def resample(pts, n):
    """Arc-length resample a flat [lon,lat,...] polyline to n vertices."""
    if len(pts) < 4:
        return pts[:]
    xy = [(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)]
    d = [0.0]
    for a, b in zip(xy, xy[1:]):
        dlon = (b[0] - a[0] + 180) % 360 - 180
        dlat = b[1] - a[1]
        d.append(d[-1] + math.hypot(dlon * math.cos(math.radians((a[1] + b[1]) / 2)), dlat))
    total = d[-1]
    if total <= 0:
        return pts[:]
    out, j = [], 0
    for k in range(n):
        t = total * k / (n - 1)
        while j < len(d) - 2 and d[j + 1] < t:
            j += 1
        span = d[j + 1] - d[j]
        f = 0.0 if span <= 0 else (t - d[j]) / span
        a, b = xy[j], xy[j + 1]
        dlon = (b[0] - a[0] + 180) % 360 - 180
        out.append(round(a[0] + dlon * f, 3))
        out.append(round(a[1] + (b[1] - a[1]) * f, 3))
    return out


def catmull(pts, per=6, closed=False):
    """Catmull-Rom through a flat [lon,lat,...] control polyline.
    Longitude is unwrapped first so a path crossing the date line stays continuous."""
    p = [(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)]
    for i in range(1, len(p)):
        while p[i][0] - p[i - 1][0] > 180:
            p[i] = (p[i][0] - 360, p[i][1])
        while p[i][0] - p[i - 1][0] < -180:
            p[i] = (p[i][0] + 360, p[i][1])
    if closed:
        p = [p[-1]] + p + [p[0], p[1]]
    else:
        p = [p[0]] + p + [p[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(per):
            t = s / per
            t2, t3 = t * t, t * t * t
            for k in (0, 1):
                out.append(round(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t
                                        + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                        + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3), 3))
    out.append(round(p[-2][0], 3)); out.append(round(p[-2][1], 3))
    return out


def dump(obj):
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
