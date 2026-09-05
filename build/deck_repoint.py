# -*- coding: utf-8 -*-
"""Repoint the deck's hover targets, surface the imagery and drift controls,
and correct the two places that still call Sentinel-1 placeholder geometry."""
import io, sys

SRC = "/home/claude/olympus/src/deck.html"
s = io.open(SRC, encoding="utf8").read()

def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# ------------------------------------------------------------ 1. layer stack
once(u'{id:"sat",  nm:"Satellite imagery", src:"NASA GIBS · reprojected at build", on:true,  ex:"passive_mw"},',
     u'{id:"sat",  nm:"Satellite imagery", src:"NASA GIBS · reprojected at build", on:true,  ex:"reprojection"},',
     "layer sat -> reprojection")
once(u'{id:"sar1", nm:"SAR acquisitions · last 18 h", src:"Copernicus CDSE · Sentinel-1 catalogue", on:true, ex:"sensors"},',
     u'{id:"sar1", nm:"SAR acquisitions · last 18 h", src:"Copernicus CDSE · Sentinel-1 catalogue", on:true, ex:"sar_footprints"},',
     "layer sar1 -> sar_footprints")
once(u'{id:"aur",  nm:"Auroral oval", src:"NOAA SWPC OVATION · model", on:true, ex:"sensors"},',
     u'{id:"aur",  nm:"Auroral oval", src:"NOAA SWPC OVATION · model", on:true, ex:"ovation"},',
     "layer aur -> ovation")
once(u'{id:"drift",nm:"Sea-ice drift · 48 h", src:"EUMETSAT OSI SAF OSI-405", on:true, ex:"passive_mw"},',
     u'{id:"drift",nm:"Sea-ice drift · 48 h", src:"EUMETSAT OSI SAF OSI-405", on:true, ex:"drift_cmcc"},',
     "layer drift -> drift_cmcc")
once(u'{id:"grat", nm:"Graticule & parallels", src:"generated · 15° / 30°", on:true},',
     u'{id:"grat", nm:"Graticule & parallels", src:"generated · 15° / 30°", on:true, ex:"graticule"},',
     "layer grat -> graticule")
once(u'{id:"stn",  nm:"Station network", src:"COMNAP · SCAR master list", on:true}',
     u'{id:"stn",  nm:"Station network", src:"COMNAP · SCAR master list", on:true, ex:"stn_deck"}',
     "layer stn -> stn_deck")

# ------------------------------------------------------------ 2. feed strip
once(u'if(A.sar)    F.push(["Sentinel-1 · CDSE", liveAge((A.sar.items[0]||{}).start), "live","sensors"]);',
     u'if(A.sar)    F.push(["Sentinel-1 · CDSE", liveAge((A.sar.items[0]||{}).start), "live","sar_s1"]);',
     "feed sar -> sar_s1")
once(u'if(A.drift)  F.push(["OSI SAF drift",     liveAge((A.drift.sh||A.drift.nh||{}).t1), "live","passive_mw"]);',
     u'if(A.drift)  F.push(["OSI SAF drift",     liveAge((A.drift.sh||A.drift.nh||{}).t1), "live","drift_cmcc"]);',
     "feed drift -> drift_cmcc")
once(u'if(A.aurora) F.push(["SWPC OVATION",      liveAge(A.aurora.observed), "warn","sensors"]);',
     u'if(A.aurora) F.push(["SWPC OVATION",      liveAge(A.aurora.observed), "warn","ovation"]);',
     "feed aurora -> ovation")
once(u'if(A.kp)     F.push(["Kp " + A.kp.latest, liveAge(A.kp.time), "live","sensors"]);',
     u'if(A.kp)     F.push(["Kp " + A.kp.latest, liveAge(A.kp.time), "live","kp_index"]);',
     "feed kp -> kp_index")
once(u'if(bl)       F.push(["GIBS imagery", bl.day || "static", "live","sensors"]);',
     u'if(bl)       F.push(["GIBS imagery", bl.day || "static", "live", bl.key === "today" ? "truecolor" : "bluemarble"]);',
     "feed gibs -> truecolor/bluemarble")
# the strip itself explains why the ages differ
once(u'  $("#feeds").innerHTML = F.map(([n,l,s,ex])=>',
     u'  $("#feeds").setAttribute("data-ex","age_stamp");\n  $("#feeds").innerHTML = F.map(([n,l,s,ex])=>',
     "feed strip -> age_stamp")

# ------------------------------------------------------------ 3. stale claims
once(u'sim_layer:{k:"ins",t:"This layer is illustrative",\n b:"Sentinel-1 footprints, ITS_LIVE velocity streaklines, Argo float positions and the satellite ground track on this deck are <b>drawn, not measured</b>. They show what the finished instrument would carry. They are marked SIM everywhere they appear, and no number on the deck is derived from them.",\n p:"Placeholder geometry. The measured layers are sea ice and AMOC."},',
     u'sim_layer:{k:"ins",t:"This layer is illustrative",\n b:"ITS_LIVE velocity streaklines, Argo float positions, the satellite ground track and the anomaly stream are <b>drawn, not measured</b>. They show what the finished instrument would carry. They are marked SIM everywhere they appear, and no number on the deck is derived from them. Sentinel-1 used to be on this list and is not any more: those footprints are now real acquisitions, which is the only kind of progress this list is meant to record.",\n p:"Placeholder geometry. Measured: sea ice, AMOC, ice drift, SAR acquisitions and the imagery."},',
     "sim_layer text")

