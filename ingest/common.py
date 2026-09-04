"""
Shared conventions for the Olympus global-spine ingest.

Two rules from the deck doctrine are enforced here rather than left to callers:

  1. Everything is keyed by calendar YYYY-MM, never by frame index. The ice
     record has genuine outages (Apr-Jun 1986, Dec 1987) so frame index does
     not equal month offset. The deck joins spine to ice on the calendar key.

  2. Outside a record's published coverage the value is null. Never held,
     never interpolated, never extended. The reader renders "no observation".
"""

import hashlib
import io
import json
import re
import urllib.request
from datetime import datetime, timezone

# The ice record's calendar span. 574 calendar months carrying 570 frames.
CAL_START = (1978, 11)
CAL_END = (2026, 8)

USER_AGENT = "olympus-spine-ingest/1.0 (+build-time ingest, no runtime fetch)"


def month_axis(start=CAL_START, end=CAL_END):
    """Every calendar month in the deck's window, inclusive, as 'YYYY-MM'."""
    y, m = start
    out = []
    while (y, m) <= end:
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def fetch(url, label):
    """Fetch once, at build time, and return bytes plus a provenance stamp."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
        server_date = r.headers.get("Last-Modified") or r.headers.get("Date")
    stamp = {
        "label": label,
        "url": url,
        "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "http_last_modified": server_date,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    return body, stamp


def header_creation_date(text):
    """NOAA GML files carry 'File Creation:' in the comment block. Keep it."""
    m = re.search(r"^#\s*File Creation:\s*(.+?)\s*$", text, re.M)
    return m.group(1) if m else None


def align(values_by_month, axis):
    """
    Project a {'YYYY-MM': value} mapping onto the deck's calendar axis.

    Returns the aligned list plus the counts that make coverage auditable:
    how many months carry an observation, and where the record's own first
    and last observations sit. Months outside coverage are None, not zero.
    """
    aligned = [values_by_month.get(k) for k in axis]
    present = [i for i, v in enumerate(aligned) if v is not None]
    outside = sorted(set(values_by_month) - set(axis))
    return aligned, {
        "months_on_axis": len(axis),
        "months_observed": len(present),
        "first_observed": axis[present[0]] if present else None,
        "last_observed": axis[present[-1]] if present else None,
        "source_months_outside_deck_window": len(outside),
        "source_range": (
            f"{min(values_by_month)} to {max(values_by_month)}"
            if values_by_month else None
        ),
    }


def write_json(path, obj):
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"), sort_keys=False)
    return path
