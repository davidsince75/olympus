#!/usr/bin/env python3
"""patch_skin_lab.py — give the Olympus Deck a second skin, "Lab", beside "Ops".

One deck, two skins. The skin is an attribute on <html> (data-skin="ops"|"lab"),
switched from the header, remembered per viewer, and reachable by a bare #lab or
#ops anchor. It is NOT data-theme: the artifact viewer writes its own data-theme
on the root element, and the deck must not fight it.

What the skin changes, and what it must not:
  * CSS chrome: tokens and component overrides, all under html[data-skin="lab"].
  * Canvas drawn OFF the planet: the timeline, the El Nino chart, the PAIR labels,
    and a soft shadow under the disc/globe (Lab only, cached as a sprite).
  * Nothing drawn ON the planet. Imagery, ice field, currents, fronts, contours,
    aurora, drift, SAR, stations: identical in both skins, byte for byte. The
    planet's offscreen caches therefore need no re-keying on skin.

Ops stays byte-identical in rendering: every literal replaced below is moved,
unchanged, into SKIN.ops by this script, so the two cannot disagree.

Convention (as patch.py): every anchor must match exactly once or the whole run
aborts before writing. --dry-run reports the counts and writes nothing.

Usage:
  python patch_skin_lab.py IN.html OUT.html [--default ops|lab] [--title "Olympus Deck"] [--dry-run]

IN may be the authored deck or a page read back from the artifact host; the
host's document skeleton, if present, is stripped (the host adds it on publish).
"""
import argparse, hashlib, json, re, sys

# ---------------------------------------------------------------- canvas literals
# (anchor-with-literal, skin key, the literal). The literal is cut out of the
# anchor and replaced by TH.<key>; SKIN.ops[key] gets the literal itself.
CANVAS = [
    ('g.fillStyle="rgba(147,167,186,.85)"; g.letterSpacing="2px";',
     "pair", '"rgba(147,167,186,.85)"'),
    ('g.strokeStyle="rgba(29,42,56,.9)"; g.lineWidth=1;\n  g.font="9px \'IBM Plex Mono\', monospace"; g.fillStyle="#3E4E5E"; g.textAlign="right";',
     "tlGrid", '"rgba(29,42,56,.9)"'),
    ('g.font="9px \'IBM Plex Mono\', monospace"; g.fillStyle="#3E4E5E"; g.textAlign="right";\n  for(let i=0;i<=4;i++){',
     "tlAxis", '"#3E4E5E"'),
    ('g.strokeStyle="rgba(155,118,220,.5)"; g.setLineDash([2,3]); g.lineWidth=1;',
     "tlRun", '"rgba(155,118,220,.5)"'),
    ('const TONE={sh:["rgba(15,165,190,.42)","#7FE3F5"], nh:["rgba(200,128,47,.40)","#E8B77E"]};',
     "tlTone", '{sh:["rgba(15,165,190,.42)","#7FE3F5"], nh:["rgba(200,128,47,.40)","#E8B77E"]}'),
    ('g.strokeStyle="#C8802F"; g.lineWidth=1.3;\n      g.beginPath(); g.arc(Xo(o),Y(a.v),4.2,0,7); g.stroke();',
     "tlAnchor", '"#C8802F"'),
    ('g.fillStyle="#5F7286"; g.textAlign="right"; g.font="9px \'IBM Plex Mono\', monospace";',
     "tlKey", '"#5F7286"'),
    ('g.strokeStyle="#7FE3F5"; g.lineWidth=1; g.beginPath(); g.moveTo(px,T-3);',
     "tlCur", '"#7FE3F5"'),
    ('g.fillStyle="#7FE3F5"; g.beginPath(); g.moveTo(px,T-3);',
     "tlCur", '"#7FE3F5"'),
    ('g.strokeStyle="rgba(147,167,186,.45)"; g.lineWidth=1; g.beginPath(); g.moveTo(0,y0);',
     "fcZero", '"rgba(147,167,186,.45)"'),
    ('g.setLineDash([3,3]); g.strokeStyle="rgba(242,198,164,.65)";',
     "fcRef", '"rgba(242,198,164,.65)"'),
    ('g.fillStyle="rgba(242,198,164,.8)"; g.textAlign="left"; g.fillText("+2.5 °C"',
     "fcRefTx", '"rgba(242,198,164,.8)"'),
    ('g.fillStyle="#F2C6A4"; g.beginPath(); g.arc(X(i),Y(v[i]),2.4,0,7); g.fill();',
     "fcDot", '"#F2C6A4"'),
    ('g.fillStyle="rgba(221,232,241,.85)"; g.textAlign=al;',
     "fcVal", '"rgba(221,232,241,.85)"'),
]

