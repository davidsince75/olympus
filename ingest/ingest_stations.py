"""
ingest_stations.py — INTERACT research stations as a point layer.

Source: stations.js, the data file behind the station globe linked from the
INTERACT Non-Profit Association homepage. It is a GitHub Pages asset on a
personal account, not an official licensed distribution. Treat it as a
prototype source and confirm redistribution with INTERACT before publishing.

Two things the raw file contains that must not reach a published artifact:
station contact email addresses, and a HasSignedGPDRContract flag. Only the
public fields are carried through. The allowlist below is the whole policy --
anything not named is dropped, so a new field appearing upstream is excluded
by default rather than leaking.

Output: stations.json
"""

import json
import re

from common import fetch, write_json

STATIONS_URL = "https://vspadetto.github.io/globe-stations/src/stations.js"
OBSERVERS_URL = "https://vspadetto.github.io/globe-stations/src/observerStations.js"

# The only fields that leave this script.
KEEP = ("StationName", "Acronym", "Website", "Latitude", "Longitude")

# The deck's polar disc is normalised at +/-45 deg. Anything inside this band
# has no disc to sit on and would have to be dropped or drawn on the globe only.
DISC_LIMIT = 45.0

# INTERACT covers Arctic, boreal AND alpine sites. Seven of them sit below
# 55degN -- Jungfraujoch, Gornergrat, Sonnblick, Hintereis and others -- which
# on a disc normalised at +/-45deg land in the outermost ring where distortion
# is worst and no ice is drawn. Banding them lets the deck filter rather than
# smear them round the rim. This band is derived here from latitude alone; it
# is not INTERACT's own classification and must not be presented as such.
ARCTIC_CIRCLE = 66.5622
BOREAL_LIMIT = 55.0


def zone_from_lat(lat):
    if lat >= ARCTIC_CIRCLE:
        return "arctic"
    if lat >= BOREAL_LIMIT:
        return "subarctic"
    return "alpine_or_temperate"


def parse_js_array(text):
    """Strip line comments and the `const x = ...;` wrapper, then JSON-parse."""
    text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    if "[" not in text:
        return []
    body = text[text.index("["):text.rindex("]") + 1]
    body = re.sub(r",\s*([\]}])", r"\1", body)  # tolerate trailing commas
    return json.loads(body)


def clean(raw, kind):
    out, dropped = [], []
    for rec in raw:
        lat, lon = rec.get("Latitude"), rec.get("Longitude")
        name = (rec.get("StationName") or "").strip()
        if lat is None or lon is None or not name:
            dropped.append({"name": name or "(unnamed)", "why": "no coordinates"})
            continue
        lat, lon = float(lat), float(lon)
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            dropped.append({"name": name, "why": f"coordinates out of range ({lat},{lon})"})
            continue
        site = (rec.get("Website") or "").strip()
        if site and not site.startswith(("http://", "https://")):
            site = "https://" + site
        out.append({
            "name": name,
            "acronym": (rec.get("Acronym") or "").strip() or None,
            "website": site or None,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "kind": kind,
            "zone": zone_from_lat(lat),
            "on_disc": "NH" if lat >= DISC_LIMIT else ("SH" if lat <= -DISC_LIMIT else None),
        })
    return out, dropped


def main():
    stations, dropped = [], []
    stamps = []

    for url, kind, label in (
        (STATIONS_URL, "access", "INTERACT transnational-access stations"),
        (OBSERVERS_URL, "observer", "INTERACT observer stations"),
    ):
        body, stamp = fetch(url, label)
        raw = parse_js_array(body.decode("utf-8"))
        got, lost = clean(raw, kind)
        stamp["records_in_file"] = len(raw)
        stamp["records_kept"] = len(got)
        stamps.append(stamp)
        stations.extend(got)
        dropped.extend(lost)

    stations.sort(key=lambda s: -s["lat"])
    lats = [s["lat"] for s in stations]
    off_disc = [s["name"] for s in stations if s["on_disc"] is None]

    doc = {
        "record": "olympus-station-layer",
        "measured": True,
        "kind": "station positions (not observations)",
        "built_utc": stamps[0]["retrieved_utc"],
        "count": len(stations),
        "fields_carried": list(KEEP),
        "fields_deliberately_dropped": [
            "Email", "Contact", "AdminId", "HasSignedGPDRContract",
            "Terms", "Image", "Confirm", "Reject", "StationId",
        ],
        "extent": {
            "lat_min": min(lats) if lats else None,
            "lat_max": max(lats) if lats else None,
            "on_NH_disc": sum(1 for s in stations if s["on_disc"] == "NH"),
            "on_SH_disc": sum(1 for s in stations if s["on_disc"] == "SH"),
            "off_disc": off_disc,
        },
        "zones": {
            z: sum(1 for s in stations if s["zone"] == z)
            for z in ("arctic", "subarctic", "alpine_or_temperate")
        },
        "zone_definition": ("Derived here from latitude: arctic >= 66.5622degN, "
                            "subarctic >= 55degN, otherwise alpine_or_temperate. "
                            "Not INTERACT's classification."),
        "stations": stations,
        "dropped": dropped,
        "provenance": stamps,
        "caveats": [
            "Northern Hemisphere only. The Antarctic disc receives no markers, so "
            "the Both view is asymmetric. INTERACT GIS lists Antarctic bases that "
            "are not in this file.",
            "This is the transnational-access subset, not the ~99 field bases the "
            "INTERACT homepage describes. Do not label it 'the INTERACT network'.",
            "Station positions are not observations. This layer is context: it says "
            "where people work, not what was measured. Stamp it as such.",
            "Unofficial source. Confirm redistribution with INTERACT before publishing.",
        ],
    }

    write_json("stations.json", doc)

    print(f"stations kept   {doc['count']}")
    print(f"lat range       {doc['extent']['lat_min']} .. {doc['extent']['lat_max']}")
    print(f"on NH disc      {doc['extent']['on_NH_disc']}")
    print(f"on SH disc      {doc['extent']['on_SH_disc']}")
    print(f"off disc (<45N) {len(off_disc)}  {off_disc}")
    for z, n in doc["zones"].items():
        print(f"  zone {z:20s} {n}")
    if dropped:
        print("dropped:")
        for d in dropped:
            print("  ", d["name"], "-", d["why"])


if __name__ == "__main__":
    main()
