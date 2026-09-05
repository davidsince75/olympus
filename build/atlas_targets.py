# -*- coding: utf-8 -*-
"""Hang the remaining explainers on the chrome that already carries their words."""
import io, sys
SRC = "/home/claude/olympus/src/atlas.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# --- live layer toggles
once(u'''const LIVE_LAYERS = [
  {id:"aurora", nm:"Aurora",  col:"#5FE3C0"},
  {id:"drift",  nm:"Drift",   col:"#7FE3F5"},
  {id:"sar",    nm:"SAR",     col:"#C89BE8"},
];''',
     u'''const LIVE_LAYERS = [
  {id:"aurora", nm:"Aurora",  col:"#5FE3C0", ex:"ovation"},
  {id:"drift",  nm:"Drift",   col:"#7FE3F5", ex:"drift_cmcc"},
  {id:"sar",    nm:"SAR",     col:"#C89BE8", ex:"sar_footprints"},
];''', "LIVE_LAYERS ex")
once(u'''  $("#liveBar").innerHTML = LIVE_LAYERS.map(l=>
    `<button data-live="${l.id}" aria-pressed="true" style="color:${l.col}">${esc(l.nm)}</button>`).join("");''',
     u'''  $("#liveBar").innerHTML = LIVE_LAYERS.map(l=>
    `<button data-live="${l.id}" aria-pressed="true" style="color:${l.col}" data-ex="${l.ex}">${esc(l.nm)}</button>`).join("");''',
     "liveBar ex")

# --- base imagery
once(u'''  const bases = [{k:"relief",nm:"Relief"},{k:"today",nm:"Today"},{k:"none",nm:"None"}]
      .filter(b=> b.k==="none" || baseLayer(b.k));
  $("#baseBar").innerHTML = bases.map(b=>
    `<button data-base="${b.k}" aria-pressed="${b.k===st.base}">${esc(b.nm)}</button>`).join("");''',
     u'''  const bases = [{k:"relief",nm:"Relief",ex:"bluemarble"},{k:"today",nm:"Today",ex:"truecolor"},
                 {k:"none",nm:"None",ex:"projection"}]
      .filter(b=> b.k==="none" || baseLayer(b.k));
  $("#baseBar").innerHTML = bases.map(b=>
    `<button data-base="${b.k}" aria-pressed="${b.k===st.base}" data-ex="${b.ex}">${esc(b.nm)}</button>`).join("");''',
     "baseBar ex")

# --- network edge toggles: the Joint button means something the others do not
once(u'''  $("#netBar").innerHTML = Object.keys(EDGE_C).map(k=>
    `<button data-net="${k}" aria-pressed="true" style="color:${EDGE_C[k]}">${EDGE_N[k]}</button>`).join("");''',
     u'''  $("#netBar").innerHTML = Object.keys(EDGE_C).map(k=>
    `<button data-net="${k}" aria-pressed="true" style="color:${EDGE_C[k]}" data-ex="${k==="joint"?"joint":"edges"}">${EDGE_N[k]}</button>`).join("");''',
     "netBar ex")

# --- the freshness panel: one target per source, as the deck's feed strip has
once(u'''  const add = (k, v, iso, mode) => rows.push(
    `<div class="row"><span class="k">${k}</span><span class="v">${esc(v)}</span>
     <span class="age">${iso ? esc(ageOf(iso) || "—") : ""}</span></div>`);
  if(LIVE.aurora) add("AURORA", "OVATION " + (LIVE.aurora.mode||""), LIVE.aurora.observed);
  if(LIVE.kp)     add("KP",     "index " + LIVE.kp.latest,           LIVE.kp.time);''',
     u'''  const add = (k, v, iso, ex) => rows.push(
    `<div class="row"${ex?` data-ex="${ex}"`:""}><span class="k">${k}</span><span class="v">${esc(v)}</span>
     <span class="age">${iso ? esc(ageOf(iso) || "—") : ""}</span></div>`);
  if(LIVE.aurora) add("AURORA", "OVATION " + (LIVE.aurora.mode||""), LIVE.aurora.observed, "ovation");
  if(LIVE.kp)     add("KP",     "index " + LIVE.kp.latest,           LIVE.kp.time,         "kp_index");''',
     "fresh rows ex 1")