# Lab values for the same keys. Each pairs with a CSS token below where a key in
# the HTML shows the same mark (the timeline key uses --ice, --s2, --s3).
LAB = {
    "pair":    '"#54626F"',
    "tlGrid":  '"#E3E8ED"',
    "tlAxis":  '"#6B7885"',
    "tlRun":   '"rgba(110,75,192,.55)"',
    "tlTone":  '{sh:["rgba(15,165,190,.6)","#0B6E96"], nh:["rgba(200,128,47,.55)","#A85A17"]}',
    "tlAnchor":'"#A85A17"',
    "tlKey":   '"#54626F"',
    "tlCur":   '"#0B6E96"',
    "fcZero":  '"rgba(56,71,86,.35)"',
    "fcRef":   '"rgba(162,72,27,.6)"',
    "fcRefTx": '"#A2481B"',
    "fcDot":   '"#A2481B"',
    "fcVal":   '"#13202B"',
    "halo":    '"rgba(16,34,52,.30)"',
}

# ---------------------------------------------------------------- the skin runtime
JS_CORE = r'''
/* ---------------- skins ----------------
   Two looks over one deck. Only what is drawn OFF the planet differs between
   them; the planet and every layer on it are drawn identically in both, so no
   offscreen cache depends on the skin. SKIN.ops holds the literals this deck
   was written with, moved here unchanged by build/patch_skin_lab.py. */
const SKIN={
  ops:{__OPS__, halo:null},
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
  try{ featChart(); }catch(e){}
  try{ drawTL(); }catch(e){}
}
/* Lab sets the planet on a pale field, where a soft shadow gives it weight. A
   blurred circle is costly to rasterise, so it is drawn once into a sprite and
   composited; the key is the radius in 4 px steps, so a zoom re-renders it at
   most every few pixels. Past 900 px the disc runs off the panel and the shadow
   could not be seen, so it is skipped rather than allocated. */
const HALO={cv:null,key:""};
function skinHalo(g,cx,cy,s){
  if(!TH.halo || !(s>8) || s>900) return;
  const dpr=Math.min(2,window.devicePixelRatio||1), R=Math.max(8,Math.round(s/4)*4);
  const pad=Math.ceil(R*0.16)+4, W=(R+pad)*2, key=R+"|"+dpr+"|"+TH.halo;
  if(HALO.key!==key){
    const c=HALO.cv||(HALO.cv=document.createElement("canvas"));
    c.width=Math.round(W*dpr); c.height=Math.round(W*dpr);
    const x=c.getContext("2d"); x.setTransform(dpr,0,0,dpr,0,0); x.clearRect(0,0,W,W);
    x.shadowColor=TH.halo; x.shadowBlur=R*0.07*dpr; x.shadowOffsetY=R*0.022*dpr;
    x.fillStyle="#0A1722"; x.beginPath(); x.arc(W/2,W/2,R,0,7); x.fill();
    HALO.key=key;
  }
  const k=s/R, Wd=W*k;
  g.drawImage(HALO.cv, cx-Wd/2, cy-Wd/2, Wd, Wd);
}
'''

JS_BOOT = r'''
$$(".skin button").forEach(b=>{
  b.setAttribute("aria-pressed", String(b.dataset.k===skinNow()));
  b.addEventListener("click",()=>setSkin(b.dataset.k,true));
});
window.addEventListener("hashchange",()=>{ const h=(location.hash||"").slice(1); if(SKIN[h]) setSkin(h,false); });
'''

# first thing in <body>: set the skin before the first paint, so there is no flash
BOOT_TAG = ('<script>(function(){var d="__DEFAULT__",k=null,h=(location.hash||"").slice(1);'
            'if(h==="lab"||h==="ops")k=h;else{try{var v=localStorage.getItem("olympus.skin");'
            'if(v==="lab"||v==="ops")k=v;}catch(e){}}'
            'document.documentElement.setAttribute("data-skin",k||d);})();</script>')

