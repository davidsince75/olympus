# Global spine + station layer — ingest

**Date:** 3 September 2026 · Ingest built and verified. Not yet wired into the deck.

## What this adds

Two things, on the same time transport the ice already uses.

**The spine** — three records that give the ice field a cause and a context. CO₂ is the forcing; global temperature is the response; the zonal breakdown is why the two poles behave differently.

**The station layer** — 39 INTERACT research stations as points on the Arctic disc. Positions, not observations. It is the first thing on the deck that shows people rather than instruments, and it pre-figures the Channel.

## Sources

| Record | Product | Coverage | Cadence | Licence |
|---|---|---|---|---|
| `CO2_GLOBAL` | NOAA GML globally averaged marine surface CO₂, `co2_mm_gl.csv` | 1979-01 → 2026-05 | monthly | CC0 |
| `T_GLOBAL` | NASA GISTEMP v4 land-ocean anomaly, `GLB.Ts+dSST.csv` | 1880 → 2026-07 | monthly | public domain |
| `T_ZONAL` | NASA GISTEMP v4 zonal anomaly, `ZonAnn.Ts+dSST.csv`, 14 bands | 1880 → 2025 | **annual** | public domain |
| Stations | INTERACT `stations.js` | — | static | **unconfirmed** |

All keyless, all plain HTTP downloads. No account, no quota.

## The number worth building the layer around

Trends fitted by OLS on annual band means over 1979–2025 — the satellite ice window. Computed from this record.

| Band | Trend | vs global |
|---|---|---|
| Global | +0.207 K/decade | 1.00× |
| Northern Hemisphere | +0.298 | 1.44× |
| Southern Hemisphere | +0.114 | 0.55× |
| **64°N–90°N** | **+0.678** | **3.28×** |
| 44°N–64°N | +0.336 | 1.62× |
| 24°S–24°N | +0.154 | 0.74× |
| 64°S–44°S | **+0.008** | 0.04× |
| 90°S–64°S | +0.143 | 0.69× |

The Arctic warms at 3.3× the global rate. The Southern high latitudes warm at 0.69×, and the Southern Ocean band immediately north of them is effectively flat — +0.008 K/decade over 47 years, the slowest-warming latitude band on the planet.

That pairing is the point. The **Both** view already makes the counter-phase legible and says nothing about why. This is the why, and it is measured.

**Caveat to carry on screen:** Rantanen et al. 2022 report ~3.8× using ERA5 north of 66.5°N for 1979–2021. This is GISTEMP north of 64°N. Different record, different boundary, both defensible. Name which one is being shown.

## Design decisions taken

- **The spine is a readout register, not a layer.** These are scalars over time; they have no map. They hang off the time transport beside the extent readout, not in the layer stack beside ice concentration.
- **Everything is keyed by calendar `YYYY-MM`, never by frame index.** The ice record's outages (1986-04…06, 1987-12) mean frame index ≠ month offset. The join is on the calendar key so the gaps survive the join. This is enforced in `common.py`, not left to the reader.
- **CO₂ is subordinate.** The Keeling curve is the most-rendered dataset in existence and a ppm counter in a corner is decoration. It earns its place as the forcing term that makes the amplification mean something. It should not lead.
- **Three different end months.** Ice → 2026-08, GISTEMP → 2026-07, CO₂ → 2026-05. Each series reads `no observation` past its own end — the pattern the AMOC gauge already uses. Do not hold the last value.
- **Records are never merged.** GISTEMP is not HadCRUT and is not ERA5. A second temperature record gets its own mark, as NSIDC does beside OSI SAF.
- **Zonal is annual only.** GISTEMP publishes no monthly zonal means; monthly bands would mean processing the gridded NetCDF. The cadence mismatch is stamped in the payload. Do not render an annual value on the monthly transport without saying so.

## The station layer, honestly

`stations.js` is the data file behind the globe linked from the INTERACT homepage. It is a GitHub Pages asset on a personal account — **not an official licensed distribution**. Usable to prototype; confirm redistribution with INTERACT before publishing. That conversation is one you want anyway.

Four things that constrain what it can claim:

1. **39 stations, not 99.** This is the transnational-access subset, matching eu-interact.org's "transnational access to 43 research stations", not the homepage's 99 field bases. The companion `observerStations.js` is entirely commented out in the published copy. Do not label the layer "the INTERACT network".
2. **Northern Hemisphere only.** Latitudes 45.98°N to 81.60°N. The Antarctic disc gets zero markers and the **Both** view goes asymmetric. INTERACT GIS lists Antarctic bases (Bulgarian St. Kliment Ohridski among them) that are not in this file.
3. **Seven stations are alpine, not polar** — Jungfraujoch, Gornergrat, Sonnblick, Hintereis, Kłapa, and two others below 55°N. On a disc normalised at ±45° they land in the outermost ring where distortion is worst and no ice is drawn. Each record carries a `zone` field (21 arctic / 11 subarctic / 7 alpine_or_temperate) so the deck can filter rather than smear them round the rim. **That band is derived here from latitude alone and is not INTERACT's classification** — do not present it as theirs.
4. **Positions are not observations.** The layer says where people work, not what was measured. It needs its own stamp category, distinct from both measured and `SIM`.

**Privacy.** The raw file carries station contact emails, an `AdminId`, and a `HasSignedGPDRContract` flag. `ingest_stations.py` uses an allowlist, so anything not explicitly named is dropped — a new upstream field is excluded by default rather than leaked. `pack_spine.py` verifies by inspecting record keys and fails the build if any dropped field reappears.

Also worth flagging for the provenance thesis: the INTERACT homepage carries both "around 1,500 researchers accessing over 50 research stations" and "around 15,000 researchers accessing over 90 research stations annually" in adjacent blocks on the same page. Neither figure is quotable until that resolves.

## Pipeline

`ingest_spine.py` and `ingest_stations.py` fetch, normalise onto the 574-month calendar axis, and stamp → `pack_spine.py` merges, verifies, and writes `olympus_spine.js` assigning a frozen object to `window.OLYMPUS_SPINE`.

Every fetch records URL, retrieval time, `Last-Modified`, byte count and SHA-256. NOAA's `File Creation:` header is preserved.

`pack_spine.py` exits non-zero on failure rather than emitting a bad payload. It checks the axis is complete, ascending and duplicate-free; that every monthly series matches the axis length and has no interior holes; that the ice-outage months are present on the axis; that the zonal bands align with their year axis and the amplification ratio is in a sane range; and that no dropped station field reappears as a record key.

**Payload: 43.8 KB raw, 14.1 KB gzipped.** Against 8.78 MB of remaining headroom, this costs 0.49% of what is left. The deck goes 7.22 → 7.26 MB.

## Not done

- Not wired into the deck. The readout register, the station markers and the explainer entries all need the deck source.
- Antarctic stations. Needs a source that is not this file.
- Monthly zonal bands. Needs the gridded NetCDF.
- INTERACT redistribution confirmation.
- A second temperature record (HadCRUT5, CC BY 4.0) as a separately-marked comparison, the way NSIDC sits beside OSI SAF.
