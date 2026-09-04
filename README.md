# Olympus — recovered station register

**Recovered 4 September 2026.** The `olympus/` repository built on 4 Sep was delivered as a
tarball that was never saved to disk; it died with its container. The only surviving copy of the
166-facility register was inside the published Atlas artifact, so it was parsed back out of the
published HTML — the exact failure mode `docs/AUDIT` warned about, now having happened twice.

**Keep this folder.** It is currently the only copy of the register outside a published page.

## Files
- `stations.json` — the full register, 166 facilities, pretty-printed. Includes the new
  `programmes` field (see below).
- `atlas.html` — the complete Atlas surface as published, with the corrected data inlined.
  This is the *wrapped* document; the artifact publish payload is this file minus the
  `<!doctype …><body>` wrapper.

## What changed in this recovery
Beyond EPICA had been filed as an operator and as a nation of Little Dome C. It is neither: it is
an EU-funded research **project** — one of roughly twenty in the EU Polar Cluster
(<https://polarcluster.eu>) — that works at a French–Italian camp.

- `aq-little-dome-c-beyond-epica`: name `Little Dome C`; operator `Italy` / `France`;
  nation `Italy`; joint `Italy (PNRA / ENEA)`, `France (IPEV)`. Position unchanged
  (75.30°S 122.44°E), 35 km from Concordia, which the record already had right.
- New `programmes[]` field on **every** record (empty by default), populated on Little Dome C,
  Concordia and Kohnen. Shape:
  `{name, kind, funder, coordinator, network, years, url, network_url}`.
- `meta.schema_note` states the rule: a facility record describes a place and its operator;
  a project that works there goes in `programmes`, never in `operator` or `nation`.
- Operator count 41 → 40 (the phantom "Beyond EPICA consortium (EU)" operator is gone).

## Audited, and clean
The other post-2017 additions were checked for the same conflation. Qinling and Troll Airfield are
national; ALCI, Antarctic Logistics & Expeditions and the International Polar Foundation are real
logistics operators, not projects. Beyond EPICA was the only project filed as infrastructure.

## Not done
`programmes` is populated on three records only. Back-filling it from the EU Polar Cluster roster
— OCEAN:ICE, EPOC, POLARIN, CRYOSCOPE, LIQUIDICE, ICELINK, SnowPI and the rest — is real research
and has not been attempted.
