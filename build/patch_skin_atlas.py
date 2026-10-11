#!/usr/bin/env python3
"""patch_skin_atlas.py — the Ops and Lab skins, and the stacked header, on the
Station Network (dist/atlas.html).

Same mechanism as the deck (build/patch_skin_lab.py + build/patch_header_stack.py):
data-skin="ops"|"lab" on <html>, chosen by #ops / #lab, then the viewer's last
choice (localStorage "olympus.skin", shared with the deck on the public site,
where both surfaces have one origin), then the build default.

Single-sourced from the deck's patch, so the two surfaces cannot drift: the Lab
tokens, the boot script, the switch markup, the Lab sigil and the disc shadow.

What changes on this surface, and what must not:
  * The map: each pole's imagery disc stays exactly as drawn. In Lab only the
    field around the disc is light: after the disc is drawn, whatever lies
    outside its imagery radius (the radius drawBase clips to) is erased so the
    page's field shows, and the shadow goes in underneath. The Both view's two
    labels and divider take Lab colours. Every station, route, gateway, live layer and
    annotation lies inside a disc and is drawn identically in both skins.
  * Openness and route colours are data. They stay as they are on the map and
    in the legend. Where they were used as TEXT on panels that turn white
    (station badges, the route and live-layer toggles), Lab sets the text in
    ink, or a darkened mix of the colour, and keeps the colour as a swatch.
    Ops keeps its inline colours untouched; Lab overrides them.
  * Seasonal (hollow) list dots were filled near-black; on white that reads as
    a solid dot, so they get a class and Lab fills them with the panel.
  * Header: Deck · Stations · Named Ice over Learn · Ops · Lab, six equal cells.

Convention: exact-string anchors, each must match exactly once, counted at its
own turn on a working copy; nothing is written unless all of them do.

usage: python build/patch_skin_atlas.py IN OUT [--default ops|lab] [--dry-run]
"""
import argparse, hashlib, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_skin_lab as deck   # noqa: E402  (the deck's skin: single source for shared parts)

TOKENS = re.search(r':root\[data-skin="lab"\]\{.*?\n\}', deck.CSS, re.S).group(0)
HALO_JS = re.search(r'/\* Lab sets the planet on a pale field.*?\n\}\n', deck.JS_CORE, re.S).group(0)
SIGIL_LAB = deck.SIGIL_LAB.replace('class="sigil sg-lab"', 'class="sg-lab" width="24" height="24"')

# Ops values are the literals cut out of the surface; Lab values sit beside them.
CANVAS = [
    ('g.font = "600 9px ui-monospace, monospace"; g.textAlign="center"; g.fillStyle = "#3E4E5E";',
     "pair", '"#3E4E5E"'),
    ('if(!S){ g.strokeStyle="#1D2A38"; g.lineWidth=1;',
     "div", '"#1D2A38"'),
]
LAB = {"pair": '"#54626F"', "div": '"#C5CFD8"', "field": "true", "halo": deck.LAB["halo"]}