once(u'The <b>thermohaline conveyor on the globe is a schematic</b> — there is no measured global map of this circulation. Its path is drawn after the classic Broecker figure; only its speed is real, scaled by the observed monthly RAPID value. The deep-water formation sites and the RAPID and OSNAP lines are at their true locations. Sentinel-1, ITS_LIVE, Argo, the ground track and the anomaly stream remain illustrative and are marked <span class="prov" style="padding:0 4px"><span class="tag sim">SIM</span></span> wherever they appear.',
     u'The <b>thermohaline conveyor on the globe is a schematic</b> — there is no measured global map of this circulation. Its path is drawn after the classic Broecker figure; only its speed is real, scaled by the observed monthly RAPID value. The deep-water formation sites and the RAPID and OSNAP lines are at their true locations. ITS_LIVE, Argo, the ground track and the anomaly stream remain illustrative and are marked <span class="prov" style="padding:0 4px"><span class="tag sim">SIM</span></span> wherever they appear.',
     "footer note SIM list")

once(u'Hover anything to find out what it is.</p>',
     u'The living layers &mdash; the imagery, the auroral oval, the 48-hour drift field and the radar footprints &mdash; are <b>baked at build time and stamped with their own observation age</b>, because a published page cannot reach the network. Turn <b>LEARN</b> on and hover anything to find out what it is.</p>',
     "footer note living layer")

# ------------------------------------------------------------ 4. surface switcher
once(u'<nav class="xnav" aria-label="Olympus surfaces">',
     u'<nav class="xnav" aria-label="Olympus surfaces" data-ex="surfaces">',
     "xnav -> surfaces")

# ------------------------------------------------------------ 5. controls that reach the new data
once(u'''            <div class="gctl" id="globeCtl" hidden>''',
     u'''            <div class="gctl" id="baseBar" role="group" aria-label="Base imagery">
              <button data-img="relief" aria-pressed="true" data-ex="bluemarble">Relief</button>
              <button data-img="today"  aria-pressed="false" data-ex="truecolor">Today</button>
              <span data-ex="polar_night" style="color:var(--ink4);letter-spacing:.04em">imagery</span>
            </div>
            <div class="gctl" id="driftBar" role="group" aria-label="Drift vector length">
              <button data-x="1"  aria-pressed="true"  data-ex="drift_true_length">&times;1</button>
              <button data-x="5"  aria-pressed="false" data-ex="drift_true_length">&times;5</button>
              <button data-x="15" aria-pressed="false" data-ex="drift_true_length">&times;15</button>
              <span id="driftNote" style="color:var(--warn);letter-spacing:.04em"></span>
            </div>
            <div class="gctl" id="globeCtl" hidden>''',
     "insert baseBar + driftBar markup")

once(u'''$$("#globeCtl button").forEach''',
     u'''  $$("#baseBar button").forEach(b=>b.addEventListener("click",()=>{
    st.baseImg = b.dataset.img;
    $$("#baseBar button").forEach(o=>o.setAttribute("aria-pressed", String(o===b)));
    feeds(); paintAll();
  }));
  $$("#driftBar button").forEach(b=>b.addEventListener("click",()=>{
    st.driftX = +b.dataset.x;
    $$("#driftBar button").forEach(o=>o.setAttribute("aria-pressed", String(o===b)));
    // an exaggerated vector is only honest if it says so on screen
    $("#driftNote").textContent = st.driftX>1 ? ("drift \\u00d7"+st.driftX+" \\u2014 exaggerated") : "";
    paintAll();
  }));
$$("#globeCtl button").forEach''',
     "wire baseBar + driftBar")

# hide a control whose layer is off
once(u'''  $("#laycount").textContent=LAYERS.filter(l=>st.lay[l.id]).length+"/"+LAYERS.length;''',
     u'''  $("#laycount").textContent=LAYERS.filter(l=>st.lay[l.id]).length+"/"+LAYERS.length;
  { const bb=$("#baseBar"), db=$("#driftBar");
    if(bb) bb.hidden = !st.lay.sat;
    if(db) db.hidden = !st.lay.drift; }''',
     "hide bars with their layers")

# pressed state for the new bars
once(u'.gctl button:hover{color:var(--ice);border-color:var(--ice)}',
     u'.gctl button:hover{color:var(--ice);border-color:var(--ice)}\n.gctl button[aria-pressed="true"]{background:var(--panel3);color:var(--ice);border-color:var(--s1)}',
     "gctl pressed state")

io.open(SRC, "w", encoding="utf8").write(s)
print("written")
