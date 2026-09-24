#!/usr/bin/env python3
"""
Olympus — the Deck log: the record behind the picture, as tables.

David, 24 Sep 2026: "Scientists don't care about pretty pictures and animated
maps. They care about data." The deck showed numbers but not the record they
came from in a form anyone could check. The log adds that, as a view on the
same arrays the map draws from, not as a new layer:

  This month  every quantity at the month on the dial, at the precision it is
              carried, with its product, file and status; and, for each layer on
              the map, what it is actually showing for that month (a measured
              month, a climatology, a snapshot with its own date, a schematic)
  Series      the scalar records in full with CSV export: sea-ice extent both
              hemispheres (gaps as empty rows marked NO OBS), the 1991-2020
              climatology, RAPID, RONI, weekly Nino-3.4, the NSIDC reference
              points and Kp
  Sources     product, version, DOI, licence, coverage and every step from the
              published value to the pixel, plus dated checks that re-derived
              what is carried from the publishers' own files

What building it found, and what this patch changes because of it
------------------------------------------------------------------
1. The deck's extent is not OSI SAF's published extent. The deck thresholds the
   month's mean concentration field; OSI SAF (and NSIDC) average the daily
   extents. Checked from OSI SAF's own files: Antarctic December 2019 is 11.148
   by the deck's method and 9.848 as a mean of 31 daily extents; OSI SAF
   publishes 9.849. Over 1978-2026 the deck runs 0.36 (Arctic) and 0.53
   (Antarctic) million km2 higher on average, up to 1.5. The deck keeps its
   number, which is computed from the same cells it draws, but now names it
   precisely, and the log carries OSI SAF's Sea Ice Index v3.0 beside it as a
   stamped reference (data/osi/sie_index_v3p0.json, never merged).
2. The "two agencies" explainer put the whole September 2012 gap (4.12 against
   about 3.6) down to OSI SAF against NSIDC. OSI SAF's own index says 3.99; the
   first 0.13 is the deck's method. Rewritten.
3. The concentration explainer said the source files carry per-cell
   uncertainty. The monthly files the deck reads carry none; the daily files do.
   Corrected.
4. OSI-450-a and OSI-430-a are licensed on condition that "Copyright EUMETSAT"
   is shown under the product. Nothing on the deck said it. Added under the
   concentration legend.

A file is saved through the viewer's own save inside claude.ai (the `downloads`
capability, which the publish must declare), through the browser on an ordinary
web host, and where neither is possible the CSV is shown as selectable text.

Exact-string anchors, applied in order; each must match once or nothing is
written. Sources for the inserted code live in build/decklog/.

  python build/patch_decklog.py [--dry]      # patches dist/deck.html
  python build/patch_decklog.py --refresh    # after ingest/fetch_sie_index.py and
                                             # ingest/check_sources.py: renews the payload only
"""
import datetime as dt
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "build", "decklog")


def rd(name):
    return open(os.path.join(SRC, name), encoding="utf-8").read()


