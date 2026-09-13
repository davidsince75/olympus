"""
patch_disc_zoom — give the polar views a camera, and both views a visible one.

The Antarctic and Arctic views had no zoom at all. The disc was fitted to the
panel and that was the whole of it, so the Weddell polynyas, the Canadian
archipelago and every ice edge the deck exists to show were permanently a few
pixels across. The globe had zoom but no way to see it: a wheel, a pinch and a
double-click, none of them announced, and no reading of where you were.

Zoom alone would not have been enough for a disc. A polar stereographic view is
centred on the pole, so magnifying it without being able to move sideways only
magnifies the pole - the one part of the picture with no ice edge in it. So the
disc pans as well, clamped so that the disc can always be found again.

Ten substitutions, each anchored on an exact string that must match exactly once
or the script aborts without writing.

  1  DISC camera state       zoom, pan, limits
  2  camStep                 ease the disc zoom the way the globe's is eased
  3  discZoom / discClamp    anchored zoom, and the clamp that keeps the disc findable
  4  drawMap                 the disc branch reads the camera
  5  wheel                   discs zoom on the wheel, anchored at the pointer
  6  dblclick                discs zoom in on a double-click
  7  keydown                 arrows pan, +/- zoom, 0 resets, in every view
  8  discDrag                drag to pan, pinch to zoom
  9  #zoomBar                the control: minus, per cent, plus, reset
 10  modeUI / frame / copy   show it where it applies, keep the number current

Usage
    python3 build/patch_disc_zoom.py --deck src/deck.html --out dist/deck.html
"""

import argparse
import io
import os
import sys

EDITS = []


def sub(label, old, new):
    EDITS.append((label, old, new))


# ------------------------------------------------------------ 1. camera state
sub("DISC camera state",
"""const CAM_ZMIN=1, CAM_ZMAX=3.6;
const CAM_IDLE_MS=14000;   // before the globe starts turning on its own
const CAM_AUTO_DPS=1.6;    // deg per second of idle drift""",
"""const CAM_ZMIN=1, CAM_ZMAX=3.6;
const CAM_IDLE_MS=14000;   // before the globe starts turning on its own
const CAM_AUTO_DPS=1.6;    // deg per second of idle drift

/* The disc camera. A polar stereographic view is centred on the pole, so a zoom
   with no pan only magnifies the pole, which is the one part of the picture with
   no ice edge in it. Hence x and y as well as z.

   The ceiling is 6x rather than the globe's 3.6x because a disc has further to
   go before it runs out of data: the ice field is a 25 km grid and the imagery a
   1180-pixel square, and past about 3x both are simply drawn larger. That is a
   property of the observation and the deck says so in the explainer rather than
   pretending the limit is somewhere else. */
const DISC={z:1, zTarget:1, x:0, y:0, drag:false};
const DISC_ZMIN=1, DISC_ZMAX=6;
function discView(){ return st.mode==="S" || st.mode==="N"; }""")

# ----------------------------------------------------------------- 2. camStep
sub("camStep eases the disc",
"""function camStep(dt){
  CAM.dt = CAM.dt*0.9 + Math.min(0.25, dt)*0.1;
  if(st.mode!=="GLOBE") return;""",
"""function camStep(dt){
  CAM.dt = CAM.dt*0.9 + Math.min(0.25, dt)*0.1;
  // the disc eases toward its target for the same reason the globe does: a
  // wheel notch should not be a jump
  if(discView() && Math.abs(DISC.zTarget-DISC.z)>0.0005){
    DISC.z += (DISC.zTarget-DISC.z)*Math.min(1, dt*11);
  }
  if(st.mode!=="GLOBE") return;""")