JS_CORE = r'''
/* ---------------- skins ----------------
   The same two looks as the deck (build/patch_skin_lab.py). On this surface the
   imagery disc of each pole is the planet: it and everything on it are drawn
   identically in both skins. Lab only lightens the field around it. */
const SKIN={
  ops:{__OPS__, field:false, halo:null},
  lab:{__LAB__}
};
const skinNow=()=>SKIN[document.documentElement.getAttribute("data-skin")] ? document.documentElement.getAttribute("data-skin") : "ops";
let TH=SKIN[skinNow()];
function setSkin(k,save){
  if(!SKIN[k]) return;
  document.documentElement.setAttribute("data-skin",k);
  TH=SKIN[k];
  $$(".skin button").forEach(b=>b.setAttribute("aria-pressed", String(b.dataset.k===k)));
  if(save){ try{ localStorage.setItem("olympus.skin",k); }catch(e){} }
  try{ draw(); }catch(e){}
}
''' + HALO_JS + r'''
/* Lab: the disc is drawn exactly as in Ops, then everything outside it is
   erased so the light field shows, and the shadow is slid in underneath.
   Clipping the drawing to the disc instead would re-rasterise the graticule
   inside a curved clip, which Chrome antialiases differently by a level or
   two: invisible, but no longer the same pixels. */
function skinField(d, S){
  const RD = d.k * ((IMG && IMG.rmax && IMG.rmax[S?"S":"N"]) || GMAX[S?"S":"N"]);
  g.save();
  g.globalCompositeOperation = "destination-out";
  g.beginPath(); g.rect(d.x0, 0, d.x1-d.x0, st.h); g.arc(d.cx, d.cy, RD, 0, 7); g.fill("evenodd");
  g.globalCompositeOperation = "destination-over";
  skinHalo(g, d.cx, d.cy, RD);
  g.restore();
}
'''

JS_BOOT = r'''
$$(".skin button").forEach(b=>{
  b.setAttribute("aria-pressed", String(b.dataset.k===skinNow()));
  b.addEventListener("click",()=>setSkin(b.dataset.k,true));
});
window.addEventListener("hashchange",()=>{ const h=(location.hash||"").slice(1); if(SKIN[h]) setSkin(h,false); });
'''

DISC_OLD = '''  g.moveTo(d.cx,d.cy-4); g.lineTo(d.cx,d.cy+4); g.stroke();

  g.restore();'''
DISC_NEW = '''  g.moveTo(d.cx,d.cy-4); g.lineTo(d.cx,d.cy+4); g.stroke();

  if(TH.field) skinField(d, S);
  g.restore();'''

LIST_OLD = '<div class="dot" style="background:${OPEN_C[s.openness]||"#7E8FA1"};'
LIST_NEW = '<div class="dot${s.seasonality!=="Year-Round"?" hollow":""}" style="background:${OPEN_C[s.openness]||"#7E8FA1"};'
BADGE_OLD = '<span class="bdg" style="color:${color};'
BADGE_NEW = '<span class="bdg" style="--c:${color};color:${color};'
NET_OLD = 'aria-pressed="true" style="color:${EDGE_C[k]}"'
NET_NEW = 'aria-pressed="true" style="--c:${EDGE_C[k]};color:${EDGE_C[k]}"'
LIVE_OLD = 'aria-pressed="true" style="color:${l.col}"'
LIVE_NEW = 'aria-pressed="true" style="--c:${l.col};color:${l.col}"'

HDR_OLD_RE = re.compile(
    r'\n    <nav class="xnav" aria-label="Olympus surfaces" data-ex="surfaces">\n.*?\n</nav>\n\n'
    r'    <button class="learn" id="learnBtn" aria-pressed="false" style="margin-left:auto"><span class="sw"></span>Learn</button>\n',
    re.S)

SIGIL_OPS_OLD = '<svg width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" fill="none">'
SIGIL_OPS_NEW = '<svg class="sg-ops" width="24" height="24" viewBox="0 0 24 24" aria-hidden="true" fill="none">'
SIGIL_END = '<circle cx="12" cy="12" r="1.5" fill="#7FE3F5"/>\n      </svg>'

