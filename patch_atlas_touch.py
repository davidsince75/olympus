#!/usr/bin/env python3
"""
patch_atlas_touch.py — give the Atlas map working pan and pinch on touch.

Run from the repo root:

    python patch_atlas_touch.py dist/atlas.html

Writes dist/atlas.html.bak first. Every anchor must match exactly once or the
script aborts having changed nothing.

WHAT IS ACTUALLY WRONG
----------------------
The surface already uses pointerdown/pointerup/pointercancel, and canvas#map
already carries touch-action:none. Both were fine. The defect is that drag
MOVEMENT is handled by a "mousemove" listener while press and release are on
Pointer Events. iOS Safari synthesises a compatibility mouse sequence for a tap
but never fires mousemove during a touch drag, so st.drag is set on pointerdown
and then never updated — the map does not pan, while tap-to-select keeps working.
Separately there is no pinch handling at all: zoom is bound to "wheel", which
iOS does not fire for a pinch.

WHAT THIS CHANGES
-----------------
1. st gains `ptrs` (active contacts) and `pinch` (gesture state).
2. "mousemove" becomes "pointermove", with a two-contact branch that zooms about
   the pinch midpoint and pans by the midpoint's travel.
3. The hover branch returns early for touch contacts, which have no hover state.
4. "mouseleave" becomes "pointerleave" so it still fires for a mouse.
5. pointerdown tracks contacts; a second contact converts a pan into a pinch.
6. pointerup ends the pinch, re-seats a surviving contact as a pan origin, and
   decides tap-vs-drag on DISPLACEMENT FROM THE DOWN POINT rather than on
   accumulated path length, with a larger threshold for touch. This part matters:
   before this patch no pointermove fired on touch, so `moved` stayed 0 and every
   touch read as a tap. Once pointermove fires, accumulated jitter would have
   pushed a fingertip tap past the 4 px limit and broken the one thing that
   currently works on iPad.
7. pointercancel clears per-pointer state instead of only st.drag.

NOT ADDRESSED HERE
------------------
The Deck has no pan or zoom on any platform — nothing to fix, it was never built
(expansion plan B1). Hit-target radii are unchanged and may be tight for a
fingertip; that is a separate judgement about HOT.
"""

import sys
import os

PATCHES = [
    (
        "state: track active contacts and pinch",
        'zoom:{S:1, N:1}, pan:{S:{x:0,y:0}, N:{x:0,y:0}}, drag:null',
        'zoom:{S:1, N:1}, pan:{S:{x:0,y:0}, N:{x:0,y:0}}, drag:null,\n'
        '  ptrs:new Map(), pinch:null',
    ),
    (
        "movement onto pointermove, with a pinch branch",
        'map.addEventListener("mousemove", ev=>{\n'
        '  const r = map.getBoundingClientRect(), mx = ev.clientX-r.left, my = ev.clientY-r.top;\n'
        '  if(st.drag){',

        'map.addEventListener("pointermove", ev=>{\n'
        '  const r = map.getBoundingClientRect(), mx = ev.clientX-r.left, my = ev.clientY-r.top;\n'
        '  if(st.ptrs.has(ev.pointerId)) st.ptrs.set(ev.pointerId, {x:mx, y:my});\n'
        '  // two contacts: zoom about the midpoint, and pan by the midpoint\'s travel\n'
        '  if(st.pinch && st.ptrs.size>=2){\n'
        '    const p = [...st.ptrs.values()].slice(0,2);\n'
        '    const nd = Math.hypot(p[0].x-p[1].x, p[0].y-p[1].y);\n'
        '    const cx = (p[0].x+p[1].x)/2, cy = (p[0].y+p[1].y)/2;\n'
        '    const key = st.pinch.S?"S":"N";\n'
        '    let dd = discFor(st.pinch.S);\n'
        '    if(dd){\n'
        '      st.pan[key].x -= (cx-st.pinch.cx)/(dd.r*dd.z);\n'
        '      st.pan[key].y += (cy-st.pinch.cy)/(dd.r*dd.z);\n'
        '      layout(); draw();\n'
        '      dd = discFor(st.pinch.S);\n'
        '      if(dd && st.pinch.d>0 && nd>0) zoomAt(dd, nd/st.pinch.d, cx, cy);\n'
        '    }\n'
        '    st.pinch.d = nd; st.pinch.cx = cx; st.pinch.cy = cy;\n'
        '    $("#tip").style.opacity = 0;\n'
        '    ev.preventDefault();\n'
        '    return;\n'
        '  }\n'
        '  if(st.drag){',
    ),
    (
        "no hover state for a touch contact",
        '  const h = hit(mx,my), tip = $("#tip");',
        '  // a touch contact has no hover state; the tooltip and the cursor lat/lon\n'
        '  // readout are for pointing devices only\n'
        '  if(ev.pointerType === "touch"){ return; }\n'
        '  const h = hit(mx,my), tip = $("#tip");',
    ),
    (
        "mouseleave -> pointerleave",
        'map.addEventListener("mouseleave", ()=>{ $("#tip").style.opacity=0; });',
        'map.addEventListener("pointerleave", ()=>{ $("#tip").style.opacity=0; });',
    ),
    (
        "pointerdown: track contacts, second contact starts a pinch",
        'map.addEventListener("pointerdown", ev=>{\n'
        '  const r = map.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;\n'
        '  st.drag = {mx, my, moved:0, d:discAt(mx), px:0, py:0};\n'
        '  map.setPointerCapture(ev.pointerId);\n'
        '});',

        'map.addEventListener("pointerdown", ev=>{\n'
        '  const r = map.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;\n'
        '  st.ptrs.set(ev.pointerId, {x:mx, y:my});\n'
        '  if(st.ptrs.size === 1){\n'
        '    st.drag = {mx, my, ox:mx, oy:my, moved:0, d:discAt(mx), px:0, py:0};\n'
        '  } else if(st.ptrs.size === 2){\n'
        '    // a second contact means pinch, not pan\n'
        '    st.drag = null;\n'
        '    const p = [...st.ptrs.values()].slice(0,2);\n'
        '    const cx = (p[0].x+p[1].x)/2, cy = (p[0].y+p[1].y)/2;\n'
        '    const d0 = discAt(cx);\n'
        '    st.pinch = {d:Math.hypot(p[0].x-p[1].x, p[0].y-p[1].y), cx, cy, S:d0?d0.S:false};\n'
        '    $("#tip").style.opacity = 0;\n'
        '  }\n'
        '  try { map.setPointerCapture(ev.pointerId); } catch(e){}\n'
        '});',
    ),
    (
        "pointerup: end pinch, re-seat survivor, tap by displacement",
        'map.addEventListener("pointerup", ev=>{\n'
        '  const r = map.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;\n'
        '  const moved = st.drag ? st.drag.moved : 99;\n'
        '  st.drag = null;\n'
        '  if(moved < 4){ const h = hit(mx,my); select(h ? h.id : null); }\n'
        '});',

        'map.addEventListener("pointerup", ev=>{\n'
        '  const r = map.getBoundingClientRect(), mx=ev.clientX-r.left, my=ev.clientY-r.top;\n'
        '  const wasPinch = !!st.pinch;\n'
        '  st.ptrs.delete(ev.pointerId);\n'
        '  try { map.releasePointerCapture(ev.pointerId); } catch(e){}\n'
        '  if(st.ptrs.size < 2) st.pinch = null;\n'
        '  if(st.ptrs.size > 0){\n'
        '    // a contact lifted out of a pinch: re-seat the survivor as a pan origin.\n'
        '    // noTap so that lifting it cannot be read as a selection.\n'
        '    const p = [...st.ptrs.values()][0];\n'
        '    st.drag = {mx:p.x, my:p.y, ox:p.x, oy:p.y, moved:0, noTap:true, d:discAt(p.x), px:0, py:0};\n'
        '    return;\n'
        '  }\n'
        '  const dr = st.drag;\n'
        '  st.drag = null;\n'
        '  if(wasPinch || !dr || dr.noTap) return;\n'
        '  // tap vs drag on displacement from the down point, not path length: a\n'
        '  // fingertip wanders more than a mouse and accumulates jitter either way\n'
        '  const lim = (ev.pointerType === "touch") ? 10 : 4;\n'
        '  if(Math.hypot(mx-dr.ox, my-dr.oy) < lim){ const h = hit(mx,my); select(h ? h.id : null); }\n'
        '});',
    ),
    (
        "pointercancel: clear per-pointer state",
        'map.addEventListener("pointercancel", ()=>{ st.drag=null; });',
        'map.addEventListener("pointercancel", ev=>{\n'
        '  if(ev && ev.pointerId != null) st.ptrs.delete(ev.pointerId); else st.ptrs.clear();\n'
        '  if(st.ptrs.size < 2) st.pinch = null;\n'
        '  if(st.ptrs.size === 0) st.drag = null;\n'
        '});',
    ),
]