# --------------------------------------------------------- 3. the disc's zoom
sub("discZoom and discClamp",
"""function camZoom(f,anchor){
  CAM.zTarget=Math.max(CAM_ZMIN, Math.min(CAM_ZMAX, CAM.zTarget*f));
  camTouch();
}""",
"""function camZoom(f,anchor){
  CAM.zTarget=Math.max(CAM_ZMIN, Math.min(CAM_ZMAX, CAM.zTarget*f));
  camTouch();
}

/* Zoom about a point rather than about the middle of the panel: the thing under
   the pointer is the thing you meant to look at, and it should stay where it is
   while everything else moves away from it. ax, ay are measured from the centre
   of the panel, which is where the disc sits when the pan is zero. */
function discZoom(f, ax, ay){
  const z0=DISC.zTarget;
  const z=Math.max(DISC_ZMIN, Math.min(DISC_ZMAX, z0*f));
  if(z===z0) return;
  if(ax!==undefined){
    const k=z/z0;
    DISC.x = ax - (ax-DISC.x)*k;
    DISC.y = ay - (ay-DISC.y)*k;
  }
  DISC.zTarget=z;
}
function discReset(){ DISC.zTarget=1; DISC.x=0; DISC.y=0; }

/* The pan is clamped to (z-1) disc radii, so at any magnification the rim is
   still reachable and the disc can never be pushed off the panel and lost. At
   z = 1 that is zero, which is why the unzoomed view cannot be dragged askew. */
function discClamp(s0){
  const lim=Math.max(0,(DISC.z-1))*s0;
  const m=Math.hypot(DISC.x,DISC.y);
  if(m>lim && m>0){ DISC.x*=lim/m; DISC.y*=lim/m; }
}

function zoomOf(){
  return st.mode==="GLOBE" ? CAM.zoom : (discView() ? DISC.z : 1);
}
function zoomBy(f){
  if(st.mode==="GLOBE") camZoom(f);
  else if(discView()) discZoom(f);
}
function zoomReset(){
  if(st.mode==="GLOBE"){ CAM.zTarget=1; camTouch(); }
  else discReset();
}""")

# ----------------------------------------------------------------- 4. drawMap
sub("drawMap reads the disc camera",
"""  } else {
    const S=st.mode==="S";
    const s=Math.min(w,h)/2*0.93, cx=w/2, cy=h/2;
    st.discs=[{cx,cy,s,S}];
    st.cx=cx; st.cy=cy; st.s=s;
    drawDisc(g,cx,cy,s,S,false);
  }""",
"""  } else {
    const S=st.mode==="S";
    const s0=Math.min(w,h)/2*0.93;
    discClamp(s0);                       // clamped here, where the panel size is known
    const s=s0*DISC.z, cx=w/2+DISC.x, cy=h/2+DISC.y;
    st.discs=[{cx,cy,s,S}];
    st.cx=cx; st.cy=cy; st.s=s;
    drawDisc(g,cx,cy,s,S,false);
  }""")

# ------------------------------------------------------------------- 5. wheel
sub("wheel zooms the disc too",
"""  map.addEventListener("wheel",e=>{
    if(st.mode!=="GLOBE") return;
    e.preventDefault();
    camZoom(Math.exp(-e.deltaY*(e.deltaMode===1?0.03:0.0016)));
  },{passive:false});""",
"""  map.addEventListener("wheel",e=>{
    const f=Math.exp(-e.deltaY*(e.deltaMode===1?0.03:0.0016));
    if(st.mode==="GLOBE"){ e.preventDefault(); camZoom(f); return; }
    if(!discView()) return;
    e.preventDefault();
    const r=map.getBoundingClientRect();
    discZoom(f, e.clientX-r.left-r.width/2, e.clientY-r.top-r.height/2);
  },{passive:false});""")

# ---------------------------------------------------------------- 6. dblclick
sub("dblclick zooms the disc too",
"""  map.addEventListener("dblclick",e=>{ if(st.mode==="GLOBE") camZoom(1.6); });""",
"""  map.addEventListener("dblclick",e=>{
    if(st.mode==="GLOBE"){ camZoom(1.6); return; }
    if(!discView()) return;
    const r=map.getBoundingClientRect();
    discZoom(1.6, e.clientX-r.left-r.width/2, e.clientY-r.top-r.height/2);
  });""")

