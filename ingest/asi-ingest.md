# ASI AMSR2 ingest, and the projection everything now shares

**Built 12 September 2026.** Closes audit finding #1 (the 220-cell ice field) and finding #3
(the projection is generic) with one piece of work, because they were the same problem.

---

## The projection came first, because nothing else could be right without it

`olympus_proj.py` and `olympus_proj.js` are the same ellipsoidal polar stereographic
implementation in two languages — Snyder, USGS PP 1395, pp. 160-163 — on WGS-84, with **no
runtime dependency**. Every surface, every ingest and every readout now places a coordinate
through one of these two files.

| Grid | Standard parallel | Central meridian | Used by |
|---|---|---|---|
| EPSG:3413 | +70° | −45° | ASI AMSR2 north, NASA GIBS Arctic |
| EPSG:3976 | −70° | 0° | ASI AMSR2 south |
| EPSG:3031 | −71° | 0° | NASA GIBS Antarctic |

**3976 and 3031 are not the same grid, and the difference is not negligible.** Measured, not
assumed: 6,567 m apart at 70° S and 9,974 m at 60° S. That is more than a cell of anything this
project draws. The southern ice field arrives on 3976; GIBS Antarctic imagery arrives on 3031;
a surface carrying both must convert. This was found by building the module, not by reading
about it, and it would have silently mis-registered the Antarctic ice against its own imagery.

### How it is verified

Two independent checks, both of which must pass before a build:

```
python3 ingest/verify_proj.py            # against pyproj, 520 points per grid
node scripts/probe_proj.cjs              # python against javascript, 1,044 points
```

`verify_proj.py` asserts forward, inverse and round-trip against **pyproj** — a genuinely
independent implementation of the same EPSG definitions — to better than 0.05 m, and then
asserts that each ASI grid's declared GeoTransform puts the pole exactly where the file says it
is. pyproj is a **build-time** dependency only; neither shipped module imports anything.

`probe_proj.cjs` asserts that the JavaScript agrees with the Python, from a fixture the Python
wrote. This is the check that matters at runtime: if the two drift apart, the surface draws data
somewhere the ingest did not put it, and nothing about the rendered page would look wrong.

Also verified: the point scale factor *k*, which is 1.0 at the standard parallel by construction
and continuous into the pole. A polar stereographic grid is conformal, not equal-area — a 6.25 km
cell is 39.06 km² at 70° N and 41.37 km² at 85° N. Extent and area are computed with *k*, never
by multiplying a cell count by a nominal size.

---

## The ice field, at the resolution it is actually published

```
python3 ingest/ingest_asi.py --hemisphere n --dates 2026-09-11
python3 ingest/ingest_asi.py --hemisphere s --dates 2026-09-01:2026-09-11
```

| | Deck today | This |
|---|---|---|
| Grid | 220 × 220 per hemisphere | 1216 × 1792 (N) · 1264 × 1328 (S) |
| Cell | ~45 km | 6.25 km |
| Cadence | monthly | daily |
| Bytes per frame | ~12 KB | 129 KB (N) · 293 KB (S) |
| Source | OSI SAF, via a lost ingest | IUP Bremen, the institute that wrote the algorithm |

**A full-resolution frame costs 129 KB.** That number reframes the whole payload argument: the
expansion plan's A2 assumed 440 × 440 would cost ~28 MB and proposed delta encoding to survive
it. A day of the real 6.25 km field costs a fiftieth of the deck's current atlas payload. The
constraint was never resolution; it was the frame count.

### Why IUP Bremen and not meereisportal

meereisportal.de mirrors this same product as 8.3 MB GeoTIFFs reprojected onto the
Hughes-ellipsoid NSIDC grids (EPSG:3411/3412). IUP Bremen is the originating institute, publishes
650 KB of CF-1.5 NetCDF on WGS-84, and its `robots.txt` permits automated retrieval —
meereisportal's does not. Fewer hops, smaller files, the grid the rest of the world publishes on,
and a licence position we can actually stand on.

  Spreen, G., L. Kaleschke and G. Heygster (2008), Sea ice remote sensing using AMSR-E 89 GHz
  channels, *J. Geophys. Res.* 113, C02S03, doi:10.1029/2005JC003384

### Two things the ingest refuses to assume

**Orientation.** The NetCDF y axis *ascends* — the files are written through
`grdmath … FLIPUD` — while the GeoTransform in the same file describes a north-up raster. The
ingest reads the axes, derives the transform from them, orients the array, and then asserts the
result against the declared transform. An unchecked flip draws the Arctic upside down and
nothing in the rendering would complain.

**Cell area.** See *k* above.

### Encoding, and what "verified" means here

8-bit PNG, `concentration_percent = code / 2` (0.5 % steps), `255` = the source carried no value
for that cell. The source does not distinguish land from outside-swath from pole hole, so
neither do we; inventing the distinction would be inventing data.

Every frame is decoded again after packing and compared to the source array. The no-value mask
must match **exactly**, and no cell may differ by more than half a quantisation step. Measured
worst error on the first two frames: 0.250 %, which is half a step, as it should be. The
manifest records that number per frame rather than asserting it in prose.

### What the manifest carries

One record per frame: instrument, algorithm and version, producer, observation date, EPSG, grid
size, encoding and its measured worst error, extent and ice area on the ellipsoid, the source
URL, its `Last-Modified`, its **SHA-256**, and the retrieval time. Provenance is stamped at
ingest, as it is everywhere else on this platform.

---

## The surface

`build/build_ice_surface.py` assembles `dist/ice_surface.html` — the deck's ice layer as a
standalone instrument: both hemispheres, zoom and pan with the cursor anchored, a cursor readout
inverted through `olympus_proj.js`, the 15 % extent threshold drawn rather than described, and a
cell-size switch that block-averages the same array 7×7 to ≈43.75 km so the deck's present
resolution can be seen beside the real one.

It is also the first proof that the shared projection works end to end: the ingest places the
data with the Python module and the page reads a coordinate back with the JavaScript one.

```
python3 build/build_ice_surface.py          # -> dist/ice_surface.html, 0.58 MB
node scripts/render_ice.cjs                 # renders it in the artifact skeleton and
                                            # reads the readouts back out of the DOM
```

`render_ice.cjs` wraps the page in the **real artifact skeleton** before rendering, because an
unwrapped local render has bitten this project before, and it asserts on the DOM rather than on
the picture.

---

## Open, and honest about it

- **Thickness is blocked on access, not on code.** CS2SMOS weekly merged CryoSat-2/SMOS is the
  highest-value missing layer. Its routes are AWI's FTP (no HTTPS reachable from the build host),
  meereisportal (robots-disallowed) and CMEMS (account required). It needs an access decision —
  a CMEMS account, or a mail to `cs2smos-support@awi.de` — before any code is worth writing.
- **Only two frames are ingested.** The machinery takes any date range; what to carry is a
  payload decision that should be made against the 129 KB number above, not before it.
- **No uncertainty layer.** ASI does not ship a per-cell uncertainty in these files. The drift
  products do, and that is where A4 should start.
- **Nothing is wired into the deck yet.** The deck still draws its 220-cell OSI SAF field on the
  spherical disc. Replacing it is the next piece of surgery, and it is the one that makes the
  projection change visible on the surface people actually hold.
