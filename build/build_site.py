#!/usr/bin/env python3
"""
Olympus — the public site: the same three surfaces at an ordinary URL.

Why this exists (audit, 24 Sep 2026): every surface lived only as a claude.ai
artifact. An artifact cannot fetch, and its share link is pinned to a version,
so each republish stays invisible to link-holders until the pin is moved by
hand. "Live" could never reach the public that way, however often it was
rebuilt. A static host has neither limit.

  python build/build_site.py site [--live data/events/live.json]

Writes:
  site/index.html        the front door: what this is, two measured numbers, three doors
  site/deck.html         dist/deck.html in a full document, cross-links made relative
  site/stations.html     dist/atlas.html, likewise
  site/named-ice.html    dist/named_ice.html, likewise
  site/.nojekyll

The numbers on the front door are computed here from the record inside the
deck — the same arrays, baseline and definitions the deck's anomaly stream
uses — and are checked against the deck's own published figures for a month
where they are known. Nothing on it is typed by hand.
"""
import argparse
import datetime as dt
import html
import json
import math
import os
import shutil
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "ingest"))

SURFACES = [
    ("deck.html", "deck.html", "Olympus — the Deck",
     "Sea ice at both poles, measured every month since November 1978, with the ocean that moves beneath it."),
    ("atlas.html", "stations.html", "Olympus — the Stations",
     "166 polar stations, camps and runways, who runs them, and whether a member of the public can see any of what they measure."),
    ("named_ice.html", "named-ice.html", "Olympus — the Named Ice",
     "The other literature of the ice: Inuit sea-ice terms, the films and paintings that shaped the polar imagination, and the names put back."),
]
ARTIFACT = {
    "https://claude.ai/code/artifact/fd6023e1-89a7-42a4-aec2-072c8f286c5f": "deck.html",
    "https://claude.ai/code/artifact/a5b3f808-d2de-4e3e-9bc5-c3d7a684c4a4": "stations.html",
    "https://claude.ai/code/artifact/f24d74f7-e536-4906-9bf5-3b2bc90d71a3": "named-ice.html",
}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def doc(title, desc, body, bg="#06090E"):
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:type" content="website">
<meta name="color-scheme" content="dark">
<style>html,body{{margin:0;padding:0;background:{bg}}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head><body>
{body}
</body></html>
"""


# ------------------------------------------------------------- the record
def record(deck_src):
    i = deck_src.find("const OSI=")
    j = deck_src.find("\n", i)
    O = json.loads(deck_src[i + len("const OSI="):j].rstrip().rstrip(";"))
    out = {}
    for key, name in (("sh", "Antarctic"), ("nh", "Arctic")):
        h = O["hemi"][key]
        y0, m0 = int(h["m0"][:4]), int(h["m0"][4:]) - 1
        rows = []
        for off, e in zip(h["ymo"], h["ext"]):
            k = m0 + off
            rows.append((y0 + k // 12, k % 12, e))
        y, m, v = rows[-1]
        base = [e for (yy, mm, e) in rows if mm == m and 1991 <= yy <= 2020]
        mean = h["clim"][m]
        sd = math.sqrt(sum((e - mean) ** 2 for e in base) / (len(base) - 1))
        same = sorted(e for (yy, mm, e) in rows if mm == m)
        rank = same.index(v) + 1
        run = 0
        below = v < mean
        for (yy, mm, e) in reversed(rows):
            if (e < h["clim"][mm]) != below:
                break
            run += 1
        start = rows[-run]
        out[key] = dict(name=name, year=y, month=m, v=v, mean=mean, d=v - mean,
                        pct=100 * (v - mean) / mean, sig=(v - mean) / sd, rank=rank, n=len(same),
                        run=run, below=below, since=(start[0], start[1]))
    # Tie-out against figures the deck's anomaly stream published (5 Sep 2026
    # note): Antarctic Aug 2026 17.35 vs 18.70, 3.4 sigma below, third lowest
    # August, 60 months below since Sep 2021; Arctic 142 months since Nov 2014.
    s = out["sh"]
    if (s["year"], s["month"]) == (2026, 7):
        assert abs(s["v"] - 17.35) < 0.006 and abs(s["mean"] - 18.70) < 0.006, s
        assert round(-s["sig"], 1) == 3.4 and s["rank"] == 3, s
        assert s["run"] == 60 and s["since"] == (2021, 8), s
        assert out["nh"]["run"] == 142 and out["nh"]["since"] == (2014, 10), out["nh"]
    return out


def ordinal(n):
    words = ["", "", "second ", "third ", "fourth ", "fifth ", "sixth ", "seventh ", "eighth ", "ninth ", "tenth "]
    if n == 1:
        return "lowest"
    if n < len(words):
        return words[n] + "lowest"
    suf = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suf} lowest"


def front_door(R, live_built):
    s, n = R["sh"], R["nh"]
    mon = MONTHS[s["month"]]

    def card(r, href):
        side = "below" if r["d"] < 0 else "above"
        since = f"{MONTHS[r['since'][1]]} {r['since'][0]}"
        return f"""<a class="card" href="{href}">
  <div class="k">{r['name']} sea ice · {MONTHS[r['month']]} {r['year']}</div>
  <div class="v">{r['v']:.2f}<span> million km²</span></div>
  <div class="d">{abs(r['d']):.2f} {side} the 1991–2020 {MONTHS[r['month']]} mean of {r['mean']:.2f}
    — {abs(r['sig']):.1f} standard deviations. The {ordinal(r['rank'])} {MONTHS[r['month']]} of {r['n']} on record.</div>
  <div class="d">{r['run']} months in a row {'below' if r['below'] else 'above'} the mean for their own month, since {since}.</div>
</a>"""
    body = f"""<style>
:root{{--void:#06090E;--panel:#0D141C;--line:#1D2A38;--line2:#26374A;--ink:#DDE8F1;--ink2:#93A7BA;--ink3:#5F7286;--ice:#7FE3F5;--s1:#0FA5BE;
  --mono:"IBM Plex Mono",ui-monospace,Menlo,monospace;--sans:"IBM Plex Sans",system-ui,sans-serif;--disp:"Saira Condensed","Arial Narrow",sans-serif;--serif:"Cormorant Garamond",Georgia,serif}}
*{{box-sizing:border-box}}
body{{color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}}
main{{max-width:1080px;margin:0 auto;padding:clamp(28px,7vh,80px) clamp(18px,4vw,40px) 48px}}
.brand{{font-family:var(--disp);font-weight:700;letter-spacing:.16em;text-transform:uppercase;font-size:14px;color:var(--ink2)}}
h1{{font-family:var(--serif);font-weight:300;font-size:clamp(38px,6.4vw,76px);line-height:1.02;margin:18px 0 0;max-width:13em;letter-spacing:-.01em}}
h1 em{{color:var(--ice)}}
.lede{{font-size:clamp(16px,1.8vw,19px);line-height:1.6;color:var(--ink2);max-width:40em;margin:22px 0 0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin-top:clamp(28px,5vh,48px)}}
.card{{background:var(--panel);padding:20px 22px;color:inherit;text-decoration:none;display:block}}
.card:hover{{background:#121C26}}
.card .k{{font-family:var(--mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3)}}
.card .v{{font-family:var(--mono);font-size:clamp(34px,5vw,46px);margin-top:6px;font-variant-numeric:tabular-nums}}
.card .v span{{font-size:13px;color:var(--ink3);margin-left:6px}}
.card .d{{font-size:14px;line-height:1.55;color:var(--ink2);margin-top:8px}}
.doors{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;margin-top:clamp(28px,5vh,48px)}}
.door{{border:1px solid var(--line2);padding:18px 18px 16px;color:inherit;text-decoration:none;display:block;border-radius:2px}}
.door:hover{{border-color:var(--s1);background:rgba(15,165,190,.06)}}
.door b{{font-family:var(--disp);font-size:18px;letter-spacing:.1em;text-transform:uppercase;display:block;color:var(--ice)}}
.door span{{font-size:14px;line-height:1.5;color:var(--ink2);display:block;margin-top:6px}}
.prov{{font-family:var(--mono);font-size:11px;line-height:1.8;color:var(--ink3);margin-top:40px;border-top:1px solid var(--line);padding-top:16px;max-width:70em}}
.prov a{{color:var(--ink2)}}
</style>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;1,300&family=IBM+Plex+Mono:wght@400&family=IBM+Plex+Sans:wght@400&family=Saira+Condensed:wght@700&display=swap" media="print" onload="this.media='all'">
<main>
  <div class="brand">Olympus</div>
  <h1>Both poles, <em>measured</em>, every month since November 1978.</h1>
  <p class="lede">A satellite has watched the sea ice at both ends of the Earth for forty-seven years.
  Here is what it saw in {mon} {s['year']}, set against its own 1991–2020 average — and, behind these
  numbers, the instrument that draws them, the stations where people work on the ice, and the older
  literature of the ice that no satellite records.</p>
  <div class="cards">
{card(s, "deck.html")}
{card(n, "deck.html")}
  </div>
  <div class="doors">
    <a class="door" href="deck.html"><b>The Deck</b><span>The instrument. Sea ice at both poles, month by month, with the currents beneath it and where every number comes from.</span></a>
    <a class="door" href="stations.html"><b>The Stations</b><span>166 polar stations, camps and runways, who runs them, and whether you can see any of what they measure.</span></a>
    <a class="door" href="named-ice.html"><b>The Named Ice</b><span>Fifty-nine Inuktitut words for one substance, and the pictures and films that made the poles in our heads.</span></a>
  </div>
  <div class="prov">Extent: EUMETSAT OSI SAF sea-ice concentration, integrated on the 25 km EASE2 grid at the 15 % threshold,
  computed at build time from the same arrays the Deck draws. Baseline: the 1991–2020 mean of the same calendar month.
  Living layers (aurora, Kp, ice drift, radar footprints) {('rebuilt ' + live_built) if live_built else 'as of their stated observation times'}.
  Nothing on this page is typed by hand.</div>
</main>"""
    return doc("Olympus — both poles, measured",
               f"Antarctic sea ice in {mon} {s['year']}: {s['v']:.2f} million km², {abs(s['sig']):.1f} standard deviations "
               f"{'below' if s['d'] < 0 else 'above'} the 1991–2020 mean.", body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--live", help="payload from ingest/build_events.py to put into the deck and the Atlas")
    a = ap.parse_args()
    live_txt = None
    if a.live and os.path.exists(a.live):
        live_txt = open(a.live, encoding="utf-8").read().strip()
        json.loads(live_txt)
    elif a.live:
        print(f"  ..  {a.live} not found — publishing the living layer already in dist/, with its own age")
    if os.path.isdir(a.out):
        shutil.rmtree(a.out)
    os.makedirs(a.out)
    deck_src = None
    live_built = None
    for src, dst, title, desc in SURFACES:
        s = open(os.path.join(ROOT, "dist", src), encoding="utf-8").read()
        if s.lstrip().lower().startswith("<!doctype"):
            raise SystemExit(f"ABORT dist/{src} carries a document skeleton; dist/ must hold the bare surface")
        for url, rel in ARTIFACT.items():
            s = s.replace(url, rel)
        if live_txt and "\nconst LIVE = " in s:
            i = s.find("\nconst LIVE = ") + 1
            j = s.find("\n", i)
            s = s[:i] + "const LIVE = " + live_txt + ";" + s[j:]
        if "\nconst LIVE = " in s:
            i = s.find("\nconst LIVE = ") + 14
            live_built = json.loads(s[i:s.find("\n", i)].rstrip().rstrip(";"))["meta"]["built"]
        if "claude.ai/code/artifact" in s:
            raise SystemExit(f"ABORT {dst}: a cross-link still points at an artifact")
        bg = "#0A0C11" if src == "named_ice.html" else "#06090E"
        open(os.path.join(a.out, dst), "w", encoding="utf-8").write(doc(title, desc, s, bg))
        if src == "deck.html":
            deck_src = s
        print(f"  ok  {dst}  {len(s)/1e6:.2f} MB")
    R = record(deck_src)
    open(os.path.join(a.out, "index.html"), "w", encoding="utf-8").write(front_door(R, live_built))
    open(os.path.join(a.out, ".nojekyll"), "w").write("")
    s = R["sh"]
    print(f"  ok  index.html  Antarctic {MONTHS[s['month']]} {s['year']}: {s['v']:.2f} vs {s['mean']:.2f}, "
          f"{s['sig']:+.1f} sigma, {ordinal(s['rank'])} of {s['n']}, run {s['run']}")


if __name__ == "__main__":
    main()
