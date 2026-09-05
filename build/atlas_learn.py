# -*- coding: utf-8 -*-
"""The Atlas had no learning layer at all. This ports the deck's explainer model
to it — same popup, same four kinds, same rule that every entry carries a
provenance line — with two differences the surface demands:

  · hover targets live on the chrome, never on the map, because the map's hover
    and click already belong to the stations;
  · except for a handful of deliberate anchored callouts, drawn only when LEARN
    is on, which say what the network shows rather than what a word means.
"""
import io, sys
SRC = "/home/claude/olympus/src/atlas.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# ============================================================== CSS
CSS = u'''
/* ---------- the learning layer ---------- */
.learn{display:flex;align-items:center;gap:6px;font-family:var(--mono);font-size:9.5px;
  letter-spacing:.12em;text-transform:uppercase;color:var(--ink3);cursor:pointer;user-select:none;
  border:1px solid var(--line2);border-radius:2px;padding:4px 9px}
.learn .sw{width:22px;height:12px;border-radius:7px;background:var(--line2);position:relative;transition:background .15s}
.learn .sw::after{content:"";position:absolute;top:2px;left:2px;width:8px;height:8px;border-radius:50%;
  background:var(--ink3);transition:transform .15s,background .15s}
.learn[aria-pressed="true"]{border-color:var(--s1);color:var(--ice)}
.learn[aria-pressed="true"] .sw{background:rgba(15,165,190,.5)}
.learn[aria-pressed="true"] .sw::after{transform:translateX(10px);background:var(--ice)}
.exbox{position:fixed;z-index:60;max-width:330px;background:rgba(9,16,23,.97);border:1px solid var(--line2);
  border-radius:3px;padding:10px 12px 9px;box-shadow:0 10px 30px rgba(0,0,0,.55);pointer-events:none}
.exh{display:flex;align-items:center;gap:7px;margin-bottom:5px}
.exh b{font-family:var(--disp);font-size:13px;letter-spacing:.03em;color:var(--ink)}
.exk{font-family:var(--disp);font-size:8.5px;letter-spacing:.16em;padding:1px 4px;border-radius:1px}
.k-obj{background:rgba(15,165,190,.18);color:#7FD5E4}
.k-ins{background:rgba(155,118,220,.18);color:#C3AEEE}
.k-num{background:rgba(200,128,47,.18);color:#E8B77E}
.k-mech{background:rgba(79,158,106,.20);color:#8FD4AC}
.exb{font-size:11.5px;line-height:1.55;color:var(--ink2)}
.exb b{color:var(--ink);font-weight:600}
.exp{margin-top:7px;padding-top:6px;border-top:1px solid var(--line);font-family:var(--mono);font-size:9px;
  line-height:1.45;color:var(--ink4)}
body.learning [data-ex]{cursor:help}
.exidx{padding:2px 10px 10px;flex:0 0 auto;max-height:38%;overflow-y:auto;border-top:1px solid var(--line)}
.exidx .grp{font-family:var(--mono);font-size:8.5px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--ink4);margin:9px 4px 4px}
.exidx button{display:block;width:100%;text-align:left;font-size:11.5px;line-height:1.35;color:var(--ink3);
  padding:3px 5px;border-radius:2px;border-left:2px solid transparent}
.exidx button:hover,.exidx button:focus-visible{color:var(--ice);background:var(--panel2);border-left-color:var(--s1)}
'''
once(u'.foot{background:var(--panel);padding:9px 16px;', CSS + u'\n.foot{background:var(--panel);padding:9px 16px;', "atlas learn css")

# ============================================================== markup
once(u'    <div class="hstat">\n      <div><b id="hsFac">—</b>facilities</div>\n      <div><b id="hsNat">—</b>operators</div>\n      <div><b id="hsLink">—</b>links</div>\n      <div><b id="hsOpen">—</b>with open data</div>\n    </div>',
     u'''    <button class="learn" id="learnBtn" aria-pressed="false" style="margin-left:auto"><span class="sw"></span>Learn</button>
    <div class="hstat">
      <div data-ex="counts"><b id="hsFac">—</b>facilities</div>
      <div data-ex="operators"><b id="hsNat">—</b>operators</div>
      <div data-ex="edges"><b id="hsLink">—</b>links</div>
      <div data-ex="openness"><b id="hsOpen">—</b>with open data</div>
    </div>''',
     "learn button + header stats")