SKIN_BUTTONS = ('\n    <div class="skin" role="group" aria-label="Interface skin">'
                '<button type="button" data-k="ops" aria-pressed="true" title="Ops skin (#ops)">Ops</button>'
                '<button type="button" data-k="lab" aria-pressed="false" title="Lab skin (#lab)">Lab</button></div>')

SIGIL_LAB = '''
      <svg class="sigil sg-lab" viewBox="0 0 24 24" aria-hidden="true" fill="none" style="color:var(--ink)">
        <circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="1.15"/>
        <ellipse cx="12" cy="12" rx="4" ry="9.5" stroke="currentColor" stroke-width=".85"/>
        <path d="M3.3 8.2h17.4M3.3 15.8h17.4" stroke="currentColor" stroke-width=".85"/>
        <path d="M2.5 12h19" stroke="var(--ice)" stroke-width="1.25"/>
      </svg>'''

CSS = r'''
<style id="skin-lab">
/* ---------- skins ----------
   The switch is always shown; Ops is the deck as it was written. Lab is the
   instrument/lab look: cool white-grey panels on hairlines, the planet on a
   pale light-table field, sentence-case headings, readouts still in Plex Mono.
   Everything below the switch rules applies to Lab only. */
:root{ --field:#04070B; --field-hi:#04070B; --plate:transparent; --sea:transparent }
.skin{display:flex;align-self:center;margin:0 10px 0 0;border:1px solid var(--line2);border-radius:2px;overflow:hidden;background:rgba(6,9,14,.6);flex:0 0 auto}
.skin button{font-family:var(--mono);font-size:9.5px;letter-spacing:.15em;text-transform:uppercase;padding:5px 10px;color:var(--ink3)}
.skin button+button{border-left:1px solid var(--line2)}
.skin button:hover{color:var(--ice)}
.skin button[aria-pressed="true"]{color:var(--ice);background:rgba(15,165,190,.16)}
.sg-lab{display:none}
@media (max-width:720px){ .skin{margin:6px 0 6px 8px} .hdr .skin+.xnav{margin-left:8px} }

/* Lab tokens: the same names, so every component follows without being restyled.
   Ink steps measured on white: 16.5, 9.5, 6.3, 4.6 : 1. */
:root[data-skin="lab"]{
  --void:#EDF1F4; --panel:#FFFFFF; --panel2:#F3F6F8; --panel3:#E6ECF1;
  --line:#DAE1E7; --line2:#C5CFD8;
  --ink:#13202B; --ink2:#384756; --ink3:#54626F; --ink4:#66737F;
  --ice:#0B6E96;
  --s1:#1388AE; --s2:#A85A17; --s3:#6E4BC0; --s4:#2D7A4A;
  --good:#2D7A4A; --warn:#A85A17; --crit:#BB3B33;
  --disp:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;
  --field:#E3E9EE; --field-hi:#F7F9FA; --plate:rgba(255,255,255,.86); --sea:#0B1620;
  color-scheme:light;
}
/* html too: the public site wraps the deck in a page that paints html dark */
html[data-skin="lab"],html[data-skin="lab"] body{background:var(--void)}

/* header */
html[data-skin="lab"] .sg-ops{display:none}
html[data-skin="lab"] .sg-lab{display:block}
html[data-skin="lab"] .brand h1{font-size:16px;font-weight:600;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .brand .sub{font-size:10.5px;letter-spacing:.03em;text-transform:none;margin-top:4px}
html[data-skin="lab"] .xnav,html[data-skin="lab"] .logbtn,html[data-skin="lab"] .skin{background:var(--panel);border-radius:4px}
html[data-skin="lab"] .xnav a,html[data-skin="lab"] .logbtn,html[data-skin="lab"] .skin button{letter-spacing:.07em}
html[data-skin="lab"] .xnav a:hover,html[data-skin="lab"] .skin button:hover{background:rgba(11,110,150,.06)}
html[data-skin="lab"] .xnav a[aria-current=page],html[data-skin="lab"] .logbtn[aria-pressed="true"],html[data-skin="lab"] .skin button[aria-pressed="true"]{background:rgba(11,110,150,.10)}
html[data-skin="lab"] .feed .nm{font-size:10.5px;font-weight:500;letter-spacing:.05em}
html[data-skin="lab"] .dot.stale{background:#A9B4BE}

/* headings in sentence case; micro-labels keep capitals with modest tracking */
html[data-skin="lab"] .ph h2{font-size:12.5px;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .note h3,html[data-skin="lab"] .dlog h3{font-size:12px;letter-spacing:.005em;text-transform:none;color:var(--ink)}
html[data-skin="lab"] .dlog-hd h2{font-size:14px;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .pairrow .lab,html[data-skin="lab"] .hero .lab,html[data-skin="lab"] .grow .k,
html[data-skin="lab"] .feat .fk,html[data-skin="lab"] .feat .nums .lab,html[data-skin="lab"] .tp .dt,
html[data-skin="lab"] .legend .cap,html[data-skin="lab"] .exidx .grp,html[data-skin="lab"] .dlog-meta dt,
html[data-skin="lab"] table.dlt th,html[data-skin="lab"] table.dlt tr.grp td,html[data-skin="lab"] .dlog-ym small,
html[data-skin="lab"] .clock .l{letter-spacing:.07em;font-weight:500}
html[data-skin="lab"] .stn .nm{font-size:12.5px;font-weight:500;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .evt .ttl{font-size:12.5px;font-weight:600;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .dsp-top .who{font-size:13.5px;font-weight:600;letter-spacing:.005em;text-transform:none}
html[data-skin="lab"] .exh b{font-weight:600;letter-spacing:.005em}
html[data-skin="lab"] .pairrow .v{font-family:var(--mono);font-size:26px;font-weight:400;letter-spacing:-.02em;font-variant-numeric:tabular-nums}

/* provenance tags: same four modes, inks that read on white */
html[data-skin="lab"] .tag,html[data-skin="lab"] .exk{letter-spacing:.06em;font-weight:600}
html[data-skin="lab"] .tag.live,html[data-skin="lab"] .k-mech,html[data-skin="lab"] .dlog-check .r.ok{background:rgba(45,122,74,.12);color:#21673E}
html[data-skin="lab"] .tag.sim,html[data-skin="lab"] .k-ins{background:rgba(110,75,192,.11);color:#5A3CA8}
html[data-skin="lab"] .tag.arch,html[data-skin="lab"] .k-obj{background:rgba(11,110,150,.10);color:#0A6584}
html[data-skin="lab"] .tag.ft,html[data-skin="lab"] .k-num,html[data-skin="lab"] .dlog-check .r.diff{background:rgba(168,90,23,.12);color:#8F4C12}
html[data-skin="lab"] .tag.wait,html[data-skin="lab"] .dlog-check .r.note{background:rgba(84,98,111,.12);color:#54626F}
html[data-skin="lab"] .tag.ref{background:rgba(19,32,43,.06);color:var(--ink2)}
html[data-skin="lab"] .tag.nil{background:rgba(84,98,111,.10);color:var(--ink3)}

/* controls: sentence case, filled selection, softer corners */
html[data-skin="lab"] .modebar{border-radius:4px;background:var(--line2);border-color:var(--line2)}
html[data-skin="lab"] .modebar button,html[data-skin="lab"] .hemi button{font-size:11px;font-weight:500;letter-spacing:.01em;text-transform:none;padding:4px 11px;background:var(--panel)}
html[data-skin="lab"] .modebar button[aria-pressed="true"],html[data-skin="lab"] .hemi button[aria-pressed="true"]{background:var(--ice);color:#fff}
html[data-skin="lab"] .gctl button{border-radius:4px;background:var(--panel)}
/* HUD buttons can sit over the dark planet, so a pressed tint goes on an opaque panel, never on what is behind */
html[data-skin="lab"] .gctl button[aria-pressed="true"]{background:linear-gradient(rgba(11,110,150,.12),rgba(11,110,150,.12)),var(--panel);color:var(--ice);border-color:var(--ice)}
html[data-skin="lab"] .feat .acts button,html[data-skin="lab"] .dsp .acts button,html[data-skin="lab"] .dlog-acts button,html[data-skin="lab"] .dlog-tabs button{font-size:11.5px;font-weight:500;letter-spacing:.01em;text-transform:none}
html[data-skin="lab"] .feat .acts button,html[data-skin="lab"] .dsp .acts button,html[data-skin="lab"] .dlog-acts button,
html[data-skin="lab"] .tbtn,html[data-skin="lab"] .tp .spd,html[data-skin="lab"] .dlog-step button,html[data-skin="lab"] .dlog-x,
html[data-skin="lab"] .dlog-tabs,html[data-skin="lab"] .dlog-sers button,html[data-skin="lab"] .hemi,html[data-skin="lab"] .legend,
html[data-skin="lab"] .mapkey,html[data-skin="lab"] .prov,html[data-skin="lab"] .tt,html[data-skin="lab"] .exbox,html[data-skin="lab"] .avatar{border-radius:4px}
html[data-skin="lab"] .dsp .acts button.pri,html[data-skin="lab"] .dlog-acts button.pri{background:var(--ice);border-color:var(--ice);color:#fff}
html[data-skin="lab"] .lay.on .sw,html[data-skin="lab"] .learn[aria-pressed="true"] .sw{background:var(--ice);border-color:var(--ice)}
html[data-skin="lab"] .lay.on .sw::after,html[data-skin="lab"] .learn[aria-pressed="true"] .sw::after{background:#fff}
html[data-skin="lab"] .meter .fill{background:linear-gradient(90deg,#0B6E96,#1388AE)}

/* lists and tables */
html[data-skin="lab"] .stn,html[data-skin="lab"] .evt,html[data-skin="lab"] table.dlt td{border-bottom-color:var(--line)}
html[data-skin="lab"] table.dlt tr.grp td{background:var(--panel2)}
html[data-skin="lab"] table.dlt tr.cur td{background:rgba(11,110,150,.07)}

/* the featured event */
html[data-skin="lab"] .feat{background:linear-gradient(180deg,rgba(168,74,26,.06),rgba(168,74,26,0) 70%)}
html[data-skin="lab"] .feat h3{font-size:24px;font-weight:600;letter-spacing:-.005em;text-transform:none;color:#A2481B}
html[data-skin="lab"] .feat .fk .tag{background:rgba(168,74,26,.11);color:#8F3F15}
html[data-skin="lab"] .feat .out{border-left-color:rgba(168,74,26,.5)}

/* floating furniture */
html[data-skin="lab"] .exbox{background:rgba(255,255,255,.98);box-shadow:0 8px 28px rgba(19,32,43,.16)}
html[data-skin="lab"] .tt{background:var(--panel);box-shadow:0 4px 14px rgba(19,32,43,.14)}

/* the map: the planet on a pale light table, ruled at 24 px. The HUD sits on
   the field in one place and on the dark planet in another, so in Lab its text
   rides on light plates that read on both. */
html[data-skin="lab"] .mapwrap{background:
  radial-gradient(rgba(19,32,43,.075) 1px,transparent 1.3px) 12px 12px/24px 24px,
  radial-gradient(ellipse at 50% 46%,var(--field-hi) 0,var(--field) 78%)}
html[data-skin="lab"] .hud .readout:not(:empty),html[data-skin="lab"] .hud .gctl>span:not(:empty),
html[data-skin="lab"] .hud .scale{background:var(--plate);padding:1px 5px;border-radius:3px}
html[data-skin="lab"] .hud .prov{background:var(--panel)}
html[data-skin="lab"] .legend,html[data-skin="lab"] .mapkey{background:var(--plate);border-color:var(--line)}
/* the current-colour legend uses the ramp's own colours, which are made for the
   dark sea they are drawn on; each sits on a chip of that sea so it reads as drawn */
html[data-skin="lab"] #flowNote span{background:var(--sea);padding:0 4px;border-radius:2px}
</style>'''

