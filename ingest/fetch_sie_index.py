#!/usr/bin/env python3
"""
fetch_sie_index — OSI SAF's own published sea-ice extent, as a reference record.

Why the deck carries a second extent
------------------------------------
The deck computes its extent itself: cells of the *monthly-mean* concentration
field at or above 15 %, times 625 km2. OSI SAF publishes a different number
for the same month in its Sea Ice Index (OSI-420-a, v3.0): the *mean of the
daily extents*. The order of operations matters. A cell the ice edge crosses
halfway through a month is counted in full by the first method and for half the
month by the second, so the deck's figure runs higher, by 0.36 (Arctic) and
0.53 (Antarctic) million km2 on average over 1978-2026 and by up to 1.5.

A reader who puts the deck beside OSI SAF will find that difference. The deck
log shows both, stamped separately, and the difference between them. The index
is never merged into the deck's record and nothing on the deck is computed
from it.

What is kept
------------
The published values exactly as published: integer km2, with the file's own
header, its creation date, the URL, the retrieval time and the SHA-256 of the
bytes read. -999 (no data) is kept as null. Nothing is rounded or rescaled.

  python ingest/fetch_sie_index.py data/osi/sie_index_v3p0.json
"""
import datetime as dt
import hashlib
import json
import os
import sys
import urllib.request

BASE = "https://osisaf-hl.met.no/archive/osisaf/sea-ice-index/v3p0/timeseries"
URL = BASE + "/{h}/ice_extent_{h}_sii-v3p0_monthly.txt"
M0 = "197811"          # the deck's record starts here; earlier rows are -999


def fetch(h):
    url = URL.format(h=h)
    with urllib.request.urlopen(url, timeout=120) as r:
        raw = r.read()
    txt = raw.decode("utf-8")
    head = [l[2:].strip() for l in txt.splitlines() if l.startswith("#")]
    rows = []
    for l in txt.splitlines():
        if not l.strip() or l.startswith("#"):
            continue
        f = l.split()
        if len(f) < 5:
            raise SystemExit(f"ABORT {h}: unexpected row {l!r}")
        v = int(float(f[4]))
        rows.append((f[1] + f[2], None if v < 0 else v))
    rows = [r for r in rows if r[0] >= M0]
    # the series must be calendar-contiguous: one row per month, no repeats
    for (a, _), (b, _) in zip(rows, rows[1:]):
        ya, ma, yb, mb = int(a[:4]), int(a[4:]), int(b[:4]), int(b[4:])
        if yb * 12 + mb != ya * 12 + ma + 1:
            raise SystemExit(f"ABORT {h}: not contiguous at {a} -> {b}")
    created = next((x.split(":", 1)[1].strip() for x in head if x.lower().startswith("creation date")), None)
    return {
        "url": url,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "created": created,
        "header": head,
        "m0": rows[0][0],
        "mN": rows[-1][0],
        "v": [v for _, v in rows],
    }


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "data/osi/sie_index_v3p0.json"
    doc = {
        "product": "EUMETSAT OSI SAF Sea Ice Index v3.0 (OSI-420-a)",
        "quantity": "sea-ice extent, monthly: the mean of the daily extents (grid cells with concentration > 15 %)",
        "unit": "km2",
        "page": "https://osisaf-hl.met.no/v3p0-sea-ice-index",
        "retrieved_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hemi": {h: fetch(h) for h in ("nh", "sh")},
    }
    for h, H in doc["hemi"].items():
        n = sum(v is not None for v in H["v"])
        print(f"  {h}: {H['m0']} -> {H['mN']}, {len(H['v'])} months, {n} with a value, created {H['created']}, sha256 {H['sha256'][:12]}")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print(f"  wrote {out}")


if __name__ == "__main__":
    main()