def variants(s):
    """(LF form, CRLF form) of a string, in that order."""
    lf = s.replace("\r\n", "\n")
    return lf, lf.replace("\n", "\r\n")


def resolve(old, new, text):
    """
    Pick the line-ending form of `old` that occurs exactly once in `text`.
    Returns (old_form, new_form, label) or (None, None, reason).

    A per-anchor decision, not a whole-file one: a file can hold a stray CR
    somewhere harmless (a trailing newline written by another tool, say) while
    every line in the region being patched is LF. Deciding globally off
    `"\\r\\n" in text` misreads that and breaks every multi-line anchor.
    """
    o_lf, o_crlf = variants(old)
    n_lf, n_crlf = variants(new)
    hits = []
    if text.count(o_lf) == 1:
        hits.append((o_lf, n_lf, "LF"))
    if o_crlf != o_lf and text.count(o_crlf) == 1:
        hits.append((o_crlf, n_crlf, "CRLF"))
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return None, None, "ambiguous: matches in both LF and CRLF form"
    n = text.count(o_lf) + (text.count(o_crlf) if o_crlf != o_lf else 0)
    if n == 0 and (n_lf in text or n_crlf in text):
        return None, None, "already applied"
    return None, None, "matched %d times (expected 1)" % n


def main():
    if len(sys.argv) != 2:
        print("usage: patch_atlas_touch.py <path to atlas.html>")
        return 2
    path = sys.argv[1]
    if not os.path.isfile(path):
        print("ABORT: no such file: " + path)
        return 1

    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")

    # Dry run: every anchor must resolve to exactly one match before anything
    # is written.
    resolved = []
    problems = []
    for label, old, new in PATCHES:
        o, n, why = resolve(old, new, text)
        if o is None:
            problems.append("  %-52s %s" % (label, why))
        else:
            resolved.append((label, o, n, why))
    if problems:
        print("ABORT: file not changed.")
        print("\n".join(problems))
        return 1

    out = text
    for label, o, n, form in resolved:
        out = out.replace(o, n, 1)

    bak = path + ".bak"
    if not os.path.exists(bak):
        open(bak, "wb").write(raw)
        print("backup written: " + bak)
    else:
        print("backup already exists, left alone: " + bak)

    data = out.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    open(path, "wb").write(data)

    for label, o, n, form in resolved:
        print("  applied  %-52s [%s]" % (label, form))
    print("\n%d patches applied to %s" % (len(resolved), path))
    print("Next: node --check on the extracted script, then open on the iPad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
