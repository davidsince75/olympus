# Olympus — Arctic & Antarctic portal

Project home: `C:\Users\david\Desktop\Projects\Olympus` · remote `github.com/davidsince75/olympus`, branch `main`.

Three surfaces, one design system, one rule: every value carries its source, its age and whether it
was measured, modelled or drawn.

| Surface | Published file | Artifact | Public site |
|---|---|---|---|
| **The Deck** — sea ice at both poles since 1978, the ocean beneath it | `dist/deck.html` | [fd6023e1](https://claude.ai/code/artifact/fd6023e1-89a7-42a4-aec2-072c8f286c5f) | `site/deck.html` |
| **The Stations** — 166 facilities, who runs them, who can see what they measure | `dist/atlas.html` | [a5b3f808](https://claude.ai/code/artifact/a5b3f808-d2de-4e3e-9bc5-c3d7a684c4a4) | `site/stations.html` |
| **The Named Ice** — the cultural surface | `dist/named_ice.html` | [f24d74f7](https://claude.ai/code/artifact/f24d74f7-e536-4906-9bf5-3b2bc90d71a3) | `site/named-ice.html` |

## The rules for `dist/`

- **`dist/<surface>.html` is exactly what is published** — the bare surface, starting at `<title>`.
  The artifact host adds its own document skeleton; a file that already carries one renders it twice.
  `scripts/verify.cjs` refuses a skeleton.
- **`src/` was retired on 24 Sep 2026.** It had become a second, stale copy of the deck (missing the
  aurora work and more) beside `dist/`. One file per surface; the patch scripts write to `dist/`.
- **The Named Ice is in the repo as of 24 Sep 2026.** Until then its only copy was the published
  artifact — the fourth time a surface had lived only inside a published page.
- **Publish from `dist/`, commit, push — in that order, the same day.** The published deck was ten days
  ahead of the repository when the audit found it.

## How a change is made

Surfaces are changed by patch scripts with exact-string anchors: each anchor must match the stated
number of times or nothing is written, and guards refuse to write a file in which a retired claim
survives. Recent ones, in the order they were applied:

    ingest/patch_ocean.py        12–13 Sep  ocean circulation plane
    ingest/patch_live.py         13 Sep     living layer cached, not rebuilt per frame
    build/patch_globe_surface.py 13 Sep     the globe draws its own imagery
    build/patch_disc_zoom.py     13 Sep     zoom and pan on the discs
    build/patch_aurora.py        14 Sep     an aurora you can see
    build/patch_audit.py         24 Sep     the audit: honesty, first view, phones, Named Ice hero

## The living layer

`ingest/build_events.py` fetches the aurora (SWPC OVATION), Kp, ice drift (OSI SAF OSI-405) and
Sentinel-1 footprints (Copernicus catalogue), no key needed on any of them.
`ingest/inject_live.py` puts the result into the deck and the Atlas.
The first `build_events.py` was lost with its container on 4 Sep; this one was rewritten on 24 Sep
against the payload shape the surfaces already read.

    python ingest/build_events.py data/events/live.json --prev dist/deck.html
    python ingest/inject_live.py data/events/live.json dist/deck.html dist/atlas.html

An artifact cannot fetch at runtime, and its share link is **pinned to a version**, so a republish is
invisible to link-holders until the pin is moved from the artifact's share menu. The living layer can
only stay current in public through the site.

## The public site

`build/build_site.py site --live data/events/live.json` writes the three surfaces as ordinary pages
with relative cross-links, plus a front door (`index.html`) whose two numbers are computed from the
deck's own record and checked against the deck's published figures.
`.github/workflows/pages.yml` rebuilds the living layer and deploys the site every morning at 06:30 UTC.
**To switch it on:** Settings → Pages → Source: *GitHub Actions*. Pages on a private repository needs a
paid plan; otherwise make the repository public.

## Verification

    npm install          # jsdom, playwright
    npm run verify       # = node scripts/verify.cjs

One command, one verdict: the projection, the learning layer on both instrument surfaces, the ocean
plane, deep limbs off land, every layer switch changing the picture, zoom, the Atlas touch paths, the
first view a stranger gets, no retired claims, the size cap, the age of the living layer, and all three
surfaces on a 390 px phone. It needs Chromium at `/opt/pw-browsers` (Claude's build host) or
`OLYMPUS_CHROME`.

## Data

- `data/stations.json` — the register, 166 facilities. Antarctic base is the COMNAP master list,
  **2017 edition**; the Arctic register is compiled. `programmes[]` is populated on three records only.
- `data/osi/` — OSI SAF monthly sea-ice concentration atlases, both hemispheres, Nov 1978 →.
- `data/asi/` — ASI AMSR2 at 6.25 km (two verified frames). Not yet wired into the deck.
- `data/imagery/`, `data/geo/` — GIBS base imagery and the Natural Earth 10 m coastline on
  EPSG:3413 / 3976.

## Known, not fixed

- **The Atlas is still on the old spherical polar stereographic projection** ("normalised at ±45°");
  the deck moved to EPSG:3413/3976 on 12 Sep. The same station sits in a different place on the two
  surfaces.
- The deck's station layer is 20 hard-coded sites, not the Atlas register.
- The deck is 12.8 MiB of a 16 MiB artifact cap. Two more measured layers fill it.
- The builds are a chain of in-place patches on a 13 MB file; there is no build that goes from data to
  page in one step.

## Housekeeping

`_to_delete/` holds git lock files an earlier session could not remove. Delete it by hand.
