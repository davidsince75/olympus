/*
 * olympus_proj.js — ellipsoidal polar stereographic, forward and inverse.
 *
 * The line-for-line mirror of ingest/olympus_proj.py. Both are verified against
 * pyproj by ingest/verify_proj.py, and against each other by
 * scripts/probe_proj.cjs, which asserts they agree to 1e-6 m on a grid of
 * several thousand points. Neither has a runtime dependency.
 *
 * Snyder, Map Projections — A Working Manual (USGS PP 1395), pp. 160-163.
 *
 *   EPSG:3413  NSIDC Sea Ice Polar Stereographic North   lat_ts +70  lon0 -45
 *   EPSG:3976  NSIDC Sea Ice Polar Stereographic South   lat_ts -70  lon0   0
 *   EPSG:3031  Antarctic Polar Stereographic             lat_ts -71  lon0   0
 *
 * 3976 and 3031 differ by 6.6 km at 70S. The ASI AMSR2 southern grid is 3976;
 * NASA GIBS Antarctic tiles are 3031. Convert, never assume.
 */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.OlympusProj = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var A = 6378137.0;
  var INV_F = 298.257223563;
  var F = 1.0 / INV_F;
  var E = Math.sqrt(2.0 * F - F * F);
  var D2R = Math.PI / 180.0;
  var R2D = 180.0 / Math.PI;

  function PolarStereographic(epsg, latTs, lon0, north) {
    this.epsg = epsg;
    this.latTs = latTs;
    this.lon0 = lon0;
    this.north = !!north;
    this.a = A;
    this.e = E;
    var phiC = Math.abs(latTs) * D2R;
    this._mc = Math.cos(phiC) / Math.sqrt(1.0 - E * E * Math.pow(Math.sin(phiC), 2));
    this._tc = this._t(phiC);
  }

  PolarStereographic.prototype._t = function (phi) {
    var e = this.e, s = Math.sin(phi);
    return Math.tan(Math.PI / 4.0 - phi / 2.0) /
      Math.pow((1.0 - e * s) / (1.0 + e * s), e / 2.0);
  };

  /* (lat, lon) degrees -> [x, y] metres */
  PolarStereographic.prototype.forward = function (lat, lon) {
    var phi = Math.abs(lat) * D2R;
    var lam = (lon - this.lon0) * D2R;
    var rho = (phi >= Math.PI / 2.0 - 1e-12)
      ? 0.0
      : this.a * this._mc * this._t(phi) / this._tc;
    return [rho * Math.sin(lam), (this.north ? -1.0 : 1.0) * rho * Math.cos(lam)];
  };

  /* [x, y] metres -> [lat, lon] degrees */
  PolarStereographic.prototype.inverse = function (x, y) {
    var sign = this.north ? 1.0 : -1.0;
    var xs = x, ys = this.north ? y : -y;
    var rho = Math.sqrt(xs * xs + ys * ys);
    if (rho < 1e-9) return [90.0 * sign, this.lon0];
    var t = rho * this._tc / (this.a * this._mc);
    var e = this.e;
    var phi = Math.PI / 2.0 - 2.0 * Math.atan(t);
    for (var i = 0; i < 32; i++) {
      var s = Math.sin(phi);
      var next = Math.PI / 2.0 - 2.0 * Math.atan(
        t * Math.pow((1.0 - e * s) / (1.0 + e * s), e / 2.0));
      if (Math.abs(next - phi) < 1e-13) { phi = next; break; }
      phi = next;
    }
    var lam = Math.atan2(xs, -ys);
    var lon = lam * R2D + this.lon0;
    lon = ((lon + 180.0) % 360.0 + 360.0) % 360.0 - 180.0;
    return [phi * R2D * sign, lon];
  };

  /* Point scale factor k (Snyder 21-32/21-35). A polar stereographic grid is
     conformal, not equal-area: true cell area is (dx*dy)/k^2. */
  PolarStereographic.prototype.scaleFactor = function (lat) {
    var phi = Math.abs(lat) * D2R, e = this.e;
    if (phi >= Math.PI / 2.0 - 1e-12) {
      return 0.5 * (this._mc / this._tc) *
        Math.sqrt(Math.pow(1 + e, 1 + e) * Math.pow(1 - e, 1 - e));
    }
    var m = Math.cos(phi) / Math.sqrt(1.0 - e * e * Math.pow(Math.sin(phi), 2));
    var rho = this.a * this._mc * this._t(phi) / this._tc;
    return rho / (this.a * m);
  };

  var GRIDS = {
    3413: new PolarStereographic(3413, 70.0, -45.0, true),
    3976: new PolarStereographic(3976, -70.0, 0.0, false),
    3031: new PolarStereographic(3031, -71.0, 0.0, false)
  };

  /* A raster on one of those projections, defined by a GDAL GeoTransform:
     [x0, dx, 0, y0, 0, dy], (x0,y0) the outer corner of the first pixel. */
  function Grid(epsg, gt, width, height, name) {
    this.proj = GRIDS[epsg];
    this.gt = gt;
    this.width = width;
    this.height = height;
    this.name = name || '';
  }
  Grid.prototype.colrowToXY = function (col, row) {
    return [this.gt[0] + (col + 0.5) * this.gt[1], this.gt[3] + (row + 0.5) * this.gt[5]];
  };
  Grid.prototype.xyToColrow = function (x, y) {
    return [(x - this.gt[0]) / this.gt[1] - 0.5, (y - this.gt[3]) / this.gt[5] - 0.5];
  };
  Grid.prototype.colrowToLatLon = function (col, row) {
    var p = this.colrowToXY(col, row); return this.proj.inverse(p[0], p[1]);
  };
  Grid.prototype.latLonToColrow = function (lat, lon) {
    var p = this.proj.forward(lat, lon); return this.xyToColrow(p[0], p[1]);
  };
  /* True ground area of one cell of this grid at this latitude, km^2. */
  Grid.prototype.cellAreaKm2 = function (lat) {
    var k = this.proj.scaleFactor(lat);
    return Math.abs(this.gt[1] * this.gt[5]) / 1e6 / (k * k);
  };
  /* Unit-square screen coordinates, for drawing into a canvas of any size. */
  Grid.prototype.latLonToUnit = function (lat, lon) {
    var cr = this.latLonToColrow(lat, lon);
    return [cr[0] / this.width, cr[1] / this.height];
  };

  return {
    A: A, E: E,
    PolarStereographic: PolarStereographic,
    Grid: Grid,
    GRIDS: GRIDS,
    ASI_N6250: new Grid(3413, [-3850000, 6250, 0, 5850000, 0, -6250], 1216, 1792, 'asi-n6250'),
    ASI_S6250: new Grid(3976, [-3950000, 6250, 0, 4350000, 0, -6250], 1264, 1328, 'asi-s6250')
  };
}));