once(u'<nav class="xnav" aria-label="Olympus surfaces">', u'<nav class="xnav" aria-label="Olympus surfaces" data-ex="surfaces">', "xnav -> surfaces")
once(u'<div class="srch"><input id="q" type="search" placeholder="search station, operator, region…" autocomplete="off"></div>',
     u'<div class="srch" data-ex="search"><input id="q" type="search" placeholder="search station, operator, region…" autocomplete="off"></div>', "search -> search")
once(u'<div class="ph"><h2>Facilities</h2><span class="n" id="listN"></span></div>\n      <div class="scroll" id="list"></div>',
     u'''<div class="ph"><h2>Facilities</h2><span class="n" id="listN"></span></div>
      <div class="scroll" id="list"></div>
      <div class="ph" id="exIndexHead" hidden><h2>Explainers</h2><span class="n" id="exCount"></span></div>
      <div class="exidx" id="exIndex" hidden></div>''',
     "index markup")

# legend, readouts, footer
once(u'<div class="t">Public presence</div>', u'<div class="t" data-ex="openness">Public presence</div>', "legend title")
for k, ex, txt in [("open","open_level","Open — live feed or open data"),
                   ("partial","partial_level","Partial — national portal or on request"),
                   ("minimal","minimal_level","Minimal — operator page only"),
                   ("opaque","opaque_level","Opaque — nothing public")]:
    once(u'<span><i class="d" style="background:var(--%s)"></i>%s</span>' % (k, txt),
         u'<span data-ex="%s"><i class="d" style="background:var(--%s)"></i>%s</span>' % (ex, k, txt),
         "legend " + k)
once(u'<span><i class="d" style="background:none;border:1.5px solid var(--ink2);box-sizing:border-box"></i>Gateway port</span>',
     u'<span data-ex="gateway"><i class="d" style="background:none;border:1.5px solid var(--ink2);box-sizing:border-box"></i>Gateway port</span>', "legend gateway")
once(u'<span><i class="d" style="background:none;border:1.5px solid var(--ember);border-radius:0;transform:rotate(45deg)"></i>Heritage site</span>',
     u'<span data-ex="heritage"><i class="d" style="background:none;border:1.5px solid var(--ember);border-radius:0;transform:rotate(45deg)"></i>Heritage site</span>', "legend heritage")
once(u'<div class="readout" id="proj">—</div>', u'<div class="readout" id="proj" data-ex="projection">—</div>', "proj readout")
once(u'<div class="readout" id="scaleR">—</div>', u'<div class="readout" id="scaleR" data-ex="scale">—</div>', "scale readout")
once(u'<div class="fresh" id="fresh"></div>', u'<div class="fresh" id="fresh" data-ex="age_stamp"></div>', "fresh panel")
once(u'<span id="fprov">—</span>', u'<span id="fprov" data-ex="comnap">—</span>', "footer provenance")
once(u'<span style="margin-left:auto">Routes are schematic great circles between published positions, not flown or sailed tracks.</span>',
     u'<span style="margin-left:auto" data-ex="routes">Routes are schematic great circles between published positions, not flown or sailed tracks.</span>', "footer routes")
once(u'<div class="modebar" id="driftX" role="group" aria-label="Drift vector length">',
     u'<div class="modebar" id="driftX" role="group" aria-label="Drift vector length" data-ex="drift_true_length">', "driftX bar")
once(u'<button data-mode="BOTH" aria-pressed="false">Both</button>',
     u'<button data-mode="BOTH" aria-pressed="false" data-ex="both_poles">Both</button>', "both mode")

io.open(SRC, "w", encoding="utf8").write(s)
print("markup + css written")
