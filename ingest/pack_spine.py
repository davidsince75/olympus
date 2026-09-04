"""
pack_spine.py — merge, verify, and emit the baked payload.

A published artifact cannot fetch at runtime, so everything the deck reads has
to be inside it. This produces one file, olympus_spine.js, that assigns a
frozen object to window.OLYMPUS_SPINE.

The verification below is the point of the script. It fails loudly rather than
shipping a payload that is subtly wrong, because a wrong number that renders
cleanly is worse than no number.

Output: olympus_spine.js, plus a printed audit.
"""

import gzip
import json
import re
import sys

# Deck budget, from the v2 notes: 7.22 MB used of a 16 MB artifact cap.
CAP_MB = 16.0
DECK_MB = 7.22

# Genuine passive-microwave outages in the ice record. The spine must not
# quietly fill them, and the deck must not treat spine coverage as ice coverage.
ICE_GAPS = ["1986-04", "1986-05", "1986-06", "1987-12"]

FAILURES = []


def check(ok, msg):
    print(("  PASS  " if ok else "  FAIL  ") + msg)
    if not ok:
        FAILURES.append(msg)


def main():
    spine = json.load(open("spine.json"))
    stations = json.load(open("stations.json"))
    axis = spine["axis"]

    print("calendar axis")
    check(len(axis) == spine["calendar"]["months"], f"axis length {len(axis)}")
    check(len(set(axis)) == len(axis), "no duplicate months")
    check(axis == sorted(axis), "months strictly ascending")
    check(all(re.fullmatch(r"\d{4}-\d{2}", k) for k in axis), "keys well formed")
    check(all(g in axis for g in ICE_GAPS), "ice-outage months present on the axis")

    print("\nmonthly series")
    for name, s in spine["series"].items():
        if s["cadence"] != "monthly":
            continue
        v = s["values"]
        check(len(v) == len(axis), f"{name} length matches axis")
        obs = [i for i, x in enumerate(v) if x is not None]
        if obs:
            interior = v[obs[0]:obs[-1] + 1]
            holes = [axis[obs[0] + i] for i, x in enumerate(interior) if x is None]
            check(not holes, f"{name} has no interior holes"
                             + (f" (found {holes})" if holes else ""))
            print(f"        {name} spans {axis[obs[0]]} to {axis[obs[-1]]}, "
                  f"{len(obs)} observations")
        # A spine series must not invent values in the ice outages either way;
        # it may legitimately have them, but the deck needs to know.
        in_gap = [g for g in ICE_GAPS if v[axis.index(g)] is not None]
        print(f"        {name} carries values in {len(in_gap)}/{len(ICE_GAPS)} "
              f"ice-outage months (expected: the spine is independent of the ice)")

    print("\nzonal series")
    z = spine["series"]["T_ZONAL"]
    check(z["cadence"] == "annual", "declared annual, not monthly")
    check(all(len(vals) == len(z["years"]) for vals in z["values"].values()),
          "every band matches the year axis")
    g = z["trend_k_per_decade"].get("Glob")
    check(g is not None and g > 0, f"global trend positive ({g} K/decade)")
    arc = z["amplification_vs_global"].get("64N-90N")
    check(arc is not None and 2.5 < arc < 4.5,
          f"Arctic amplification in a sane range ({arc}x)")

    print("\nstation layer")
    records = stations["stations"]
    record_blob = json.dumps(records)
    check("@" not in record_blob, "no email addresses in station records")

    # Check keys, not substrings. Prose elsewhere in the document legitimately
    # contains words like "Confirm"; only the records themselves are the risk.
    keys_present = set()
    for r in records:
        keys_present.update(r.keys())
    leaked = sorted(k for k in keys_present
                    if k in set(stations["fields_deliberately_dropped"]))
    check(not leaked, "no dropped field appears as a station-record key"
                      + (f" (leaked: {leaked})" if leaked else ""))
    check(keys_present == {"name", "acronym", "website", "lat", "lon", "kind",
                           "zone", "on_disc"},
          f"station records carry exactly the intended keys ({sorted(keys_present)})")
    check(all(-90 <= s["lat"] <= 90 for s in stations["stations"]), "latitudes in range")
    check(all(-180 <= s["lon"] <= 180 for s in stations["stations"]), "longitudes in range")
    check(stations["extent"]["on_SH_disc"] == 0,
          "Antarctic disc is empty -- Both view will be asymmetric (known, not a bug)")

    print("\npayload")
    payload = {
        "spine": spine,
        "stations": stations,
        "note": ("Baked at build time. Nothing here is fetched at runtime; the "
                 "sandbox blocks outbound requests and that is the reason this "
                 "file exists."),
    }
    js = ("// Olympus global spine -- baked payload, do not edit by hand.\n"
          "// Regenerate with ingest_spine.py, ingest_stations.py, pack_spine.py\n"
          "window.OLYMPUS_SPINE = Object.freeze("
          + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
          + ");\n")
    with open("olympus_spine.js", "w", encoding="utf-8") as f:
        f.write(js)

    raw_kb = len(js.encode("utf-8")) / 1024
    gz_kb = len(gzip.compress(js.encode("utf-8"), 9)) / 1024
    headroom = CAP_MB - DECK_MB
    print(f"        raw       {raw_kb:8.1f} KB")
    print(f"        gzipped   {gz_kb:8.1f} KB")
    print(f"        deck now  {DECK_MB:8.2f} MB of {CAP_MB:.0f} MB "
          f"({headroom:.2f} MB headroom)")
    print(f"        after     {DECK_MB + raw_kb / 1024:8.2f} MB "
          f"({raw_kb / 1024 / headroom * 100:.2f}% of remaining headroom)")

    print()
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED -- do not publish")
        sys.exit(1)
    print("all checks passed -- olympus_spine.js ready to bake")


if __name__ == "__main__":
    main()