def payload():
    sii = json.load(open(os.path.join(ROOT, "data", "osi", "sie_index_v3p0.json"), encoding="utf-8"))
    checks = json.load(open(os.path.join(ROOT, "data", "checks", "sources.json"), encoding="utf-8"),
                       parse_constant=lambda c: (_ for _ in ()).throw(ValueError(f"non-finite {c} in checks")))
    doc = {
        "build": {"built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "by": "build/patch_decklog.py"},
        "sii": sii,
        "checks": checks,
    }
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


BUTTON = ('    <button type="button" class="logbtn" id="logBtn" aria-pressed="false" aria-controls="dlog" '
          'data-ex="deck_log" title="Deck log (L)"><svg class="glyph" viewBox="0 0 10 10" aria-hidden="true">'
          '<path d="M1 1.5h8M1 4h8M1 6.5h8M1 9h5" stroke="currentColor" stroke-width="1.1" fill="none"/></svg>Log</button>\n')

EXPLAINERS = r''',

/* ---- the deck log ---- */
deck_log:{k:"ins",t:"The deck log",
 b:"Every number behind the picture, as a table you can check and take away. <b>This month</b> lists each value the deck holds for the month on the dial, at the precision it is carried, with its product, its file and what kind of claim it is, and says for every layer on the map whether it is that month, an average of all such months, or a snapshot with its own date. <b>Series</b> has the scalar records in full, with a CSV of each. <b>Sources</b> traces every layer from the published value to the pixel and lists the checks that re-derived it from the publisher’s own files. The log follows the dial. Press <b>L</b> to open or close it.",
 p:"A view on the arrays the map draws from. Nothing in it is fetched, and gridded fields are not re-exported: the log names the product instead."},
log_extent:{k:"num",t:"Which extent this is",
 b:"There are two standard ways to turn a month of sea-ice concentration into one extent, and they give different answers. This deck takes the month’s <b>mean concentration field</b> and counts every cell at 15 % or more. OSI SAF and NSIDC work out an extent for <b>each day</b> and average those. A cell the ice edge crosses halfway through the month is counted in full by the first method and for half the month by the second, so the deck’s figure is larger: over 1978–2026 by about 0.4 million km² in the Arctic and 0.5 in the Antarctic, and by up to 1.5 in months when the edge moves fast. The deck keeps its method because the number then comes from exactly the cells that are drawn. The published figure is the one quoted in the literature, and the log shows both side by side.",
 p:"Recomputed from OSI SAF’s own files for four months; see Sources in the log. Antarctic December 2019: monthly-mean field 11.148, mean of the 31 daily extents 9.848, OSI SAF’s published index 9.849."},
sie_index:{k:"ins",t:"OSI SAF’s Sea Ice Index",
 b:"OSI SAF’s own monthly extent (OSI-420-a, version 3.0): the mean of the daily extents, counting cells above 15 %, from its sea-ice concentration records. It is kept here exactly as published, in km², with the file’s creation date and checksum. It is a <b>reference</b>: the deck never computes anything from it and never merges it into its own record.",
 p:"ingest/fetch_sie_index.py → data/osi/sie_index_v3p0.json. osisaf-hl.met.no/v3p0-sea-ice-index."},
log_status:{k:"num",t:"What the status words mean",
 b:"<b>MEAS</b> is a measured value from the product named beside it; <b>FT</b> is the provisional fast-track version of one. <b>DERIVED</b> is computed in this page from values it carries. <b>REF</b> is another agency’s published figure, shown and never used. <b>CLIM</b> and <b>MEAN</b> are averages over many years, not the month on the dial. <b>AS OF</b> is a snapshot with its own date. <b>MODEL</b>, <b>SCHEMATIC</b> and <b>SIM</b> are not measurements. <b>NO OBS</b> means the source has nothing there, and the value is left empty rather than filled. <b>NOT CARRIED</b> means the source has it and this page does not.",
 p:"One word per kind of claim, the same in every table and in every CSV."},
log_build:{k:"num",t:"Which build this is",
 b:"Two times, because the page is built in two parts. The log’s own tables and checks were assembled at the first time; the living layer (El Niño, aurora, Kp, ice drift, radar footprints) was rebuilt at the second. Every CSV carries both, so a number taken away from here can be traced to the build it came from.",
 p:"A published link can be pinned to an earlier version of the page: the stamp is the way to tell."},
log_checks:{k:"ins",t:"The checks",
 b:"Two kinds. Some run in your browser on the values the page carries, such as recomputing the 1991–2020 climatology from the extents. The others were run at build time against the publishers’ own files: the RAPID monthly means recomputed from <code>moc_transports.nc</code>, the ENSO series compared value for value with NOAA’s, and the two extent methods worked out from OSI SAF’s monthly and daily files. Each says whether the values agree or differ, and when it was run.",
 p:"ingest/check_sources.py → data/checks/sources.json."},
eumetsat_credit:{k:"ins",t:"Copyright EUMETSAT",
 b:"The sea-ice concentration records are free to use on one condition: the words <b>Copyright EUMETSAT</b> are shown with the product. OSI-438, the newest record, is licensed CC BY 4.0.",
 p:"Licence text in the OSI-450-a and OSI-430-a files; OSI-438 file attribute: CC-BY-4.0."}
};'''

NSIDC_OLD = (' b:"OSI SAF and NSIDC publish different numbers for the same month — typically 0.1 to 0.5 million km² apart, '
             'and for September 2012 the Arctic gap is 4.12 against about 3.6. Neither is wrong. They use different retrieval '
             'algorithms and different corrections for land contamination. The honest response is to pick one and stamp it, '
             'never to average them.",\n p:"OSI SAF values on this deck; NSIDC daily records shown separately as orange rings."}')
NSIDC_NEW = (' b:"OSI SAF and NSIDC publish different numbers for the same month. Neither is wrong: they use different retrieval '
             'algorithms and different corrections for land contamination, and the honest response is to pick one and stamp it, '
             'never to average them. The deck adds a third number of its own. For the Arctic in September 2012 it reads <b>4.12</b>; '
             'OSI SAF’s published index reads <b>3.99</b> and NSIDC about 3.6. Only the step from 3.99 to 3.6 is between the agencies. '
             'The step from 4.12 to 3.99 is this deck’s method: it counts the edge in the month’s mean concentration field, where both '
             'agencies average the daily extents.",\n'
             ' p:"OSI SAF values on this deck; OSI SAF’s published index beside them in the Deck log; NSIDC daily records as orange rings on the timeline."}')

EDITS = [
    ("log styles",
     "@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}\n</style>",
     None, 1),
    ("log button in the header",
     '    <nav class="xnav" aria-label="Olympus surfaces" data-ex="surfaces">',
     None, 1),
    ("log panel over the three columns",
     "    </section>\n  </div>\n\n  <!-- TRANSPORT -->",
     None, 1),
    ("Copyright EUMETSAT under the concentration legend",
     '<div class="rl"><span>15%</span><span>50%</span><span>100%</span></div>',
     '<div class="rl"><span>15%</span><span>50%</span><span>100%</span></div>\n'
     '              <div class="cr" data-ex="eumetsat_credit">Copyright EUMETSAT</div>', 1),
    ("the hero names which extent it is",
     '<span class="prov" data-ex="threshold"><b>Integrated on the EASE2 source grid · ≥15% threshold</b>',
     '<span class="prov" data-ex="log_extent"><b>Monthly-mean field · EASE2 grid · ≥15%</b>', 1),
    ("the log's payload",
     "\nconst LIVE_FETCH = false;\n",
     None, 1),
    ("the log's code",
     "\n/* ---------------- boot ---------------- */\n",
     None, 1),
    ("boot",
     "st.t=NMON-1;                         // open on the most recent month on the record\n"
     "maskFor(true); maskFor(false); buildLandTex();\nsync(); drawTL();\n",
     "st.t=NMON-1;                         // open on the most recent month on the record\n"
     "maskFor(true); maskFor(false); buildLandTex();\nsync(); drawTL();\ndecklog();\n", 1),
    ("the log follows the dial",
     "  // the stream describes the month on screen, so it moves with it\n  try{ events(); }catch(e){}\n}",
     "  // the stream describes the month on screen, so it moves with it\n  try{ events(); }catch(e){}\n"
     "  // and so does the log, when it is open\n  try{ logSync(); }catch(e){}\n}", 1),
    ("explainers for the log",
     'p:"OSI SAF monthly extent, Nov 1978 – Aug 2026."}\n};',
     'p:"OSI SAF monthly extent, Nov 1978 – Aug 2026."}' + EXPLAINERS, 1),
    ("extent explainer names its method",
     ' p:"Counted on the OSI SAF EASE2 grid: cells ≥15% × 625 km²."}',
     ' p:"Counted on the OSI SAF EASE2 grid in the month’s mean concentration field: cells ≥ 15 % × 625 km². '
     'OSI SAF’s own published figure averages the daily extents instead and runs lower; the Deck log shows both."}', 1),
    ("two agencies, and the deck's own method", NSIDC_OLD, NSIDC_NEW, 1),
    ("concentration uncertainty, where it actually is",
     ' p:"OSI SAF ice_conc variable, per cell, with per-cell uncertainty in the source files."}',
     ' p:"OSI SAF ice_conc, per cell. The monthly files read here carry no uncertainty; OSI SAF’s daily files carry a '
     'per-cell total_standard_uncertainty, which the deck does not propagate."}', 1),
    ("footer points at the log",
     "Turn <b>LEARN</b> on and hover anything to find out what it is.</p>",
     "Turn <b>LEARN</b> on and hover anything to find out what it is. <b>Log</b>, in the header, lays out every number "
     "behind the picture as a table, with its source, its status and a CSV.</p>", 1),
]

GUARD_ABSENT = ["the Arctic gap is 4.12 against about 3.6", "with per-cell uncertainty in the source files"]
GUARD_PRESENT = ['id="dlog"', 'id="logBtn"', "\nconst DECKLOG = ", "function decklog(", "logSync(); }catch(e){}",
                 "Copyright EUMETSAT", 'deck_log:{k:"ins"', 'log_extent:{k:"num"']


def main():
    dry = "--dry" in sys.argv
    path = os.path.join(ROOT, "dist", "deck.html")
    src = open(path, encoding="utf-8", newline="").read()
    if "\nconst DECKLOG = " in src:
        if "--refresh" not in sys.argv:
            raise SystemExit("ABORT — the log is already in dist/deck.html (use --refresh to renew its payload)")
        # renew the reference index and the dated checks, and nothing else
        if src.count("\nconst DECKLOG = ") != 1:
            raise SystemExit("ABORT — more than one DECKLOG payload")
        i = src.find("\nconst DECKLOG = ") + 1
        j = src.find("\n", i)
        out = src[:i] + "const DECKLOG = " + payload() + ";" + src[j:]
        print(f"  ok  DECKLOG payload renewed ({(j - i) / 1e3:.0f} KB -> {len(payload()) / 1e3:.0f} KB)")
        if not dry:
            open(path, "w", encoding="utf-8", newline="").write(out)
        return
    fills = {
        "log styles": rd("decklog.css") + "\n",
        "log button in the header": BUTTON,
        "log panel over the three columns": None,
        "the log's payload": "\nconst DECKLOG = " + payload() + ";\nconst LIVE_FETCH = false;\n",
        "the log's code": "\n" + rd("decklog.js") + "\n/* ---------------- boot ---------------- */\n",
    }
    out = src
    for name, old, new, want in EDITS:
        n = out.count(old)
        if n != want:
            raise SystemExit(f"ABORT — '{name}': anchor matched {n} times, need {want}")
        if new is None:
            if name == "log styles":
                new = fills[name] + old
            elif name == "log button in the header":
                new = fills[name] + old
            elif name == "log panel over the three columns":
                new = "    </section>\n" + rd("decklog.html") + "  </div>\n\n  <!-- TRANSPORT -->"
            else:
                new = fills[name]
        out = out.replace(old, new, want)
        print(f"  ok  {name}")
    bad = [g for g in GUARD_ABSENT if g in out] + [g for g in GUARD_PRESENT if g not in out]
    if bad:
        raise SystemExit(f"ABORT — guard: {bad}")
    print(f"      {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB")
    if dry:
        print("dry run — nothing written")
        return
    open(path, "w", encoding="utf-8", newline="").write(out)
    print("written dist/deck.html")


if __name__ == "__main__":
    main()
