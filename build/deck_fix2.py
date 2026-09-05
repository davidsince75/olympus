# -*- coding: utf-8 -*-
"""Close the gaps the probe found: two globe hotspots that pointed at nothing,
and three new entries with nowhere to hover from."""
import io, sys
SRC = "/home/claude/olympus/src/deck.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# 1. the globe draws OSNAP as two arrays with ids osnap_w and osnap_e; the
#    explainer only had 'osnap', so both hotspots resolved to nothing.
once(u'''osnap:{k:"ins",t:"OSNAP",
 b:"A second array further north, in two legs: OSNAP West across the mouth of the Labrador Sea, OSNAP East from Greenland to Scotland. Between 2014 and 2020 it measured a mean overturning of <b>16.7 ± 0.6 Sv</b> — and found that 16.3 Sv of it happens east of Greenland, not in the Labrador Sea.",
 p:"Comm. Earth & Environment (2023), 71 months, Aug 2014 – Jun 2020."},''',
     u'''osnap_e:{k:"ins",t:"OSNAP East",
 b:"Greenland to Scotland, and the leg that carries almost all of it: <b>16.3 ± 0.6 Sv</b> of the 16.7 Sv subpolar overturning. Together with OSNAP West it forms the second continuously measured overturning line in the ocean, north of RAPID.",
 p:"Comm. Earth & Environment (2023), 71 months, Aug 2014 – Jun 2020. o-snap.org."},
osnap_w:{k:"ins",t:"OSNAP West",
 b:"Across the mouth of the Labrador Sea — the section that was expected to carry the overturning and does not. It measures <b>3.0 ± 0.5 Sv</b> against 16.3 to the east. The array was built to watch the textbook site of deep convection and its main result was that the textbook was pointing at the wrong sea.",
 p:"Comm. Earth & Environment (2023), 71 months, Aug 2014 – Jun 2020. o-snap.org."},''',
     "osnap -> osnap_e + osnap_w")

# 2. the imagery date is the honest place to say the satellite is ageing
once(u'''              <span data-ex="polar_night" style="color:var(--ink4);letter-spacing:.04em">imagery</span>''',
     u'''              <span data-ex="polar_night" style="color:var(--ink4);letter-spacing:.04em">imagery</span>
              <span id="imgDay" data-ex="terra_drift" style="color:var(--ink3);letter-spacing:.04em"></span>''',
     "imagery day span -> terra_drift")
once(u'''    st.baseImg = b.dataset.img;''',
     u'''    st.baseImg = b.dataset.img;
    { const L = deckBaseLayer(); $("#imgDay").textContent = (L && L.day) ? L.day : "static composite"; }''',
     "imagery day text on click")
once(u'''  $$("#baseBar button").forEach(b=>b.addEventListener("click",()=>{''',
     u'''  { const L0 = deckBaseLayer(); const el=$("#imgDay"); if(el) el.textContent = (L0 && L0.day) ? L0.day : "static composite"; }
  $$("#baseBar button").forEach(b=>b.addEventListener("click",()=>{''',
     "imagery day text at load")

# 3. the provenance box is where 'live' has to be defined honestly
once(u'''        <span class="prov" style="margin:8px 4px 0 0"><span class="tag live">LIVE</span> streamed</span>''',
     u'''        <span class="prov" style="margin:8px 4px 0 0" data-ex="live_transport"><span class="tag live">LIVE</span> streamed</span>''',
     "LIVE chip -> live_transport")

# 4. the drift field is the layer that connects the ice map to the AMOC gauge
once(u'''the auroral oval, the 48-hour drift field and the radar footprints''',
     u'''the auroral oval, the <b data-ex="drift_pump">48-hour drift field</b> and the radar footprints''',
     "note drift -> drift_pump")

io.open(SRC, "w", encoding="utf8").write(s)
print("written")
