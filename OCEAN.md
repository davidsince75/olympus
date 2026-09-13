# The ocean circulation plane

Rebuilt 12 September 2026. Replaces the single `thc` layer — seven hand-drawn
polylines with a marching-ant dash — with three registers that are kept apart.

| layer | mode | source |
|---|---|---|
| Near-surface currents | **MEASURED** | NOAA Global Drifter Program near-surface velocity climatology v3.10, 1/4°, drogued at 15 m, annual mean plus twelve climatological months. CC BY 4.0. [doi:10.1016/j.dsr.2017.04.009](https://doi.org/10.1016/j.dsr.2017.04.009) |
| Sea-surface temperature | **MEASURED** | The thermistor on the same drifters. Annual mean, 1/2°, 60 KB. Same DOI and licence. |
| ACC fronts | **MEASURED** | Park & Durand (2019), altimetry-derived ACC fronts from the CNES-CLS18 MDT. CC BY 4.0. [doi:10.17882/59800](https://doi.org/10.17882/59800) |
| Warm upper limb | SCHEMATIC | Path after Talley (2013), drawn at 90–300 m — the half of the circuit that goes north |
| Deep & bottom-water limbs | SCHEMATIC | Paths after Talley (2013) and Lumpkin & Speer (2007); gateways at published positions and sill depths, cited per node |

## Build

    sh ingest/fetch_ocean.sh                                    # two keyless downloads
    python ingest/pack_ocean.py data/gdp_annual.nc data/parkfronts.nc build/ocean.js
    python ingest/patch_ocean.py dist/deck.html build/ocean.js   # --dry to check anchors only
    # anchors are checked and applied in order against a working copy, so a patch
    # may anchor on text an earlier one introduced; nothing is written unless
    # every anchor matched exactly the number of times it claimed
    python ingest/patch_live.py dist/deck.html
    node scripts/probe_ocean.cjs dist/deck.html build/shots

`pack_ocean.py` refuses to emit a non-finite value. It has to: `json.dumps`
writes `NaN`, which is valid JavaScript, and an all-NaN front layer renders as
nothing at all while every count-based test still passes. That is how the first
build of this shipped.

## What the payload is

The velocity field is one RGBA PNG, 1440 × 632, 1.0 MB before base64:

- **R, G** — u and v, signed-sqrt encoded over ±1.5 m/s. Worst-case decode error
  1.0 cm/s, RMS 0.18 cm/s, against a field whose own standard error is far larger.
- **B** — drifter-days per square degree, log-scaled. The sampling density, which
  is wildly uneven and worth showing.
- **A** — 0 where the climatology has no observation. 513,970 of 910,080 cells
  carry data; the rest is land and unsampled ocean, most of it under ice.

Fronts are resampled to 760 vertices each from 3,779–4,253. Limbs carry a depth
per vertex.

## Depth

Deep limbs are drawn inside the translucent globe at a radius set by their depth,
so North Atlantic Deep Water passes visibly underneath the warm water returning
north above it. The ocean is 0.06 % of the Earth's radius, so the vertical scale
is stretched **×165** (6000 m → 0.155 of the globe radius) and the number is
carried in `OCEAN.depth.exag` and stated in the `depth_exag` explainer.
Horizontal positions are not stretched.

## The season

The surface field follows the scrubber. Run the timeline and the Somali Current
reverses with the monsoon, the equatorial bands tighten, the Circumpolar Current
leans with the season.

It is a **climatology**, and the deck never lets that blur: a climatological
September is the average of every September in the record, not September of the
year on the dial. The ice above it is that month, that year, measured; the water
is that month averaged over four decades. The `CURRENT` readout names which one
each sample is, the control bar shows the month, and `Season` turns it off and
falls back to the annual mean.

Resolution was chosen by measurement. Against the true monthly field:

| | error vs the true month | payload |
|---|---|---|
| annual mean alone | 4.82 cm/s RMS | 0 |
| 1° anomaly (shipped) | **1.77 cm/s** | **724 KB** |
| 1/2° anomaly | 1.12 cm/s | 2.51 MB |

3.4× the payload for 0.65 cm/s, well inside the field's own standard error. So
1°, as an anomaly on the full-resolution annual mean, tiled 4×3 into one sheet
and kept as raw encoded bytes (1.4 MB of typed array, decoded with one multiply
at sample time). Where a month has no observation of its own — 4% of cells — the
anomaly is zero, the value falls back to the annual mean, and the readout says
so rather than pretending the month was observed.

## Temperature — the thermo half

The velocity field alone is only the *haline* half of a thermohaline map: every
filament was the same colour whether it carried 24 °C north or 3 °C back. `Temp`
recolours by measured SST from the same drifters — Gulf Stream 24.3 °C in orange,
Labrador Current 3.6 °C in blue, Drake Passage 3.9 °C. Breaks at 10 and 22 °C.
The temperature is also in the `CURRENT` readout at all times, whatever the
colouring.

Eighty cells read below −1.9 °C, the freezing point of seawater, down to
−11.6 °C — beached drifters and failed thermistors. They are **dropped, not
clamped**: the deck says nothing where it knows nothing.

## The warm limb, and why it was missing

The first rebuild removed the warm return flow entirely. The reasoning was that
the surface is measured now, so the warm limb is *shown* by the particle field
and need not be drawn. That is technically true and communicatively wrong: the
conveyor's story is warm-north-at-the-surface, cold-south-at-depth, and only the
cold half was drawn as structure. The Gulf Stream was in the particles but the
same white as everything else — nothing said *this is the water going north*.

It is back, in the deep register, at its true depth in the upper 90–300 m, so it
passes visibly over the NADW limb returning at 3000 m. Two limbs: the main path
from the Indian Ocean round the Cape, across the South Atlantic, through the
Caribbean and Florida Straits and out along the Gulf Stream to the Nordic Seas,
and a branch into the Irminger and Labrador seas.

## Coverage

`Coverage` recolours the same filaments by how much the ocean has actually been
sampled there. The thresholds are the field's own terciles, 158 and 337
drifter-days per square degree, because round numbers put 80% of the ocean in
one bucket. The legend is derived from the ramp in code, never typed beside it.

The finding it exists to show: **95% of the ocean between 40°S and 60°S has been
sampled at all; south of 60°S only 20% has, and north of 60°N only 12%.** Where
no drifter has ever been there is no filament, and the emptiness is the point —
this is the same ocean whose deep water is made in exactly those two places.

## Rates

Two clocks, deliberately separate. The *velocities* change with the month; the
rate they are played back at does not — a fixed, stated 18 days of ocean per
second of wall clock, the only number here chosen by eye. The **deep limbs**
are schematic, so their animation speed is still driven by the observed monthly
RAPID value. Scaling the measured surface field by RAPID would have invented a
link that is not in the data.

## Performance

Three things were costing frames, two of them pre-existing:

1. **The living layer was rebuilt every frame** — 8,100 separate aurora quad
   fills plus up to 3,329 ice-drift vectors, none of which move. Now rendered
   once into two offscreen sheets (two, because the aurora composites with
   `lighter` and the rest does not) and rebuilt only when the hemisphere, size,
   layer switches or drift multiplier change. The Antarctic disc went from
   ~108 ms to ~52 ms a frame on the build host's software rasteriser.
2. **`gpath` begins its own path**, so calling it in a loop and stroking once at
   the end drew only the last ring. The globe had never drawn its coastlines or
   more than one graticule line. `gpathTo` fixes both.
3. **The screen-cell lookup table was rebuilt on every frame of a drag** — an
   `asin` and an `atan2` per cell per side, ~15 ms at rest resolution. Now on a
   26 ms budget while the camera moves; only the ice shell lags, by at most one
   budget period.

The particle layer itself batches each trail into one polyline and buckets by
speed, so it is nine strokes a frame rather than fourteen thousand capped
segments, and an adaptive budget sheds or restores particles to hold 30 fps on
whatever machine it lands on.

## Two failures worth remembering

**`json.dumps` writes bare `NaN`, which is valid JavaScript.** Each Park & Durand
front carries a single non-finite terminator; carrying it through the arc-length
resample turned all 3,800 vertices into NaN. The layer loaded, drew nothing, and
passed every count-based assertion in the probe. `pack_ocean.py` now scans the
whole emitted object and uses `allow_nan=False`, and the probe asserts pixels on
canvas rather than object counts.

**The camera's flick detector was frame-rate absolute.** A fixed 140 ms gap
between the last pointer move and the release meant that on a machine managing
ten frames a second — where two genuine movements are already 100 ms apart — a
real flick was read as a deliberate stop. It now scales with the frame interval
the machine is actually achieving.

## Still schematic, still marked

The deep path between one sill and the next. Everything else in this plane is
measured or is a published position.

## Known, not fixed

The `.feed` strip overflows horizontally at phone width — the document is 507 px
wide in a 420 px viewport. Pre-existing, unrelated to this work, and a one-line
`overflow-x` on the strip container.
