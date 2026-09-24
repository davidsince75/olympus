#!/usr/bin/env python3
"""
Olympus — fixes from the audit of 24 September 2026.

Deck
  1. The invented contributor goes. "Ines Halvorsen, Glaciologist, Halley VI"
     was a made-up person with a made-up quote about a real crack at a real
     station, beside three buttons that did nothing. On a surface whose claim is
     that provenance is the product, it was the most damaging thing on the page.
     The Channel now says plainly that it is not open.
  2. Freshness is computed, not assigned. Every feed dot was hard-coded green,
     including two archives and four layers that were twenty days old. Dots now
     follow observation age: green under 48 h, amber under a week, grey after
     that; archives get their own colour. Live layer lines carry "as of <date>".
  3. Sentences that were not true: "Uncertainty is drawn, not hidden" (it is
     not drawn yet); "SAR acquisitions · last 18 h" (it was an 18 h window three
     weeks ago); "Today" on an image whose date is printed beside it; "the site
     build fetches" (no site build is published).
  4. The physics. The Temp explainer and the footer called the surface
     Gulf Stream / Labrador contrast "the engine", moved by heating, cooling and
     salt. The drifter field is mostly wind-driven; the overturning is the smaller
     net flow underneath, measured at RAPID. The counter-phase entry said the pump
     "never fully stops"; it says what is true instead.
  5. A stranger's first view. 13 of 14 layers were on at open, including four
     SIM layers and a twenty-day-old aurora washing green over the continent. The
     deck now opens on what is measured: ice, currents, fronts, shelves,
     imagery, stations. Everything else is one click away and unchanged.
  6. Phones. At 390 px the document was 507 px wide and the HUD covered the map.

Atlas
  7. Phones: header wraps, map first, HUD reduced to what a finger can use.
  8. The freshness panel's green pulse follows the age of what it lists.
  9. Living layers off at open, as on the deck — this surface is about stations.

Named Ice
 10. The aurora hero drew ~1,200 separately blur-filtered fills per frame; on
     the build host that was one 23-second task per frame at 1440 px. It now
     draws the curtains once at 1/6 resolution, blurs once, and scales up.
 11. The Google Fonts stylesheet no longer blocks the page.

Exact-string anchors, applied in order to a working copy; each must match the
stated number of times or nothing is written. Guards refuse to write a file in
which a retired sentence survives.

  python build/patch_audit.py [--dry]            # patches dist/{deck,atlas,named_ice}.html
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# --------------------------------------------------------------------------- deck
DECK = [
("the invented contributor",
'''      <div class="dispatch dsp">
        <div class="dsp-top">
          <div class="avatar">IH</div>
          <div>
            <div class="who">Ines Halvorsen</div>
            <div class="role">Glaciologist · Halley VI · Brunt Ice Shelf</div>
          </div>
        </div>
        <q>The Halloween Crack moved further this week than in the whole of last season. We are watching the shelf decide something.</q>
        <div class="acts">
          <button class="pri">Open channel</button>
          <button>Field log</button>
          <button>Follow</button>
        </div>
        <div style="margin-top:10px"><span class="prov"><b>Placeholder contributor profile</b><span class="tag sim">SIM</span></span></div>
      </div>''',
'''      <div class="dispatch dsp" data-ex="channel_empty">
        <div class="dsp-top">
          <div class="avatar" aria-hidden="true">&middot;</div>
          <div>
            <div class="who">The Channel</div>
            <div class="role">No one on the ice writes here yet</div>
          </div>
        </div>
        <p class="dsp-note">When a scientist does, their name, their station and the date will be on it, stamped like every other value on this deck. Until then the space stays empty rather than holding an invented voice.</p>
        <div style="margin-top:10px"><span class="prov"><b>Not open</b><span class="tag wait">NONE</span></span></div>
      </div>''', 1),

("style for the empty Channel",
'.dsp .acts button.pri{',
'.dsp .dsp-note{font-size:12px;line-height:1.55;color:var(--ink3);margin:10px 0 0}\n.dsp .acts button.pri{', 1),

("explainer for the empty Channel",
'sim_layer:{k:"ins",t:"This layer is illustrative",',
'''channel_empty:{k:"ins",t:"Why this space is empty",
 b:"This is where people on the ice will speak — a glaciologist at a station, a technician on a drifting platform — under their own names, with their station and the date. <b>Nobody does yet</b>, so it says so. An earlier version of this deck filled it with an invented scientist and an invented quote about a real crack at a real station, marked as a placeholder in small type. That is exactly what this deck exists not to do, and it is gone.",
 p:"No contributor. Nothing on this panel is simulated."},
sim_layer:{k:"ins",t:"This layer is illustrative",''', 1),

("provenance legend: nothing here is streamed",
'<span class="prov" style="margin:8px 4px 0 0" data-ex="live_transport"><span class="tag live">LIVE</span> streamed</span>',
'<span class="prov" style="margin:8px 4px 0 0" data-ex="live_transport"><span class="tag live">AS OF</span> baked, dated</span>', 1),

("uncertainty is not drawn yet",
'<div style="margin-top:9px">Nothing renders without one. Uncertainty is drawn, not hidden.</div>',
'<div style="margin-top:9px">Nothing renders without one. Uncertainty is stated beside the values that carry it; drawing it on the map is not built yet.</div>', 1),

("feed dots follow observation age",
'''function feeds(){
  const A = (typeof LIVE !== "undefined" && LIVE) ? LIVE : {};
  const F = [["OSI SAF · monthly","1978→2026","live","record_switch"]];
  if(A.sar)    F.push(["Sentinel-1 · CDSE", liveAge((A.sar.items[0]||{}).start), "live","sar_s1"]);
  if(A.drift)  F.push(["OSI SAF drift",     liveAge((A.drift.sh||A.drift.nh||{}).t1), "live","drift_cmcc"]);
  if(A.aurora) F.push(["SWPC OVATION",      liveAge(A.aurora.observed), "warn","ovation"]);
  if(A.kp)     F.push(["Kp " + A.kp.latest, liveAge(A.kp.time), "live","kp_index"]);
  const bl = (typeof deckBaseLayer === "function") ? deckBaseLayer() : null;
  if(bl)       F.push(["GIBS imagery", bl.time || "static", "live", bl.key === "today" ? "truecolor" : "bluemarble"]);
  F.push(["RAPID 26.5°N","2004–2024","live","rapid"]);''',
'''function feeds(){
  const A = (typeof LIVE !== "undefined" && LIVE) ? LIVE : {};
  // A dot is a claim about freshness, so it is computed from the observation
  // time and never assigned: green under 48 h, amber under a week, grey after
  // that. An archive is not live at any age and gets its own colour.
  const F = [["OSI SAF · monthly","1978→2026","arch","record_switch"]];
  const sT = (A.sar ? (A.sar.items[0]||{}).start : null), dT = (A.drift ? (A.drift.sh||A.drift.nh||{}).t1 : null);
  if(A.sar)    F.push(["Sentinel-1 · CDSE", liveAge(sT), liveFresh(sT),"sar_s1"]);
  if(A.drift)  F.push(["OSI SAF drift",     liveAge(dT), liveFresh(dT),"drift_cmcc"]);
  if(A.aurora) F.push(["SWPC OVATION",      liveAge(A.aurora.observed), liveFresh(A.aurora.observed),"ovation"]);
  if(A.kp)     F.push(["Kp " + A.kp.latest, liveAge(A.kp.time), liveFresh(A.kp.time),"kp_index"]);
  const bl = (typeof deckBaseLayer === "function") ? deckBaseLayer() : null;
  if(bl)       F.push(["GIBS imagery", bl.time || "static", bl.time ? liveFresh(String(bl.time).slice(0,10)+"T12:00:00Z") : "arch", bl.key === "today" ? "truecolor" : "bluemarble"]);
  F.push(["RAPID 26.5°N","2004–2024","arch","rapid"]);''', 1),

("dot colours for archive and stale",
'.dot.warn{',
'.dot.arch{background:var(--s1);box-shadow:0 0 0 3px rgba(15,165,190,.14)}\n.dot.stale{background:var(--ink4);box-shadow:none}\n.dot.warn{', 1),

("freshness helpers",
'''  return Math.round(m/1440)+" d";
}''',
'''  return Math.round(m/1440)+" d";
}
function liveFresh(iso){
  const t = Date.parse(iso||""); if(!isFinite(t)) return "stale";
  const h = (Date.now()-t)/3.6e6;
  return h < 48 ? "live" : h < 168 ? "warn" : "stale";
}
function liveAsOf(k){
  const A = (typeof LIVE !== "undefined" && LIVE) ? LIVE : null;
  if(!k || !A || !A[k]) return "";
  const t = k==="sar" ? (A.sar.items[0]||{}).start
          : k==="drift" ? (A.drift.sh||A.drift.nh||{}).t1
          : (A[k].observed || A[k].time);
  return t ? " · as of " + String(t).slice(0,10) : "";
}''', 1),

("layer lines carry their date",
'<div class="src">${l.src}</div></div></div>`',
'<div class="src">${l.src}${liveAsOf(l.live)}</div></div></div>`', 1),

("open on what is measured: deep limbs",
'''{id:"deep", nm:"Deep & bottom-water limbs", src:"schematic path on real gateways · RAPID-driven speed", on:true, sim:true,''',
'''{id:"deep", nm:"Deep & bottom-water limbs", src:"schematic path on real gateways · RAPID-driven speed", on:false, sim:true,''', 1),
("open on what is measured: ice velocity",
'''{id:"vel",  nm:"Ice-sheet surface velocity", src:"placeholder geometry", on:true,''',
'''{id:"vel",  nm:"Ice-sheet surface velocity", src:"placeholder geometry", on:false,''', 1),
("SAR: a window, dated, off at open",
'''{id:"sar1", nm:"SAR acquisitions · last 18 h", src:"Copernicus CDSE · Sentinel-1 catalogue", on:true,''',
'''{id:"sar1", nm:"SAR acquisitions · 18 h window", src:"Copernicus CDSE · Sentinel-1 catalogue", live:"sar", on:false,''', 1),
("aurora dated, off at open",
'''{id:"aur",  nm:"Auroral oval", src:"NOAA SWPC OVATION · model · one frame, turned ×3600", on:true,''',
'''{id:"aur",  nm:"Auroral oval", src:"NOAA SWPC OVATION · model · one frame, turned ×3600", live:"aurora", on:false,''', 1),
("drift dated, off at open",
'''{id:"drift",nm:"Sea-ice drift · 48 h", src:"EUMETSAT OSI SAF OSI-405", on:true,''',
'''{id:"drift",nm:"Sea-ice drift · 48 h", src:"EUMETSAT OSI SAF OSI-405", live:"drift", on:false,''', 1),
("Argo placeholder off at open",
'''{id:"argo", nm:"Argo profiling floats", src:"placeholder geometry", on:true,''',
'''{id:"argo", nm:"Argo profiling floats", src:"placeholder geometry", on:false,''', 1),

("imagery button says what it is",
'<button data-img="today"  aria-pressed="false" data-ex="truecolor">Today</button>',
'<button data-img="today"  aria-pressed="false" data-ex="truecolor">Latest</button>', 1),

("SAR explainer: a dated window",
'Each outline is <b>where the radar was pointed</b> in the last 18 hours, taken from',
'Each outline is <b>where the radar was pointed</b> during an 18-hour window before this page was built — the date is on the layer line and the age in the header — taken from', 1),
("SAR provenance line",
'p:"Copernicus Data Space Ecosystem OData catalogue, both polar caps, 18-hour window."',
'p:"Copernicus Data Space Ecosystem OData catalogue, swaths centred poleward of 60°, one outline per acquisition, 18-hour window. ingest/build_events.py."', 1),

("what live means, without a site that does not exist",
'''The same page built for a web host sets a flag and refreshes the fast layers from the identical endpoints in the browser. One data model, two transports; the honest word for this copy is not <i>live</i> but <i>as of</i>.",
 p:"ingest/build_events.py writes both. The artifact build carries the snapshot; the site build fetches."''',
'''Served from an ordinary web host, the same page is designed to refresh the fast layers from the identical endpoints in the browser; that build is not published yet. The honest word for this copy is not <i>live</i> but <i>as of</i> — and the dot beside each feed turns from green to amber to grey as its observation ages, so the header cannot go on calling a three-week-old frame live.",
 p:"ingest/build_events.py fetches the payload; ingest/inject_live.py puts it into a surface. Dot colour is computed from observation time: under 48 h green, under 7 days amber, older grey."''', 1),

("the physics: what the Temp colouring shows",
''' ocean_temp:{k:"num",t:"The thermo in thermohaline",
 b:"Colour the filaments by <b>Temp</b> and the conveyor stops being a diagram. The Gulf Stream leaves the tropics at about <b>24 °C</b> and runs northeast in orange; the Labrador Current comes back past it at <b>3 °C</b> in blue; the Circumpolar Current is a cold band all the way round. That contrast is the engine — water is moved by being heated and cooled and by gaining and losing salt, and until this ramp existed every filament on this map was the same white whichever way it was carrying heat. The temperature is measured by the thermistor on the same drifters that measured the velocity.",
 p:"''',
''' ocean_temp:{k:"num",t:"Where the heat goes",
 b:"Colour the filaments by <b>Temp</b> and you can see which way the heat is carried. The Gulf Stream leaves the tropics at about <b>24 °C</b> and runs northeast in orange; the Labrador Current comes back past it at <b>3 °C</b> in blue; the Circumpolar Current is a cold band all the way round. Read it carefully: <b>most of what moves the surface water here is the wind</b>, not heating and cooling. The Gulf Stream is first the western edge of a wind-driven gyre, and carries several times more water than the overturning does. The thermohaline part is the smaller, slower net flow left once the gyres are taken out — warm water that does not come back at the surface because it has been cooled and salted enough to sink. That is why it is measured across a whole basin, at RAPID, and drawn as its own layer rather than read off these filaments. The temperature is measured by the thermistor on the same drifters that measured the velocity.",
 p:"On wind- versus buoyancy-driven circulation: Wunsch (2002), What is the thermohaline circulation?, Science 298, 1179. ''', 1),

("the footer: same correction",
'Switch the colouring to <b>Temp</b> and the conveyor stops being a diagram — the Gulf Stream runs north at 24 °C in orange, the Labrador Current comes back past it at 3 °C in blue, and the engine is visible.',
'Switch the colouring to <b>Temp</b> to see which way the heat goes — the Gulf Stream runs north at 24 °C in orange, the Labrador Current comes back past it at 3 °C in blue. Most of that surface motion is driven by the wind; the overturning is the smaller net flow beneath it, which is why it is measured at RAPID and drawn as its own layer.', 1),

("counter-phase: what is true",
'One pole is always freezing while the other melts, so the pump never fully stops — it alternates ends.',
'One pole is always freezing while the other melts, so the season of ice growth — and the brine it makes — alternates between the two ends of the Earth.', 1),

("phones",
'@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}',
'''/* Phones — audited 24 Sep 2026 at 390 px: the document was 507 px wide, the
   clock was cut off and the HUD covered most of the map. On a phone the map is
   the page: readouts that need a cursor and bars that duplicate the layer stack
   step aside, and the header wraps instead of pushing the page sideways. */
.feeds{min-width:0}
.body>.col{min-width:0}
.lay .src{overflow-wrap:anywhere}
@media (max-width:720px){
  .hdr{flex-wrap:wrap;height:auto}
  .brand{flex:1 1 auto;border-right:0;padding:8px 12px}
  .hdr .xnav{margin:6px 10px 6px auto}
  .feeds,.clock{display:none}
  .mapwrap{height:min(112vw,560px);max-height:none}
  .hud .tr>*:not(#conc),#hemiNote,#proj,#flowBar,#driftBar,#baseBar,#globeCtl,.hud .bl .mapkey,#pass{display:none!important}
  .hud .tl{top:8px;left:8px}.hud .tr{top:44px;right:8px}
  .hud .bl{bottom:8px;left:8px}.hud .br{bottom:8px;right:8px}
  .legend{padding:5px 7px}.legend .ramp,.legend .rl{width:92px}
  .modebar button{padding:4px 7px}
  .hero .val{font-size:34px}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}''', 1),
]

DECK_GUARD = ["Ines Halvorsen", "Uncertainty is drawn, not hidden", "last 18 h", "in the last 18 hours",
              "That contrast is the engine", "the engine is visible", "pump never fully stops",
              "the site build fetches", ">Today</button>", "Placeholder contributor profile"]

# --------------------------------------------------------------------------- atlas
ATLAS = [
("phones",
'''@media (max-width:900px){
  .shell{height:auto;min-height:0}''',
'''/* Phones — audited 24 Sep 2026 at 390 px: the header pushed the document to
   730 px wide, the station list came before the map and the HUD covered it. */
@media (max-width:900px){
  .hdr{flex-wrap:wrap;height:auto;padding:8px 12px;gap:8px 12px}
  .hstat{width:100%;margin-left:0;justify-content:space-between;gap:8px}
  .body .col:nth-child(2){order:-1}
}
@media (max-width:720px){
  #netBar,#liveBar,#baseBar,#driftX,.fresh,.hud .bl{display:none!important}
  .hud .tr{display:none!important}
}
@media (max-width:900px){
  .shell{height:auto;min-height:0}''', 1),
("the pulse follows the age",
'''`<div class="hd"><span class="pulse"></span>''',
'''`<div class="hd"><span class="pulse ${freshClass()}"></span>''', 1),
("freshness class helper",
'''/* ---- the freshness panel: every layer states its own age ---- */''',
'''/* ---- the freshness panel: every layer states its own age ----
   The pulse is a claim that something is current, so its colour follows the
   oldest observation listed: green under 48 h, amber under a week, grey and
   still after that. (Audit, 24 Sep 2026: it pulsed green over 20-day-old data.) */
function freshClass(){
  if(!LIVE) return "stale";
  const ts = [LIVE.aurora && LIVE.aurora.observed, LIVE.kp && LIVE.kp.time,
              LIVE.drift && (LIVE.drift.sh||LIVE.drift.nh||{}).t1,
              LIVE.sar && (LIVE.sar.items[0]||{}).start].filter(Boolean).map(Date.parse).filter(isFinite);
  if(!ts.length) return "stale";
  const h = (Date.now() - Math.min(...ts)) / 3.6e6;
  return h < 48 ? "" : h < 168 ? "warn" : "stale";
}''', 1),
("pulse colours",
'''@keyframes pulse{0%,100%{opacity:.25}50%{opacity:1}}''',
'''@keyframes pulse{0%,100%{opacity:.25}50%{opacity:1}}
.fresh .pulse.warn{background:var(--warn)}
.fresh .pulse.stale{background:var(--ink4);animation:none;opacity:.8}''', 1),
]
ATLAS.append(("living layers off at open — this surface is about stations",
'st.live = new Set(["aurora","drift","sar"]);',
'st.live = new Set();   // off at open; one click on the bar above the map (audit, 24 Sep 2026)', 1))
ATLAS.append(("the zoom hint names the gesture the reader has",
'$("#scaleR").textContent = "scroll to zoom · drag to pan";',
'$("#scaleR").textContent = (matchMedia("(pointer: coarse)").matches ? "pinch to zoom · drag to pan" : "scroll to zoom · drag to pan");', 1))
ATLAS_GUARD = []

# --------------------------------------------------------------------------- named ice
ICE = [
("fonts do not block the page",
'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap">',
'''<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap"></noscript>''', 1),
("offscreen buffers for the curtains",
'''  const FLAKES = [];
''',
'''  const FLAKES = [];
  /* The curtains are drawn at 1/DS resolution with no filter, blurred once,
     and scaled up. Same softness; the old path ran ~1,200 separately
     blur-filtered fills a frame, which on the audit host (24 Sep 2026) was one
     23-second task per frame at 1440 px. */
  const DS = 6;
  const cA = document.createElement("canvas"), gA = cA.getContext("2d");
  const cB = document.createElement("canvas"), gB = cB.getContext("2d");
''', 1),
("size the buffers with the canvas",
'''    g.setTransform(dpr,0,0,dpr,0,0);
    FLAKES.length = 0;''',
'''    g.setTransform(dpr,0,0,dpr,0,0);
    cA.width = cB.width = Math.max(2, Math.ceil(W/DS));
    cA.height = cB.height = Math.max(2, Math.ceil(H/DS));
    FLAKES.length = 0;''', 1),
("the curtain draws into the small buffer, unfiltered",
'''  function curtain(b, t){
    const step = Math.max(3, W/300);
    g.globalCompositeOperation = "lighter";
    g.filter = "blur(" + Math.max(9, W/120).toFixed(0) + "px)";
    const yOff = Math.sin(t*b.drift)*0.035;''',
'''  function curtain(b, t){
    const g = gA, W = cA.width, H = cA.height;
    const step = Math.max(1, W/300);
    g.globalCompositeOperation = "lighter";
    const yOff = Math.sin(t*b.drift)*0.035;''', 1),
("no per-fill filter to reset",
'''      g.fillRect(x-step, yc-hh, step*3, hh*1.55);
    }
    g.filter = "none";
    g.globalCompositeOperation = "source-over";
  }''',
'''      g.fillRect(x-step, yc-hh, step*3, hh*1.55);
    }
    g.globalCompositeOperation = "source-over";
  }''', 1),
("one blur, one scaled composite",
'''    for(const b of BANDS) curtain(b, t);
''',
'''    gA.clearRect(0,0,cA.width,cA.height);
    for(const b of BANDS) curtain(b, t);
    gB.clearRect(0,0,cB.width,cB.height);
    gB.filter = "blur(" + Math.max(1.5, W/120/DS).toFixed(1) + "px)";
    gB.drawImage(cA,0,0);
    gB.filter = "none";
    g.globalCompositeOperation = "lighter";
    g.imageSmoothingEnabled = true; g.imageSmoothingQuality = "high";
    g.drawImage(cB,0,0,W,H);
    g.globalCompositeOperation = "source-over";
''', 1),
]
ICE_GUARD = []


def apply(path, edits, guards, dry):
    src = open(path, encoding="utf-8", newline="").read()
    out = src
    for name, old, new, want in edits:
        n = out.count(old)
        if n != want:
            raise SystemExit(f"ABORT {os.path.basename(path)} — '{name}': anchor matched {n} times, need {want}")
        out = out.replace(old, new, want)
        print(f"  ok  {os.path.basename(path)}: {name}")
    bad = [g for g in guards if g in out]
    if bad:
        raise SystemExit(f"ABORT {os.path.basename(path)} — retired text survives: {bad}")
    print(f"      {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB")
    if not dry:
        open(path, "w", encoding="utf-8", newline="").write(out)


def main():
    dry = "--dry" in sys.argv
    apply(os.path.join(ROOT, "dist", "deck.html"), DECK, DECK_GUARD, dry)
    apply(os.path.join(ROOT, "dist", "atlas.html"), ATLAS, ATLAS_GUARD, dry)
    apply(os.path.join(ROOT, "dist", "named_ice.html"), ICE, ICE_GUARD, dry)
    print("dry run — nothing written" if dry else "written")


if __name__ == "__main__":
    main()