CSS_ANCHOR = '  .scroll{max-height:420px}\n}\n</style>'
CSS = r'''
<style id="skin-lab">
/* ---------- skins ----------
   Ops is the surface as it was written. Lab is the deck's instrument/lab look:
   the same tokens (copied from build/patch_skin_lab.py at build time), white-
   grey panels on hairlines, the imagery discs on a pale light-table field. */
:root{ --field:#04070B; --field-hi:#04070B; --plate:transparent }
.skin{display:flex}
.sg-lab{display:none}
__TOKENS__
html[data-skin="lab"],html[data-skin="lab"] body{background:var(--void)}
html[data-skin="lab"] .sg-ops{display:none}
html[data-skin="lab"] .sg-lab{display:block}
html[data-skin="lab"] a{border-bottom-color:rgba(11,110,150,.3)}
html[data-skin="lab"] ::selection{background:rgba(11,110,150,.18)}

/* header text */
html[data-skin="lab"] .brand h1{font-size:18px;font-weight:600;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .brand .sub{letter-spacing:.07em}
html[data-skin="lab"] .hstat b{font-family:var(--mono);font-weight:500}

/* panels and lists: sentence-case heads, hairlines from the tokens */
html[data-skin="lab"] .ph h2{font-family:var(--sans);font-size:12px;font-weight:600;letter-spacing:.005em;text-transform:none;color:var(--ink)}
html[data-skin="lab"] .stn,html[data-skin="lab"] .nat td{border-color:var(--line)}
html[data-skin="lab"] .stn.sel{background:rgba(11,110,150,.08)}
html[data-skin="lab"] .chip.on{background:rgba(11,110,150,.08)}
/* openness dots keep their data colour; on white they get an edge, and the
   seasonal (hollow) ones are hollow against the panel, not filled near-black */
html[data-skin="lab"] .stn .dot,html[data-skin="lab"] .chip i,html[data-skin="lab"] .lgd i.d{outline:1px solid rgba(19,32,43,.22)}
html[data-skin="lab"] .stn .dot.hollow{background:var(--panel)!important}
/* badges carry their colour in --c; as text on white it is darkened */
html[data-skin="lab"] .bdg{color:color-mix(in oklab,var(--c) 50%,#000)!important;
  border-color:color-mix(in srgb,var(--c) 50%,transparent)!important;background:color-mix(in srgb,var(--c) 11%,transparent)!important}
html[data-skin="lab"] .pgn a{color:#5A3CA8;border-bottom-color:rgba(90,60,168,.3)}
html[data-skin="lab"] .pgn a:hover{border-bottom-color:#5A3CA8}
html[data-skin="lab"] .dhero h3{letter-spacing:-.005em}
html[data-skin="lab"] .kv .v{font-size:16px}

/* the map: the discs on a pale light table, ruled at 24 px */
html[data-skin="lab"] .mapwrap{background:
  radial-gradient(rgba(19,32,43,.075) 1px,transparent 1.3px) 12px 12px/24px 24px,
  radial-gradient(ellipse at 50% 46%,var(--field-hi) 0,var(--field) 78%)}
/* HUD furniture sits over the dark discs and the light field alike: opaque-ish plates */
html[data-skin="lab"] .modebar{background:var(--panel);border-color:var(--line2);border-radius:4px}
html[data-skin="lab"] .modebar button{border-right-color:var(--line2)}
html[data-skin="lab"] .modebar button[aria-pressed=true]{background:linear-gradient(rgba(11,110,150,.12),rgba(11,110,150,.12)),var(--panel);color:var(--ice)}
html[data-skin="lab"] #modeBar button{letter-spacing:.02em;text-transform:none;font-family:var(--sans);font-size:11px;font-weight:500}
html[data-skin="lab"] #modeBar button[aria-pressed=true]{background:var(--ice);color:#fff}
/* route and live-layer toggles: ink text, the line colour as a swatch */
html[data-skin="lab"] #netBar button,html[data-skin="lab"] #liveBar button{color:var(--ink3)!important}
html[data-skin="lab"] #netBar button[aria-pressed=true],html[data-skin="lab"] #liveBar button[aria-pressed=true]{color:var(--ink)!important}
html[data-skin="lab"] #netBar button::before,html[data-skin="lab"] #liveBar button::before{content:"";display:inline-block;
  width:11px;height:3px;border-radius:1px;background:var(--c);margin-right:6px;vertical-align:2px;opacity:.35}
html[data-skin="lab"] #netBar button[aria-pressed=true]::before,html[data-skin="lab"] #liveBar button[aria-pressed=true]::before{opacity:1}
html[data-skin="lab"] .readout,html[data-skin="lab"] .lgd,html[data-skin="lab"] .fresh{background:var(--plate);border-color:var(--line);border-radius:4px}
html[data-skin="lab"] .tip{background:var(--panel);box-shadow:0 4px 14px rgba(19,32,43,.14);border-radius:4px}

/* learning layer */
html[data-skin="lab"] .learn[aria-pressed="true"] .sw{background:var(--ice)}
html[data-skin="lab"] .learn[aria-pressed="true"] .sw::after{background:#fff}
html[data-skin="lab"] .exbox{background:rgba(255,255,255,.98);box-shadow:0 8px 28px rgba(19,32,43,.16);border-radius:4px}
html[data-skin="lab"] .exh b{font-weight:600;letter-spacing:.005em}
html[data-skin="lab"] .exk{letter-spacing:.06em;font-weight:600}
html[data-skin="lab"] .k-mech{background:rgba(45,122,74,.12);color:#21673E}
html[data-skin="lab"] .k-ins{background:rgba(110,75,192,.11);color:#5A3CA8}
html[data-skin="lab"] .k-obj{background:rgba(11,110,150,.10);color:#0A6584}
html[data-skin="lab"] .k-num{background:rgba(168,90,23,.12);color:#8F4C12}

/* ---------- header controls: one block, six equal cells ----------
   As on the deck: row 1 is where you are, row 2 is what you do here. */
.hdr .hctl{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,minmax(24px,1fr));
  gap:1px;background:var(--line);border-left:1px solid var(--line);border-right:1px solid var(--line);
  flex:0 0 auto;align-self:stretch}
.hdr .hctl .xnav,.hdr .hctl .skin{display:grid;grid-template-columns:subgrid;gap:1px;margin:0;border:0;border-radius:0;
  background:none;overflow:visible;align-self:stretch}
.hdr .hctl .xnav{grid-column:1/-1;grid-row:1}
.hdr .hctl .learn{grid-column:1;grid-row:2}
.hdr .hctl .skin{grid-column:2/-1;grid-row:2}
.hdr .hctl .xnav a,.hdr .hctl .learn,.hdr .hctl .skin button{display:flex;align-items:center;justify-content:center;gap:6px;
  margin:0;padding:0 14px;border:0;border-radius:0;align-self:stretch;
  background-color:var(--panel);background-image:none;
  font-family:var(--mono);font-size:9.5px;font-weight:400;letter-spacing:.15em;text-transform:uppercase;
  color:var(--ink3);white-space:nowrap;text-decoration:none}
.hdr .hctl .learn .sw{flex:0 0 auto}
.hdr .hctl a:hover,.hdr .hctl button:hover{color:var(--ice);background-image:linear-gradient(rgba(15,165,190,.10),rgba(15,165,190,.10))}
.hdr .hctl a[aria-current=page],.hdr .hctl button[aria-pressed="true"]{color:var(--ice);background-image:linear-gradient(rgba(15,165,190,.16),rgba(15,165,190,.16))}
.hdr .hctl a:focus-visible,.hdr .hctl button:focus-visible{outline-offset:-2px}
html[data-skin="lab"] .hdr .hctl a,html[data-skin="lab"] .hdr .hctl button{letter-spacing:.07em}
html[data-skin="lab"] .hdr .hctl a:hover,html[data-skin="lab"] .hdr .hctl button:hover{background-image:linear-gradient(rgba(11,110,150,.06),rgba(11,110,150,.06))}
html[data-skin="lab"] .hdr .hctl a[aria-current=page],html[data-skin="lab"] .hdr .hctl button[aria-pressed="true"]{background-image:linear-gradient(rgba(11,110,150,.10),rgba(11,110,150,.10))}
@media (max-width:900px){
  .hdr .hctl{flex:1 1 100%;border:1px solid var(--line);grid-template-rows:repeat(2,32px);align-self:auto}
  .hdr .hctl .xnav a,.hdr .hctl .learn,.hdr .hctl .skin button{padding:0 8px;letter-spacing:.08em}
}
</style>'''

