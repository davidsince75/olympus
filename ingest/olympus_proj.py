"""
olympus_proj — ellipsoidal polar stereographic, forward and inverse.

Why this exists
---------------
Every Olympus surface has so far drawn a *spherical* polar stereographic disc
normalised at +/-45 degrees. That projection is not EPSG:3413, EPSG:3031 or
EPSG:3976, and so nothing published on a real polar grid could be overlaid on it
without being resampled through the surface's own inverse — which is what the
GIBS imagery currently is. This module is the replacement: the real thing, on
WGS-84, with no dependency at runtime.

Snyder, *Map Projections — A Working Manual* (USGS PP 1395), pp. 160-163.
Verified against pyproj at ingest time by `verify_proj.py`; the runtime code
here and in `olympus_proj.js` carries no dependency at all.

Grids this project actually uses
--------------------------------
  EPSG:3413  WGS 84 / NSIDC Sea Ice Polar Stereographic North   lat_ts +70  lon0  -45
  EPSG:3976  WGS 84 / NSIDC Sea Ice Polar Stereographic South   lat_ts -70  lon0    0
  EPSG:3031  WGS 84 / Antarctic Polar Stereographic             lat_ts -71  lon0    0

3976 and 3031 are NOT the same grid: their standard parallels differ by one
degree. Measured: they differ by 6.6 km at 70S and 10.0 km at 60S - more than a
pixel of any grid this project draws.
The ASI AMSR2 southern grid is 3976. NASA GIBS Antarctic tiles are 3031.
Anything that draws both must convert, not assume.
"""

import math

# WGS-84
A = 6378137.0
INV_F = 298.257223563
F = 1.0 / INV_F
E2 = 2.0 * F - F * F
E = math.sqrt(E2)


class PolarStereographic:
    """One polar stereographic grid, defined the way a CF grid_mapping defines it."""

    def __init__(self, epsg, lat_ts, lon0, north, a=A, e=E):
        self.epsg = epsg
        self.lat_ts = float(lat_ts)      # standard parallel, degrees, signed
        self.lon0 = float(lon0)          # straight vertical longitude from pole
        self.north = bool(north)
        self.a = a
        self.e = e
        # Snyder 21-33 / 14-15 evaluated once at the standard parallel.
        phi_c = math.radians(abs(self.lat_ts))
        self._mc = math.cos(phi_c) / math.sqrt(1.0 - e * e * math.sin(phi_c) ** 2)
        self._tc = self._t(phi_c)

    def _t(self, phi):
        """Snyder 15-9, on the absolute latitude."""
        e, s = self.e, math.sin(phi)
        return math.tan(math.pi / 4.0 - phi / 2.0) / (
            ((1.0 - e * s) / (1.0 + e * s)) ** (e / 2.0)
        )

    def forward(self, lat, lon):
        """(lat, lon) in degrees -> (x, y) in metres on this grid.

        North aspect:  x = rho sin(lam),  y = -rho cos(lam)
        South aspect:  x = rho sin(lam),  y = +rho cos(lam)
        so that in both cases the straight vertical longitude runs up the page
        away from the pole. rho is always computed on the absolute latitude.
        """
        phi = math.radians(abs(lat))
        lam = math.radians(lon - self.lon0)
        if phi >= math.pi / 2.0 - 1e-12:        # the pole itself
            rho = 0.0
        else:
            rho = self.a * self._mc * self._t(phi) / self._tc
        x = rho * math.sin(lam)
        y = (-1.0 if self.north else 1.0) * rho * math.cos(lam)
        return (x, y)

    def inverse(self, x, y):
        """(x, y) in metres -> (lat, lon) in degrees."""
        sign = 1.0 if self.north else -1.0
        xs, ys = (x, y) if self.north else (x, -y)
        rho = math.hypot(xs, ys)
        if rho < 1e-9:
            return (90.0 * sign, self.lon0)
        t = rho * self._tc / (self.a * self._mc)
        # Snyder 7-9, iterated. Converges in 4-6 passes at any polar latitude.
        chi = math.pi / 2.0 - 2.0 * math.atan(t)
        phi = chi
        e = self.e
        for _ in range(32):
            s = math.sin(phi)
            phi_new = math.pi / 2.0 - 2.0 * math.atan(
                t * (((1.0 - e * s) / (1.0 + e * s)) ** (e / 2.0))
            )
            if abs(phi_new - phi) < 1e-13:
                phi = phi_new
                break
            phi = phi_new
        lam = math.atan2(xs, -ys)
        lat = math.degrees(phi) * sign
        lon = math.degrees(lam) + self.lon0
        lon = (lon + 180.0) % 360.0 - 180.0
        return (lat, lon)


    def scale_factor(self, lat):
        """Point scale factor k at this latitude (Snyder 21-32/14-21).

        A polar stereographic grid is conformal, not equal-area: a nominal
        6.25 km cell is 6.25 km on a side only at the standard parallel. True
        ground area of a cell is (dx*dy)/k^2. Any extent or area number that
        multiplies a cell count by a nominal cell size is wrong, and wrong by
        more the further from the standard parallel it is.
        """
        phi = math.radians(abs(lat))
        if phi >= math.pi / 2.0 - 1e-12:
            # Snyder 21-35: the limit of k at the pole itself.
            e = self.e
            return 0.5 * (self._mc / self._tc) * math.sqrt(
                (1.0 + e) ** (1.0 + e) * (1.0 - e) ** (1.0 - e)
            )
        m = math.cos(phi) / math.sqrt(1.0 - self.e ** 2 * math.sin(phi) ** 2)
        rho = self.a * self._mc * self._t(phi) / self._tc
        return rho / (self.a * m)