# ----------------------------------------------------------------- 7. keyboard
sub("keyboard reaches both cameras",
"""  map.addEventListener("keydown",e=>{
    if(st.mode!=="GLOBE") return;
    const step=e.shiftKey?12:4;
    if(e.key==="ArrowLeft")  { setCam(st.glat, st.glon-step); camTouch(); }
    else if(e.key==="ArrowRight"){ setCam(st.glat, st.glon+step); camTouch(); }
    else if(e.key==="ArrowUp")   { setCam(st.glat+step, st.glon); camTouch(); }
    else if(e.key==="ArrowDown") { setCam(st.glat-step, st.glon); camTouch(); }
    else if(e.key==="+"||e.key==="="){ camZoom(1.25); }
    else if(e.key==="-"||e.key==="_"){ camZoom(1/1.25); }
    else if(e.key==="0"){ CAM.zTarget=1; camTouch(); }
    else return;
    e.preventDefault();
  });""",
"""  map.addEventListener("keydown",e=>{
    if(st.mode==="GLOBE"){
      const step=e.shiftKey?12:4;
      if(e.key==="ArrowLeft")  { setCam(st.glat, st.glon-step); camTouch(); }
      else if(e.key==="ArrowRight"){ setCam(st.glat, st.glon+step); camTouch(); }
      else if(e.key==="ArrowUp")   { setCam(st.glat+step, st.glon); camTouch(); }
      else if(e.key==="ArrowDown") { setCam(st.glat-step, st.glon); camTouch(); }
      else if(e.key==="+"||e.key==="="){ camZoom(1.25); }
      else if(e.key==="-"||e.key==="_"){ camZoom(1/1.25); }
      else if(e.key==="0"){ CAM.zTarget=1; camTouch(); }
      else return;
      e.preventDefault(); return;
    }
    if(!discView()) return;
    // on a disc the arrows pan, because there is nothing to orbit
    const step=(e.shiftKey?0.22:0.08)*st.s;
    if(e.key==="ArrowLeft")  { DISC.x+=step; }
    else if(e.key==="ArrowRight"){ DISC.x-=step; }
    else if(e.key==="ArrowUp")   { DISC.y+=step; }
    else if(e.key==="ArrowDown") { DISC.y-=step; }
    else if(e.key==="+"||e.key==="="){ discZoom(1.25); }
    else if(e.key==="-"||e.key==="_"){ discZoom(1/1.25); }
    else if(e.key==="0"){ discReset(); }
    else return;
    e.preventDefault();
  });""")

# ----------------------------------------------------------------- 8. discDrag
sub("discDrag",
"""/* ---------------- readouts ---------------- */
const MON=""",
"""/* Drag to pan, pinch to zoom, on the polar discs. Separate from globeDrag
   because the two cameras have nothing in common: one turns a sphere and carries
   angular momentum, this one slides a flat picture and stops when you stop. */
(function discDrag(){
  const pts=new Map();
  let px=0,py=0,id=null,pinch=0;
  const dist=()=>{ const a=[...pts.values()]; return a.length<2?0:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y); };

  map.addEventListener("pointerdown",e=>{
    if(!discView()) return;
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pts.size===2){ pinch=dist(); DISC.drag=false; return; }
    id=e.pointerId; px=e.clientX; py=e.clientY; DISC.drag=true;
    try{ map.setPointerCapture(id); }catch(err){}
  });

  map.addEventListener("pointermove",e=>{
    if(!pts.has(e.pointerId)) return;
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pts.size>=2){
      const d=dist();
      if(pinch>4 && d>4){ discZoom(d/pinch); pinch=d; }
      return;
    }
    if(!DISC.drag || e.pointerId!==id) return;
    // a pan at z = 1 is clamped to nothing, so an unzoomed disc cannot be
    // dragged askew by a stray gesture
    DISC.x += e.clientX-px; DISC.y += e.clientY-py;
    px=e.clientX; py=e.clientY;
  });

  const end=e=>{
    if(e) pts.delete(e.pointerId);
    if(pts.size<2) pinch=0;
    if(!e || e.pointerId===id) DISC.drag=false;
  };
  map.addEventListener("pointerup",end);
  map.addEventListener("pointercancel",end);
  map.addEventListener("pointerleave",e=>{ if(pts.size) end(e); });
})();

/* ---------------- readouts ---------------- */
const MON=""")