# ---------------------------------------------------------------- edits
def build_edits(default, title):
    ops_pairs, edits, seen = [], [], set()
    for anchor, key, lit in CANVAS:
        assert lit in anchor, (key, "literal not inside its own anchor")
        edits.append((anchor, anchor.replace(lit, "TH." + key, 1), "canvas:" + key))
        if key not in seen:
            ops_pairs.append(key + ":" + lit); seen.add(key)
    assert set(LAB) - {"halo"} == seen, "Lab and Ops skins carry different keys"
    lab_pairs = ",\n    ".join(k + ":" + v for k, v in LAB.items())
    core = (JS_CORE.replace("__OPS__", ",\n    ".join(ops_pairs))
                   .replace("__LAB__", lab_pairs))

    A_DOLLAR = 'const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];'
    edits += [
        (A_DOLLAR, A_DOLLAR + "\n" + core, "js:skin-core"),
        ('new ResizeObserver(()=>{ drawTL(); }).observe(tl);',
         'new ResizeObserver(()=>{ drawTL(); }).observe(tl);' + JS_BOOT, "js:skin-boot"),
        ('  g.save(); g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();\n  const og=g.createRadialGradient(cx-s*0.25',
         '  skinHalo(g,cx,cy,s);\n  g.save(); g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();\n  const og=g.createRadialGradient(cx-s*0.25',
         "canvas:halo-globe"),
        ('  g.save(); g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();\n  const og=g.createRadialGradient(cx,cy,0,cx,cy,s);',
         '  skinHalo(g,cx,cy,s);\n  g.save(); g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();\n  const og=g.createRadialGradient(cx,cy,0,cx,cy,s);',
         "canvas:halo-disc"),
        ('@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}\n</style>',
         '@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}\n</style>' + CSS,
         "css:skin-lab"),
        ('<title>Olympus Deck</title>',
         '<title>' + title + '</title>\n' + BOOT_TAG.replace("__DEFAULT__", default), "html:boot"),
        ('title="Deck log (L)"><svg class="glyph" viewBox="0 0 10 10" aria-hidden="true"><path d="M1 1.5h8M1 4h8M1 6.5h8M1 9h5" stroke="currentColor" stroke-width="1.1" fill="none"/></svg>Log</button>',
         'title="Deck log (L)"><svg class="glyph" viewBox="0 0 10 10" aria-hidden="true"><path d="M1 1.5h8M1 4h8M1 6.5h8M1 9h5" stroke="currentColor" stroke-width="1.1" fill="none"/></svg>Log</button>' + SKIN_BUTTONS,
         "html:switch"),
        ('<svg class="sigil" viewBox="0 0 24 24" aria-hidden="true" fill="none">',
         '<svg class="sigil sg-ops" viewBox="0 0 24 24" aria-hidden="true" fill="none">', "html:sigil-ops"),
        ('<circle cx="12" cy="12" r="1.5" fill="#7FE3F5"/>\n      </svg>',
         '<circle cx="12" cy="12" r="1.5" fill="#7FE3F5"/>\n      </svg>' + SIGIL_LAB, "html:sigil-lab"),
    ]
    return edits