BOOT_END = 'if(window.ResizeObserver) new ResizeObserver(()=>fit()).observe(map.parentElement);\n'

def build_edits(default):
    ops_pairs = [k + ":" + lit for _, k, lit in CANVAS]
    lab_pairs = ",\n    ".join(f"{k}:{v}" for k, v in LAB.items())
    core = JS_CORE.replace("__OPS__", ",\n    ".join(ops_pairs)).replace("__LAB__", lab_pairs)
    edits = [(a, a.replace(lit, "TH." + k, 1), "canvas:" + k) for a, k, lit in CANVAS]
    A_DOLLAR = 'const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];'
    edits += [
        (A_DOLLAR, A_DOLLAR + "\n" + core, "js:skin-core"),
        (DISC_OLD, DISC_NEW, "canvas:disc-field"),
        (BOOT_END, BOOT_END + JS_BOOT, "js:skin-boot"),
        (LIST_OLD, LIST_NEW, "html:list-hollow"),
        (BADGE_OLD, BADGE_NEW, "html:badge-var"),
        (NET_OLD, NET_NEW, "html:net-var"),
        (LIVE_OLD, LIVE_NEW, "html:live-var"),
        (CSS_ANCHOR, CSS_ANCHOR + CSS.replace("__TOKENS__", TOKENS), "css:skin-lab"),
        ('<title>Olympus Station Network</title>',
         '<title>Olympus Station Network</title>\n' + deck.BOOT_TAG.replace("__DEFAULT__", default), "html:boot"),
        (SIGIL_OPS_OLD, SIGIL_OPS_NEW, "html:sigil-ops"),
        (SIGIL_END, SIGIL_END + SIGIL_LAB, "html:sigil-lab"),
    ]
    return edits

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--default", choices=["ops", "lab"], default="ops")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = open(a.src, encoding="utf-8", newline="").read()
    if "data-skin" in s: sys.exit("ABORT: input already carries a skin")
    m = deck.WRAP_HEAD.match(s)
    if m:
        s = s[m.end():]
        if s.endswith("</body></html>"): s = s[:-len("</body></html>")]
        print("stripped host document skeleton")

    bad, w = [], s
    def count(name, n):
        print(f"  {name:20s} matches={n}")
        if n != 1: bad.append((name, n))
    for old, new, name in build_edits(a.default):
        n = w.count(old); count(name, n)
        if n == 1: w = w.replace(old, new, 1)
    # header: the nav and the Learn toggle become the block, with the switch
    hm = list(HDR_OLD_RE.finditer(w)); count("html:header-block", len(hm))
    if len(hm) == 1:
        h = hm[0].group(0)
        nav = h[h.index("<nav"):h.index("</nav>") + len("</nav>")]
        learn = '<button class="learn" id="learnBtn" aria-pressed="false"><span class="sw"></span>Learn</button>'
        block = ('\n    <div class="hctl">\n    ' + nav + '\n    ' + learn + deck.SKIN_BUTTONS + '\n    </div>\n')
        w = w[:hm[0].start()] + block + w[hm[0].end():]
    if bad: sys.exit("ABORT: " + ", ".join(f"{n}={c}" for n, c in bad))
    if a.dry_run: print("dry run: all anchors unique, nothing written"); return
    open(a.out, "w", encoding="utf-8", newline="").write(w)
    b = w.encode("utf-8")
    print(f"wrote {a.out}  {len(b):,} bytes  default={a.default}  sha256={hashlib.sha256(b).hexdigest()[:16]}")

if __name__ == "__main__":
    main()