# ---------------------------------------------------------------- 9. the control
sub("zoomBar markup",
"""          <div class="br">
            <div class="scale"><span id="scalelab">1000 km</span><span class="scalebar"></span></div>""",
"""          <div class="br">
            <div class="gctl" id="zoomBar" role="group" aria-label="Zoom"
                 style="justify-content:flex-end;margin:0 0 6px">
              <button data-zoom="out" aria-label="Zoom out" data-ex="zoom_pan">&minus;</button>
              <span id="zoomPct" style="color:var(--ink2);letter-spacing:.04em;min-width:40px;text-align:center;font-variant-numeric:tabular-nums">100%</span>
              <button data-zoom="in" aria-label="Zoom in" data-ex="zoom_pan">+</button>
              <button data-zoom="reset" data-ex="zoom_pan">Reset</button>
            </div>
            <div class="scale"><span id="scalelab">1000 km</span><span class="scalebar"></span></div>""")

sub("zoomBar narrow-panel rule",
"""@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}""",
"""/* The zoom control shares the bottom-right corner with the scale bar, and on a
   narrow panel the bottom-left legend reaches across far enough to meet it —
   measured at 430 px, where the two boxes overlap. Reset has a keyboard key and
   a double-click; the corner keeps the two controls that have neither. */
@media (max-width:720px){
  #zoomBar{gap:4px}
  #zoomBar button[data-zoom="reset"]{display:none}
  #zoomPct{min-width:34px!important}
}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}""")

sub("zoomBar wiring",
"""$$("#globeCtl button").forEach(b=>b.addEventListener("click",()=>{""",
"""$$("#zoomBar button").forEach(b=>b.addEventListener("click",()=>{
  const k=b.dataset.zoom;
  if(k==="in") zoomBy(1.35); else if(k==="out") zoomBy(1/1.35); else zoomReset();
  map.focus({preventScroll:true});
}));
$$("#globeCtl button").forEach(b=>b.addEventListener("click",()=>{""")

# --------------------------------------------------------- 10. modeUI, frame, copy
sub("modeUI shows the zoom bar",
"""  $("#globeCtl").hidden = st.mode!=="GLOBE";""",
"""  $("#globeCtl").hidden = st.mode!=="GLOBE";
  // Both is a comparison of two fitted discs; magnifying one of them would make
  // it a comparison of two different things
  { const zb=$("#zoomBar"); if(zb) zb.hidden = st.mode==="PAIR"; }""")

sub("frame keeps the per cent current",
"""  drawMap();
  if(st.mode==="GLOBE" && st.gDrag) sync();""",
"""  drawMap();
  { const t=Math.round(zoomOf()*100)+"%";
    if(t!==st._zpct){ st._zpct=t; const el=$("#zoomPct"); if(el) el.textContent=t; } }
  if(st.mode==="GLOBE" && st.gDrag) sync();""")

sub("zoom_pan explainer",
"""mode_globe:{k:"obj",t:"The globe",""",
"""zoom_pan:{k:"obj",t:"Zoom and pan",
 b:"Scroll or pinch to zoom, drag to pan, double-click to zoom in, arrow keys to move, <b>0</b> to reset. The polar views go to <b>6\\u00d7</b> and the globe to 3.6\\u00d7. What magnification cannot do is add detail that was never measured: the ice field is a <b>25 km</b> grid and the imagery a 1180-pixel square, so past about three times you are looking at the same observations drawn larger, not at more of them. The scale bar, the cursor position and the concentration readout stay right at every magnification, because all three are computed from the projection rather than from the picture.",
 p:"Magnification is a property of the view. The resolution is a property of the instrument."},
mode_globe:{k:"obj",t:"The globe",""")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = io.open(args.deck, encoding="utf-8").read()
    print(f"in  {args.deck}  {len(src)/1024/1024:.2f} MB")
    for label, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected exactly one match, found {n}")
        src = src.replace(old, new)
        print(f"  {label}: applied")

    if args.dry_run:
        print("dry run — nothing written")
        return
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        f.write(src)
    size = os.path.getsize(args.out)
    print(f"out {args.out}  {size/1024/1024:.2f} MB")
    if size > 16 * 1024 * 1024:
        print("WARNING: over the 16 MB artifact ceiling", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