WRAP_HEAD = re.compile(r'^<!doctype html><html><head><meta charset=utf8>.*?</head><body>\n?', re.S)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--default", choices=["ops", "lab"], default="ops")
    ap.add_argument("--title", default="Olympus Deck")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    s = open(a.src, encoding="utf-8", newline="").read()
    if 'data-skin' in s:
        sys.exit("ABORT: input already carries a skin (data-skin found); patch the unskinned deck")
    m = WRAP_HEAD.match(s)
    if m:
        s = s[m.end():]
        if s.endswith("</body></html>"): s = s[:-len("</body></html>")]
        print("stripped host document skeleton")

    # Applied in order to a working copy, each anchor counted at its own turn, so
    # an edit that disturbs a later anchor is caught too. Nothing is written
    # unless every one of them matched exactly once.
    edits = build_edits(a.default, a.title)
    bad, w = [], s
    for old, new, name in edits:
        n = w.count(old)
        print(f"  {name:22s} matches={n}")
        if n != 1: bad.append((name, n)); continue
        w = w.replace(old, new, 1)
    if bad:
        sys.exit("ABORT: anchors not matched exactly once: " + ", ".join(f"{n}={c}" for n, c in bad))
    if a.dry_run:
        print("dry run: all anchors unique, nothing written"); return
    s = w
    open(a.out, "w", encoding="utf-8", newline="").write(s)
    print(f"wrote {a.out}  {len(s.encode('utf-8')):,} bytes  default={a.default}  sha256={hashlib.sha256(s.encode('utf-8')).hexdigest()[:16]}")

if __name__ == "__main__":
    main()