EPSG3413 = PolarStereographic(3413, 70.0, -45.0, north=True)
EPSG3976 = PolarStereographic(3976, -70.0, 0.0, north=False)
EPSG3031 = PolarStereographic(3031, -71.0, 0.0, north=False)

GRIDS = {3413: EPSG3413, 3976: EPSG3976, 3031: EPSG3031}


class Grid:
    """A raster on one of those projections, defined by a GDAL GeoTransform.

    GeoTransform is (x0, dx, 0, y0, 0, dy) with (x0, y0) the OUTER corner of the
    first pixel and dy negative for a north-up raster — the same convention the
    IUP Bremen NetCDF files carry, so it is read straight out of the file rather
    than restated here.
    """

    def __init__(self, epsg, geotransform, width, height, name=""):
        self.proj = GRIDS[epsg]
        self.gt = tuple(float(v) for v in geotransform)
        self.width = int(width)
        self.height = int(height)
        self.name = name

    @property
    def extent(self):
        x0, dx, _, y0, _, dy = self.gt
        return (x0, y0 + dy * self.height, x0 + dx * self.width, y0)

    def colrow_to_xy(self, col, row):
        """Pixel centre in projected metres."""
        x0, dx, _, y0, _, dy = self.gt
        return (x0 + (col + 0.5) * dx, y0 + (row + 0.5) * dy)

    def xy_to_colrow(self, x, y):
        x0, dx, _, y0, _, dy = self.gt
        return ((x - x0) / dx - 0.5, (y - y0) / dy - 0.5)

    def colrow_to_latlon(self, col, row):
        return self.proj.inverse(*self.colrow_to_xy(col, row))

    def latlon_to_colrow(self, lat, lon):
        return self.xy_to_colrow(*self.proj.forward(lat, lon))


    def pixel_area_km2(self, row):
        """True ground area of every pixel in a row, km^2, on the ellipsoid."""
        _, dx, _, _, _, dy = self.gt
        nominal = abs(dx * dy) / 1e6
        out = []
        for col in range(self.width):
            lat, _ = self.colrow_to_latlon(col, row)
            k = self.proj.scale_factor(lat)
            out.append(nominal / (k * k))
        return out


# The two ASI AMSR2 6.25 km grids, as declared by the source files themselves.
ASI_N6250 = Grid(3413, (-3850000, 6250, 0, 5850000, 0, -6250), 1216, 1792, "asi-n6250")
ASI_S6250 = Grid(3976, (-3950000, 6250, 0, 4350000, 0, -6250), 1264, 1328, "asi-s6250")