once(u'''                                (LIVE.drift.sh||LIVE.drift.nh||{}).t1);
  if(LIVE.sar)    add("SAR",    LIVE.sar.n + " passes",              (LIVE.sar.items[0]||{}).start);''',
     u'''                                (LIVE.drift.sh||LIVE.drift.nh||{}).t1, "drift_cmcc");
  if(LIVE.sar)    add("SAR",    LIVE.sar.n + " passes",              (LIVE.sar.items[0]||{}).start, "sar_s1");''',
     "fresh rows ex 2")
once(u'''  if(bl)                      add("IMAGERY", bl.day ? "MODIS " + bl.day : "Blue Marble",
                                             bl.day ? bl.day + "T12:00:00Z" : null);
  else if(st.base === "none") add("IMAGERY", "off", null);''',
     u'''  if(bl)                      add("IMAGERY", bl.day ? "MODIS " + bl.day : "Blue Marble",
                                             bl.day ? bl.day + "T12:00:00Z" : null,
                                             bl.day ? "truecolor" : "bluemarble");
  else if(st.base === "none") add("IMAGERY", "off", null, "projection");''',
     "fresh rows ex 3")
once(u'''    `<div class="hd"><span class="pulse"></span>${LIVE_FETCH ? "Live · refreshing" : "Observed"} · age now</div>` +''',
     u'''    `<div class="hd"><span class="pulse"></span><span data-ex="live_transport">${LIVE_FETCH ? "Live · refreshing" : "Observed"}</span> · <span data-ex="age_stamp">age now</span></div>` +''',
     "fresh header split")
# the container target would shadow every child
once(u'<div class="fresh" id="fresh" data-ex="age_stamp"></div>', u'<div class="fresh" id="fresh"></div>', "unshadow fresh")

# --- detail panel headings carry the register's own rules
once(u'`<div class="sec"><h4>Programmes hosted</h4>', u'`<div class="sec"><h4 data-ex="facility_vs_programme">Programmes hosted</h4>', "programmes heading")
once(u'`<div class="sec"><h4>Changed since the master list</h4>', u'`<div class="sec"><h4 data-ex="comnap">Changed since the master list</h4>', "changed heading")
once(u'`<div class="sec"><h4>Shared with</h4>', u'`<div class="sec"><h4 data-ex="joint">Shared with</h4>', "shared heading")
once(u'  <div class="sec" style="border-bottom:0">\n    <h4>Provenance</h4>', u'  <div class="sec" style="border-bottom:0">\n    <h4 data-ex="positions">Provenance</h4>', "provenance heading")
once(u'<div class="sec" style="border-bottom:0"><h4>Provenance</h4>', u'<div class="sec" style="border-bottom:0"><h4 data-ex="positions">Provenance</h4>', "provenance heading 2")
once(u'    <h4>Public presence</h4>', u'    <h4 data-ex="openness">Public presence</h4>', "presence heading")
once(u'    <h4>Operators, by facilities held</h4>', u'    <h4 data-ex="operators">Operators, by facilities held</h4>', "operators heading")
once(u'    <h4>Reading this map</h4>', u'    <h4 data-ex="edges">Reading this map</h4>', "reading heading")

# --- the Arctic half of the register was compiled, not inherited
once(u'<button data-mode="N" aria-pressed="false">Arctic</button>',
     u'<button data-mode="N" aria-pressed="false" data-ex="arctic_register">Arctic</button>', "arctic mode")
once(u'<button data-mode="S" aria-pressed="true">Antarctic</button>',
     u'<button data-mode="S" aria-pressed="true" data-ex="comnap">Antarctic</button>', "antarctic mode")

io.open(SRC, "w", encoding="utf8").write(s)
print("written")
