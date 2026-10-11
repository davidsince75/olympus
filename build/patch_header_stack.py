#!/usr/bin/env python3
"""patch_header_stack.py — stack the deck's header controls into one block.

Before: three separately bordered groups of different widths in a row —
  [Log]  [Ops|Lab]  [Deck|Stations|Named Ice]
After: one block of six equal cells, two rows, filling the header's full height
and joined by the header's own hairlines:
  Deck | Stations | Named Ice      where you are (the surface switcher)
  Log  | Ops      | Lab            what you do here
DOM order follows the visual order, so keyboard focus runs row by row.

Equal widths come from the grid itself: three 1fr columns in a block sized to
its content resolve to the widest label, and both rows share those columns
through subgrid. In the 50 px header each row is 24.5 px, above the 24 px
minimum target; on a phone the block takes its own full-width row, 32 px tall.

Runs on the deck AFTER build/patch_skin_lab.py. It also retires the four Lab
rules that styled the old groups, since the block replaces them.

Convention: exact-string anchors, each must match exactly once, counted at its
own turn on a working copy; nothing is written unless all of them do.

usage: python patch_header_stack.py IN.html OUT.html [--dry-run]
"""
import argparse, hashlib, re, sys

LOG_RE  = re.compile(r'\n    <button type="button" class="logbtn" id="logBtn"[^\n]*?Log</button>')
SKIN_RE = re.compile(r'\n    <div class="skin" role="group" aria-label="Interface skin">.*?</div>')
NAV_RE  = re.compile(r'\n    <nav class="xnav" aria-label="Olympus surfaces" data-ex="surfaces">\n.*?\n</nav>\n', re.S)

LAB_OLD = '''html[data-skin="lab"] .xnav,html[data-skin="lab"] .logbtn,html[data-skin="lab"] .skin{background:var(--panel);border-radius:4px}
html[data-skin="lab"] .xnav a,html[data-skin="lab"] .logbtn,html[data-skin="lab"] .skin button{letter-spacing:.07em}
html[data-skin="lab"] .xnav a:hover,html[data-skin="lab"] .skin button:hover{background:rgba(11,110,150,.06)}
html[data-skin="lab"] .xnav a[aria-current=page],html[data-skin="lab"] .logbtn[aria-pressed="true"],html[data-skin="lab"] .skin button[aria-pressed="true"]{background:rgba(11,110,150,.10)}
'''
LAB_NEW = '''html[data-skin="lab"] .hdr .hctl a,html[data-skin="lab"] .hdr .hctl button{letter-spacing:.07em}
html[data-skin="lab"] .hdr .hctl a:hover,html[data-skin="lab"] .hdr .hctl button:hover{background-image:linear-gradient(rgba(11,110,150,.06),rgba(11,110,150,.06))}
html[data-skin="lab"] .hdr .hctl a[aria-current=page],html[data-skin="lab"] .hdr .hctl button[aria-pressed="true"]{background-image:linear-gradient(rgba(11,110,150,.10),rgba(11,110,150,.10))}
'''

CSS_ANCHOR = '#flowNote span{background:var(--sea);padding:0 4px;border-radius:2px}\n</style>'
CSS = '''
<style id="hdr-stack">
/* ---------- header controls: one block, six equal cells ----------
   Row 1 is where you are (the surfaces), row 2 is what you do here (log, skin).
   The cells are header furniture like the brand and the clock: full height,
   flush, separated by the same 1 px hairlines as everything else. */
.hdr .hctl{display:grid;grid-template-columns:repeat(3,1fr);grid-template-rows:repeat(2,minmax(24px,1fr));
  gap:1px;background:var(--line);border-right:1px solid var(--line);flex:0 0 auto;align-self:stretch}
.hdr .hctl .xnav,.hdr .hctl .skin{display:grid;grid-template-columns:subgrid;gap:1px;margin:0;border:0;border-radius:0;
  background:none;overflow:visible;align-self:stretch}
.hdr .hctl .xnav{grid-column:1/-1;grid-row:1}
.hdr .hctl .logbtn{grid-column:1;grid-row:2}
.hdr .hctl .skin{grid-column:2/-1;grid-row:2}
.hdr .hctl .xnav a,.hdr .hctl .logbtn,.hdr .hctl .skin button{display:flex;align-items:center;justify-content:center;gap:6px;
  margin:0;padding:0 14px;border:0;border-radius:0;align-self:stretch;
  background-color:var(--panel);background-image:none;
  font-family:var(--mono);font-size:9.5px;font-weight:400;letter-spacing:.15em;text-transform:uppercase;
  color:var(--ink3);white-space:nowrap;text-decoration:none}
.hdr .hctl .logbtn{color:var(--ink2)}
.hdr .hctl a:hover,.hdr .hctl button:hover{color:var(--ice);background-image:linear-gradient(rgba(15,165,190,.10),rgba(15,165,190,.10))}
.hdr .hctl a[aria-current=page],.hdr .hctl button[aria-pressed="true"]{color:var(--ice);background-image:linear-gradient(rgba(15,165,190,.16),rgba(15,165,190,.16))}
.hdr .hctl a:focus-visible,.hdr .hctl button:focus-visible{outline-offset:-2px}
@media (max-width:720px){
  .hdr .hctl{flex:1 1 100%;order:3;border-right:0;border-top:1px solid var(--line);grid-template-rows:repeat(2,32px)}
  .hdr .hctl .xnav a,.hdr .hctl .logbtn,.hdr .hctl .skin button{padding:0 8px;letter-spacing:.08em}
}
</style>'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    s = open(a.src, encoding="utf-8", newline="").read()
    if 'class="hctl"' in s: sys.exit("ABORT: header already stacked")
    if 'data-skin' not in s: sys.exit("ABORT: run build/patch_skin_lab.py first")

    bad, w = [], s
    def count(name, n):
        print(f"  {name:18s} matches={n}")
        if n != 1: bad.append((name, n))

    m_log, m_skin, m_nav = (list(r.finditer(w)) for r in (LOG_RE, SKIN_RE, NAV_RE))
    count("html:log", len(m_log)); count("html:skin", len(m_skin)); count("html:nav", len(m_nav))
    if not bad:
        L, K, N = m_log[0], m_skin[0], m_nav[0]
        if not (L.end() == K.start() and K.end() == N.start()):
            bad.append(("html:adjacent", 0)); print("  html:adjacent      the three groups are not side by side")
        else:
            nav = N.group(0).strip("\n")
            block = ('\n    <div class="hctl">\n    ' + nav + '\n    ' + L.group(0).strip("\n").strip()
                     + '\n    ' + K.group(0).strip("\n").strip() + '\n    </div>\n')
            w = w[:L.start()] + block + w[N.end():]
    for name, old, new in [("css:lab-retire", LAB_OLD, LAB_NEW), ("css:hdr-stack", CSS_ANCHOR, CSS_ANCHOR + CSS)]:
        n = w.count(old); count(name, n)
        if n == 1: w = w.replace(old, new, 1)
    if bad: sys.exit("ABORT: " + ", ".join(f"{n}={c}" for n, c in bad))
    if a.dry_run: print("dry run: all anchors unique, nothing written"); return
    open(a.out, "w", encoding="utf-8", newline="").write(w)
    b = w.encode("utf-8")
    print(f"wrote {a.out}  {len(b):,} bytes  sha256={hashlib.sha256(b).hexdigest()[:16]}")

if __name__ == "__main__":
    main()
