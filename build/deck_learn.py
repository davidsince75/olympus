# -*- coding: utf-8 -*-
"""Olympus deck — learning-layer update.

Adds explainer entries for everything the deck gained after v2 (GIBS imagery,
the living layer, the surface switcher), repoints the layers and feed entries
that were aimed at the wrong explainer, and corrects the two places on the page
that still describe Sentinel-1 as placeholder geometry.
"""
import io, re, sys

SRC = "/home/claude/olympus/src/deck.html"
s = io.open(SRC, encoding="utf8").read()
orig = s

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1)
    print("  ok  %s" % label)

# ----------------------------------------------------------------- new entries
NEW = u'''
/* ---- the base imagery ---- */
bluemarble:{k:"obj",t:"Blue Marble",
 b:"The default ground under the map is a static composite — shaded relief and <b>bathymetry</b>, so the sea floor is drawn as well as the land. Look at the Southern Ocean: the pale ring around the continent is the continental shelf, and the sharp step where it ends is the shelf break. That step is where the dense water made in the polynyas above it descends into the deep ocean.",
 p:"NASA GIBS BlueMarble_ShadedRelief_Bathymetry. A composite with no date, and no time dimension in the service."},
truecolor:{k:"ins",t:"True colour, and what it is not",
 b:"One day of real reflectance from MODIS: red is band 1, green band 4, blue band 3, at <b>250 m</b>. It is called <i>corrected</i> reflectance because Rayleigh scattering and gas absorption have been removed — but aerosols deliberately have not, so smoke, dust and haze stay visible instead of being scrubbed out. It is a near-real-time product, not the science-grade surface reflectance.",
 p:"NASA GIBS / Worldview MODIS Corrected Reflectance, produced by LANCE. Terra record since 24 February 2000."},
polar_night:{k:"obj",t:"The dark half of the disc",
 b:"Where the imagery goes black, nothing is missing. It is <b>polar night</b> — the sun has not risen there for weeks or months, and an optical instrument photographs exactly what is there to photograph, which is nothing. This is the whole reason the ice record underneath is microwave rather than optical: half the year, the only pole you can see is the one you can hear.",
 p:"An absence of light in the source imagery, not an absence of data."},
terra_drift:{k:"ins",t:"The satellite is drifting",
 b:"Terra launched on 18 December 1999 for a six-year mission and is still returning imagery in its twenty-seventh. Orbit maintenance stopped in <b>2020</b>; it left the morning constellation in 2022 and its equator crossing has been sliding earlier ever since, from 10:30 towards about 9:00. The pictures are still real, but the light in them is changing — lower sun, longer shadows, year on year. End of science operations is projected for February 2027.",
 p:"NASA Terra mission status; NSIDC data announcement on Terra and Aqua orbit drift."},
reprojection:{k:"ins",t:"Why the picture lines up",
 b:"GIBS publishes polar imagery in EPSG:3413 and EPSG:3031. This deck does not draw either of them — it draws a spherical polar stereographic disc normalised at 45°, and says so in the readout. Rather than pretend, the imagery is fetched as plate carrée and <b>resampled at build time through this deck's own inverse projection</b>. Alignment is then exact by construction rather than by coincidence. Drawing the real tiles is a projection change, and it has not been made yet.",
 p:"ingest/build_imagery.py, using the same proj() the coastlines and stations use."},

/* ---- the living layer ---- */
ovation:{k:"ins",t:"The aurora is a forecast",
 b:"Not a photograph, and stamped <b>MODEL</b> for that reason. A spacecraft at L1, 1.5 million km upstream, measures the solar wind speed and the interplanetary magnetic field; OVATION-Prime turns those into the energy flux of particles precipitating into the atmosphere, from which a viewing probability follows. The roughly half-hour lead time is nothing more than how long the solar wind takes to cross the remaining distance to Earth.",
 p:"NOAA SWPC OVATION-Prime 30-minute forecast. Packed here as two 360 × 46 grids from 45° poleward."},
kp_index:{k:"num",t:"Kp",
 b:"The largest wobble in the horizontal magnetic field over three hours, scaled 0 to 9, averaged across <b>thirteen ground observatories</b> — all of them between 44° and 60° geomagnetic latitude, none of them anywhere near the poles. Five or above is a geomagnetic storm. Read it as a planetary weather report, not as what any one station is seeing tonight: the definitive index comes from GFZ Potsdam, and what updates here every minute is SWPC's running estimate of it.",
 p:"NOAA SWPC estimated planetary K index; definitive Kp from GFZ Potsdam."},
drift_cmcc:{k:"ins",t:"How you measure ice moving",
 b:"You photograph the pack twice, 48 hours apart, and find the displacement that best matches each patch of the first image to the second — maximum cross-correlation. The <b>continuous</b> version used here refines that match between pixels instead of snapping to the grid, which removes most of the quantisation noise. Inputs are SSMIS at 91 GHz, ASCAT and AMSR2. Target accuracy is 5 km per component over the 48 hours, checked against drifting buoys.",
 p:"EUMETSAT OSI SAF OSI-405-c, 62.5 km grid. Only nominal-quality vectors — status flag 30 — are drawn."},
drift_true_length:{k:"num",t:"Why the arrows look short",
 b:"They are drawn at <b>true length</b>. Pack ice typically travels a few kilometres a day, so two days of motion is often less than a single 62.5 km cell — the vector is genuinely shorter than the grid it sits on. Any exaggeration is a lie unless it is labelled, so the multipliers are named on screen when they are on. The pattern is what carries the meaning: where the field converges the ice piles into ridges, where it diverges it opens water.",
 p:"48-hour displacement, unscaled. Head and tail are both real positions."},
sar_s1:{k:"ins",t:"Radar that makes its own light",
 b:"Sentinel-1 carries a C-band synthetic aperture radar at <b>5.405 GHz</b> — a 5.6 cm wavelength. It is active: it illuminates the surface itself, so cloud and polar night are irrelevant to it, and unlike passive microwave it resolves metres rather than kilometres. Over sea ice it runs in Extra Wide mode, five sub-swaths stitched into a 410 km strip at 20 × 40 m. Sentinel-1A was retired in July 2026; the 6-day repeat is now flown by 1C and 1D.",
 p:"ESA Copernicus Sentinel-1 mission specification."},
sar_footprints:{k:"obj",t:"Footprints, not pictures",
 b:"Each outline is <b>where the radar was pointed</b> in the last 18 hours, taken from the Copernicus catalogue of acquisitions — the metadata, not the imagery. The scene behind one of these polygons is a separate download of several hundred megabytes. They fade with age. The product code says how far each has been processed: RAW is unprocessed telemetry, SLC keeps the phase for interferometry, GRD is the multi-looked picture, OCN the level-2 wind and wave fields derived from it.",
 p:"Copernicus Data Space Ecosystem OData catalogue, both polar caps, 18-hour window."},
live_transport:{k:"ins",t:"What live means here",
 b:"A published artifact cannot fetch anything at runtime — no network of any kind reaches it. So the living layers are <b>baked at build time and stamped with their own observation time</b>, never with the build time. The same page built for a web host sets a flag and refreshes the fast layers from the identical endpoints in the browser. One data model, two transports; the honest word for this copy is not <i>live</i> but <i>as of</i>.",
 p:"ingest/build_events.py writes both. The artifact build carries the snapshot; the site build fetches."},
age_stamp:{k:"num",t:"Every layer states its own age",
 b:"The ages in the strip above count from the <b>observation</b>, not from the build. A two-hour-old radar footprint and a day-old drift field are both correct and they mean different things, so there is no single last-updated time on this deck and there should not be one. Collapsing them into one number would be the most convenient available lie.",
 p:"Each source carries its own observation timestamp through ingest to the page."},
drift_pump:{k:"mech",t:"Why drift belongs on this deck",
 b:"The ice map shows where ice is; the drift field shows where it is <b>going</b>, and that is the half that touches the circulation. Ice carried out of the Arctic through Fram Strait — roughly 2,000 to 2,500 km³ a year — melts in the North Atlantic and freshens exactly the water that is supposed to be sinking there. And where the pack pulls apart, it opens leads and polynyas, and open water in winter makes new ice, and new ice rejects brine. Convergence builds ridges; divergence builds the pump.",
 p:"Fram Strait volume export: The Cryosphere 13, 3209 (2019), 2010–2016 satellite and model record."},

/* ---- the platform ---- */
surfaces:{k:"obj",t:"Three surfaces",
 b:"This is one of three. The <b>Deck</b> is the instrument: measured fields, time, and the circulation. <b>Stations</b> is the register of who is actually on the ice — 166 facilities, their operators, and whether any member of the public can see a thing they do. <b>Named Ice</b> is the cultural surface, where the ice has words rather than values. Same data model, same palette, three registers.",
 p:"All three are separate builds. The payload ceiling applies to each surface rather than to the platform."},
stn_deck:{k:"obj",t:"The stations on this map",
 b:"A <b>selection</b>, chosen to sit near the features on screen — not the register. The full one is on the Stations surface: 166 facilities north and south, with operator, seasonality, population, what each observes, how it is reached, and the axis nobody else publishes, which is whether any of it is reachable by someone outside the institution.",
 p:"Deck list is hard-coded. Wiring it to the Atlas register is an open action."},
graticule:{k:"obj",t:"Graticule",
 b:"Meridians every 30° and parallels every 15°, generated rather than sourced. The outer circle is <b>45°</b> — the edge of the polar grid the ice field is delivered on, and therefore the edge of what this deck can draw. It is not the edge of the ice: a sliver of Okhotsk and Bering ice sits outside it, and the extent numbers, which come from the full source grid, include it.",
 p:"Generated. The 45° limit is a property of the EASE2 polar subset, not of the record."}
'''

# insert immediately before the UI section of EXPL
anchor = u'/* ---- UI ---- */'
once(anchor, NEW.rstrip() + u',\n\n' + anchor, "insert new EXPL entries")

print("entries added")
io.open(SRC, "w", encoding="utf8").write(s)
