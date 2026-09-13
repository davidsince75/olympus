#!/usr/bin/env python3
"""
Olympus — rebuild the thermohaline layer of dist/deck.html.

Exact-string anchors, each required to match exactly once or the whole run
aborts before anything is written. --dry runs every check and writes nothing.

  python ingest/patch_ocean.py dist/deck.html build/ocean.js [--dry]
"""
import sys, os, io, shutil

PATCHES = []


def P(name, anchor, new, count=1):
    PATCHES.append((name, anchor, new, count))


# ---------------------------------------------------------------- 1. the data
def patch_data(src, ocean_js):
    anchor = '\nconst GEO={"ant":'
    if src.count(anchor) != 1:
        raise SystemExit(f"[data] anchor matched {src.count(anchor)} times, need 1")
    return src.replace(anchor, "\n" + ocean_js.rstrip() + anchor, 1)


# ---------------------------------------------------------------- 2. layers
P("layers",
  ''' {id:"thc",  nm:"Thermohaline conveyor",  src:"schematic path · RAPID-driven speed", on:true, sim:true, ex:"thc_schematic"},''',
  ''' {id:"flow", nm:"Near-surface currents",   src:"NOAA Global Drifter Program · 1/4° · annual mean", on:true, ex:"ocean_flow"},
 {id:"fronts",nm:"ACC fronts",               src:"Park & Durand · CNES-CLS18 mean dynamic topography", on:true, ex:"ocean_fronts"},
 {id:"deep", nm:"Deep & bottom-water limbs", src:"schematic path on real gateways · RAPID-driven speed", on:true, sim:true, ex:"deep_schematic"},''')


# ---------------------------------------------------------------- 3. renderer
OCEAN_RENDER = open(os.path.join(os.path.dirname(__file__), "..", "build", "ocean_render.js"),
                    encoding="utf-8").read()
OCEAN_CAMERA = open(os.path.join(os.path.dirname(__file__), "..", "build", "ocean_camera.js"),
                    encoding="utf-8").read()

OLD_THC_START = 'const THCCOL={warm:"#D8724A", cold:"#4A86D8", bottom:"#7FE3F5", acc:"#9B76DC", up:"#4F9E6A"};'
OLD_THC_END = '''function drawTHC(g,B,cx,cy,s,nearSide,speed){
  const dash=performance.now()/1000*22*speed;
  for(const p of EX.thc){
    const col=THCCOL[p.cls];
    g.globalAlpha = nearSide ? 0.85 : 0.20;
    g.lineCap="round"; g.lineJoin="round";
    g.strokeStyle=col; g.lineWidth = nearSide?4.6:3.0;
    g.globalAlpha *= 0.28;
    gpath(g,p.pts,B,cx,cy,s,nearSide); g.stroke();
    g.globalAlpha = nearSide ? 0.95 : 0.24;
    g.lineWidth = nearSide?2.1:1.4;
    g.setLineDash([9,11]); g.lineDashOffset=-dash;
    gpath(g,p.pts,B,cx,cy,s,nearSide); g.stroke();
    g.setLineDash([]);
  }
  g.globalAlpha=1;
}'''
P("renderer", OLD_THC_START + "\n" + OLD_THC_END, OCEAN_RENDER.rstrip() + "\n" + OCEAN_CAMERA.rstrip())


# ---------------------------------------------------------------- 4. drawGlobe
OLD_GLOBE = '''function drawGlobe(g,cx,cy,s,w,h){
  const moving = st.gDrag || (performance.now()-st.gMoved < 260);
  const n = moving ? GN_MOVE : GN_STILL;
  globeLUT(n, st.glat, st.glon);
  const B=globeBasis(st.glat,st.glon);
  const speed=amocSpeed();

  g.save(); g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();
  const og=g.createRadialGradient(cx-s*0.25,cy-s*0.3,s*0.1,cx,cy,s*1.05);
  og.addColorStop(0,"#0A1722"); og.addColorStop(.7,"#071119"); og.addColorStop(1,"#03080D");
  g.fillStyle=og; g.fillRect(cx-s,cy-s,s*2,s*2);

  // ---- far shell, seen through the body of the Earth
  if(st.lay.ice && (CURF.sh||CURF.nh)){
    g.imageSmoothingEnabled=true; g.globalAlpha=.30;
    g.drawImage(globeShell("far",n),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;
  }
  g.strokeStyle="rgba(92,114,133,.28)"; g.lineWidth=0.7;
  for(const ring of EX.coast){ gpath(g,ring,B,cx,cy,s,false); }
  g.stroke();
  if(st.lay.thc) drawTHC(g,B,cx,cy,s,false,speed);

  // ---- the Earth itself, translucent
  g.fillStyle="rgba(7,16,24,.62)"; g.beginPath(); g.arc(cx,cy,s,0,7); g.fill();
'''
NEW_GLOBE = '''function drawGlobe(g,cx,cy,s0,w,h){
  const s=s0*CAM.zoom;
  st.s=s;
  const moving = st.gDrag || CAM.auto || Math.abs(CAM.vlon)+Math.abs(CAM.vlat)>0.05
               || (performance.now()-st.gMoved < 260);
  const n = moving ? GN_MOVE : GN_STILL;
  globeLUT(n, st.glat, st.glon, moving);
  const B=globeBasis(st.glat,st.glon);
  const speed=amocSpeed();
  const phase=(performance.now()/1000*0.16*speed);

  g.save(); g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();
  const og=g.createRadialGradient(cx-s*0.25,cy-s*0.3,s*0.1,cx,cy,s*1.05);
  og.addColorStop(0,"#0A1722"); og.addColorStop(.7,"#071119"); og.addColorStop(1,"#03080D");
  g.fillStyle=og; g.fillRect(cx-s,cy-s,s*2,s*2);

  // ---- far shell, seen through the body of the Earth
  if(st.lay.ice && (CURF.sh||CURF.nh)){
    g.imageSmoothingEnabled=true; g.globalAlpha=.30;
    g.drawImage(globeShell("far",n),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;
  }
  g.strokeStyle="rgba(92,114,133,.28)"; g.lineWidth=0.7;
  g.beginPath();
  for(const ring of EX.coast){ gpathTo(g,ring,B,cx,cy,s,false); }
  g.stroke();
  // the deep limbs behind the planet, at their own depth
  if(st.lay.deep) ocDrawLimbs(g,B,cx,cy,s,-1,phase,speed);

  // ---- the Earth itself, translucent
  g.fillStyle="rgba(7,16,24,.62)"; g.beginPath(); g.arc(cx,cy,s,0,7); g.fill();
'''
P("drawGlobe.head", OLD_GLOBE, NEW_GLOBE)

OLD_GLOBE2 = '''  // ---- near shell
  if(st.lay.ice && (CURF.sh||CURF.nh)){
    g.imageSmoothingEnabled=true; g.globalAlpha=.95;
    g.drawImage(globeShell("near",n),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;
  }

  // ---- near coastlines
  g.beginPath();
  for(const ring of EX.coast){ gpath(g,ring,B,cx,cy,s,true); }
  g.strokeStyle="rgba(140,168,190,.72)"; g.lineWidth=0.9; g.stroke();

  if(st.lay.thc){
    drawTHC(g,B,cx,cy,s,true,speed);
    drawSitesGlobe(g,B,cx,cy,s);
  }

  g.restore();
'''
NEW_GLOBE2 = '''  // ---- the deep limbs on this side sit UNDER the sea surface, so they go on
  //      before the ice shell and the coastlines, inside the translucent body
  if(st.lay.deep) ocDrawLimbs(g,B,cx,cy,s,+1,phase,speed);

  // ---- near shell
  if(st.lay.ice && (CURF.sh||CURF.nh)){
    g.imageSmoothingEnabled=true; g.globalAlpha=.95;
    g.drawImage(globeShell("near",n),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;
  }

  // ---- the measured surface field, advected
  if(st.lay.flow) ocDrawField(g, ocPutGlobe(B,cx,cy,s));
  if(st.lay.fronts){
    const pf=ocPutGlobe(B,cx,cy,s);
    ocDrawFronts(g,(lon,lat)=>{
      const a=lat*D, b=lon*D, ca=Math.cos(a);
      return pf(ca*Math.cos(b), ca*Math.sin(b), Math.sin(a));
    });
  }

  // ---- near coastlines
  g.beginPath();
  for(const ring of EX.coast){ gpathTo(g,ring,B,cx,cy,s,true); }
  g.strokeStyle="rgba(140,168,190,.72)"; g.lineWidth=0.9; g.stroke();

  if(st.lay.deep) drawSitesGlobe(g,B,cx,cy,s);

  g.restore();
'''
P("drawGlobe.tail", OLD_GLOBE2, NEW_GLOBE2)

# the gateways are drawn with the site labels, in the same collision list
P("sitesGlobe.nodes",
  '''  // stations, if the layer is on
  if(st.lay.stn){
    for(const key of ["S","N"]) for(const L of STATIONS[key]){
      const q=gproj(L[2],L[1],B);''',
  '''  if(st.lay.deep) ocDrawNodes(g,B,cx,cy,s,labels);
  // stations, if the layer is on
  if(st.lay.stn){
    for(const key of ["S","N"]) for(const L of STATIONS[key]){
      const q=gproj(L[2],L[1],B);''')


# ---------------------------------------------------------------- 5. the LUT budget
P("gpath.add",
  '''function gpath(g,flat,B,cx,cy,s,nearSide){
  g.beginPath();''',
  '''// gpath begins its own path, so calling it in a loop and stroking once at the
// end draws only the last ring. Both the coastline passes and the graticule did
// exactly that, which is why the globe drew one arbitrary coast segment and four
// arbitrary lines. gpathTo adds to the open path instead.
function gpathTo(g,flat,B,cx,cy,s,nearSide){
  let started=false;
  for(let i=0;i<flat.length;i+=2){
    const q=gproj(flat[i],flat[i+1],B);
    const vis = nearSide ? q[2]>=0 : q[2]<0;
    if(!vis){ started=false; continue; }
    const px=cx+q[0]*s, py=cy-q[1]*s;
    if(!started){ g.moveTo(px,py); started=true; } else g.lineTo(px,py);
  }
}
function gpath(g,flat,B,cx,cy,s,nearSide){
  g.beginPath();''')

P("globeLUT.budget",
  '''function globeLUT(n,lat0,lon0){
  const key=n+"|"+lat0.toFixed(2)+"|"+lon0.toFixed(2);
  if(GLB.cam===key && GLB.lut) return GLB.lut;''',
  '''function globeLUT(n,lat0,lon0,moving){
  const key=n+"|"+lat0.toFixed(2)+"|"+lon0.toFixed(2);
  if(GLB.cam===key && GLB.lut) return GLB.lut;
  // While the camera is moving the table is the most expensive thing on the
  // frame — an asin and an atan2 per screen cell per side. Rebuilding it every
  // frame is what made the old globe stutter. Hold the previous one instead
  // until the budget allows a new one; the vector layers keep running at full
  // rate, so only the ice shell lags, by at most one budget period.
  if(moving && GLB.lut){
    const t=performance.now();
    if(t-CAM.lastLUT < 26) return GLB.lut;
    CAM.lastLUT=t;
  }''')


# ---------------------------------------------------------------- 6. the camera
OLD_DRAG = '''(function globeDrag(){
  let px=0,py=0,id=null;
  map.addEventListener("pointerdown",e=>{
    if(st.mode!=="GLOBE") return;
    id=e.pointerId; px=e.clientX; py=e.clientY; st.gDrag=true;
    map.setPointerCapture(id);
  });
  map.addEventListener("pointermove",e=>{
    if(!st.gDrag||e.pointerId!==id) return;
    const k=140/st.s;
    setCam(st.glat + (e.clientY-py)*k*0.55, st.glon - (e.clientX-px)*k*0.55);
    px=e.clientX; py=e.clientY;
  });
  const end=()=>{ if(st.gDrag){ st.gDrag=false; st.gMoved=performance.now(); } };
  map.addEventListener("pointerup",end);
  map.addEventListener("pointercancel",end);
})();'''
NEW_DRAG = '''(function globeDrag(){
  const pts=new Map();            // pointerId -> {x,y}
  let px=0,py=0,id=null,lt=0,pinch=0;
  const dist=()=>{ const a=[...pts.values()]; return a.length<2?0:Math.hypot(a[0].x-a[1].x,a[0].y-a[1].y); };

  map.addEventListener("pointerdown",e=>{
    if(st.mode!=="GLOBE") return;
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    camTouch();
    if(pts.size===2){ pinch=dist(); st.gDrag=false; return; }
    id=e.pointerId; px=e.clientX; py=e.clientY; lt=performance.now();
    st.gDrag=true; CAM.vlat=0; CAM.vlon=0;
    try{ map.setPointerCapture(id); }catch(err){}
  });

  map.addEventListener("pointermove",e=>{
    if(!pts.has(e.pointerId)) return;
    pts.set(e.pointerId,{x:e.clientX,y:e.clientY});
    if(pts.size>=2){
      const d=dist();
      if(pinch>4 && d>4){ CAM.zTarget=Math.max(CAM_ZMIN,Math.min(CAM_ZMAX,CAM.zTarget*(d/pinch))); pinch=d; camTouch(); }
      return;
    }
    if(!st.gDrag||e.pointerId!==id) return;
    const k=140/st.s;
    const dlat=(e.clientY-py)*k*0.55, dlon=-(e.clientX-px)*k*0.55;
    setCam(st.glat+dlat, st.glon+dlon);
    const now=performance.now(), dt=Math.max(8,now-lt)/1000;
    // exponentially smoothed so a single jittery sample cannot fling the globe
    CAM.vlat = CAM.vlat*0.62 + (dlat/dt)*0.38;
    CAM.vlon = CAM.vlon*0.62 + (dlon/dt)*0.38;
    px=e.clientX; py=e.clientY; lt=now;
    camTouch();
  });

  const end=e=>{
    if(e) pts.delete(e.pointerId);
    if(pts.size<2) pinch=0;
    if(st.gDrag && (!e || e.pointerId===id)){
      st.gDrag=false; st.gMoved=performance.now();
      if(performance.now()-lt > camFlickGapMs()){ CAM.vlat=0; CAM.vlon=0; }  // released after a pause: no throw
      const m=Math.hypot(CAM.vlat,CAM.vlon);
      if(m>170){ CAM.vlat*=170/m; CAM.vlon*=170/m; }
    }
  };
  map.addEventListener("pointerup",end);
  map.addEventListener("pointercancel",end);
  map.addEventListener("pointerleave",e=>{ if(pts.size) end(e); });

  map.addEventListener("wheel",e=>{
    if(st.mode!=="GLOBE") return;
    e.preventDefault();
    camZoom(Math.exp(-e.deltaY*(e.deltaMode===1?0.03:0.0016)));
  },{passive:false});

  map.addEventListener("dblclick",e=>{ if(st.mode==="GLOBE") camZoom(1.6); });

  // the globe is reachable from the keyboard, which it was not before
  map.setAttribute("tabindex","0");
  map.addEventListener("keydown",e=>{
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
  });
})();'''
P("camera", OLD_DRAG, NEW_DRAG)

# a preset should also cancel the throw and reset the zoom
P("presets",
  '''  if(c==="atl") setCam(0,-30); else setCam(+c, st.glon);''',
  '''  CAM.vlat=0; CAM.vlon=0; CAM.zTarget=1; camTouch();
  if(c==="atl") setCam(0,-30); else setCam(+c, st.glon);''')


# ---------------------------------------------------------------- 7. the discs
P("drawDisc.flow",
  '''  if(st.lay.ice && CURF[h]){ g.imageSmoothingEnabled=true; g.globalAlpha=.92; g.drawImage(OFF[h],cx-s,cy-s,s*2,s*2); g.globalAlpha=1; }
''',
  '''  if(st.lay.ice && CURF[h]){ g.imageSmoothingEnabled=true; g.globalAlpha=.92; g.drawImage(OFF[h],cx-s,cy-s,s*2,s*2); g.globalAlpha=1; }

  // the measured surface field, on the disc's own projection. The polar grid
  // stops at 45 deg and so does this; the drifter climatology stops at 72.9 S
  // and 84.9 N, which is where drifters stop, not where the ocean does.
  if(st.lay.flow) ocDrawField(g, ocPutDisc(cx,cy,s,S));
  if(st.lay.fronts && S){
    ocDrawFronts(g,(lon,lat)=>{
      if(lat>-40) return false;
      const p=proj(lon,lat,S);
      if(p[0]*p[0]+p[1]*p[1]>1) return false;
      OC_PX=cx+p[0]*s; OC_PY=cy-p[1]*s; return true;
    });
  }
''')

P("drawDisc.sites",
  '''  if(st.lay.thc) drawSitesDisc(g,cx,cy,s,S,compact,boxes);''',
  '''  if(st.lay.deep) drawSitesDisc(g,cx,cy,s,S,compact,boxes);''')


# ---------------------------------------------------------------- 8. the loop
P("frame",
  '''  const s=new Date();
  $("#utc").textContent=[s.getUTCHours(),s.getUTCMinutes(),s.getUTCSeconds()].map(v=>String(v).padStart(2,"0")).join(":");''',
  '''  camStep(dt);
  if(st.lay.flow){ ocStep(dt); ocBudget(dt); }
  if(st.mode==="GLOBE"){
    const pk=st.glat.toFixed(0)+"|"+st.glon.toFixed(0)+"|"+CAM.zoom.toFixed(1);
    if(pk!==st.projKey){ st.projKey=pk; projLabel(); }
  }
  const s=new Date();
  $("#utc").textContent=[s.getUTCHours(),s.getUTCMinutes(),s.getUTCSeconds()].map(v=>String(v).padStart(2,"0")).join(":");''')


# ---------------------------------------------------------------- 9. the readout
P("projlabel",
  '''  $("#proj").textContent = st.mode==="GLOBE"
    ? `ORTHOGRAPHIC · VIEW ${Math.abs(st.glat).toFixed(0)}°${st.glat<0?"S":"N"} ${Math.abs(st.glon).toFixed(0)}°${st.glon<0?"W":"E"}`
    : st.mode==="PAIR" ? "EASE2 25 km → EPSG:3413 / EPSG:3976 · FRAMED TO ±45°"
    : st.S ? "EASE2 25 km → EPSG:3976 · WGS-84 · SP 70°S · FRAMED TO 45°S"
           : "EASE2 25 km → EPSG:3413 · WGS-84 · SP 70°N · FRAMED TO 45°N";''',
  '''  projLabel();''')

# the camera now moves continuously, so the readout has to be able to follow it
# without paying for a whole sync()
P("projlabel.fn",
  '''/* ---------------- readouts ---------------- */
const MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];''',
  '''/* ---------------- readouts ---------------- */
const MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function projLabel(){
  $("#proj").textContent = st.mode==="GLOBE"
    ? `ORTHOGRAPHIC · VIEW ${Math.abs(st.glat).toFixed(0)}°${st.glat<0?"S":"N"} ${Math.abs(st.glon).toFixed(0)}°${st.glon<0?"W":"E"}${CAM.zoom>1.02?" · ×"+CAM.zoom.toFixed(1):""}`
    : st.mode==="PAIR" ? "EASE2 25 km → EPSG:3413 / EPSG:3976 · FRAMED TO ±45°"
    : st.S ? "EASE2 25 km → EPSG:3976 · WGS-84 · SP 70°S · FRAMED TO 45°S"
           : "EASE2 25 km → EPSG:3413 · WGS-84 · SP 70°N · FRAMED TO 45°N";
}''')


# the cursor readout gains the measured current under the pointer
P("hover.current",
  '''  $("#cursor").innerHTML=`<b>CURSOR</b> ${Math.abs(p.lat).toFixed(2)}°${p.lat<0?"S":"N"} ${Math.abs(p.lon).toFixed(2)}°${p.lon<0?"W":"E"}`;
  if(p.land){ $("#conc").innerHTML="<b>CONC</b> land mask"; showEx("ice_edge",e.clientX,e.clientY); return; }''',
  '''  $("#cursor").innerHTML=`<b>CURSOR</b> ${Math.abs(p.lat).toFixed(2)}°${p.lat<0?"S":"N"} ${Math.abs(p.lon).toFixed(2)}°${p.lon<0?"W":"E"}`;
  ocCursor(p);
  if(p.land){ $("#conc").innerHTML="<b>CONC</b> land mask"; showEx("ice_edge",e.clientX,e.clientY); return; }''')

P("hover.clear",
  '''map.addEventListener("pointerleave",()=>{
  $("#cursor").innerHTML="<b>CURSOR</b> ——.—° ——.—°";
  $("#conc").innerHTML="<b>CONC</b> ———"; hideEx();
});''',
  '''map.addEventListener("pointerleave",()=>{
  $("#cursor").innerHTML="<b>CURSOR</b> ——.—° ——.—°";
  $("#conc").innerHTML="<b>CONC</b> ———"; ocCursor(null); hideEx();
});

/* the measured current under the pointer, read from the field rather than off
   anything rendered. NO OBS where the drifter climatology has no observation. */
function ocCursor(p){
  const el=$("#curr"); if(!el) return;
  if(!p || !st.lay.flow){ el.innerHTML="<b>CURRENT</b> ———"; return; }
  if(!OC.ready){ el.innerHTML="<b>CURRENT</b> loading"; return; }
  if(p.land || !ocSample(p.lon,p.lat)){ el.innerHTML='<b>CURRENT</b> <span class="wait">NO OBS</span>'; return; }
  const sp=Math.hypot(OC_S.u,OC_S.v)*100;
  const brg=(Math.atan2(OC_S.u,OC_S.v)/D+360)%360;
  const pts=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];
  el.innerHTML=`<b>CURRENT</b> ${sp.toFixed(1)} cm/s → ${pts[Math.round(brg/22.5)%16]} (${brg.toFixed(0)}°)`;
}''')


# ---------------------------------------------------------------- 10. explainers
P("explainers",
  '''thc_schematic:{k:"mech",t:"Why the conveyor is a cartoon",''',
  ''' ocean_flow:{k:"ins",t:"The surface currents are measured",
 b:"These are not drawn. Every filament on the ocean is a particle advected through a <b>measured velocity field</b> — the near-surface climatology of the NOAA Global Drifter Program, built from satellite-tracked buoys drogued at 15 m and binned to a quarter of a degree. The Gulf Stream, the Agulhas retroflection, the Kuroshio, the equatorial bands and the jets of the Circumpolar Current are in the data, not in the artwork. Where the drifters never went, nothing is drawn and the readout says NO OBS — which is most of the ice-covered ocean, because a drifter cannot survive there.",
 p:"NOAA GDP near-surface velocity climatology v3.10, 1/4°, drogued at 15 m, CC BY 4.0. Laurindo, Mariano & Lumpkin (2017), doi:10.1016/j.dsr.2017.04.009. Annual mean: it does not move with the scrubber."},
 ocean_rate:{k:"num",t:"How fast the flow is played",
 b:"The animation runs at a fixed rate: about <b>five days of ocean per second</b>. That number is a display choice and nothing else — it is not modulated by the timeline, because the field is an annual mean and has no month. The deep limbs are the ones that change speed, and they change with the measured RAPID value.",
 p:"Display rate only. Velocity itself is the measured climatology, unscaled."},
 drifter_days:{k:"num",t:"Where we actually know",
 b:"Colour the filaments by <b>Coverage</b> and the map stops being about the ocean and starts being about us. The field carries its own sampling density — drifter-days per square degree — and it is wildly uneven. Across the whole record, <b>95% of the ocean between 40°S and 60°S has been sampled at all; south of 60°S only 20% has, and north of 60°N only 12%</b>. Where a drifter has never been there is no filament, and the emptiness is the finding. This is the same ocean whose deep water is made in exactly those two places.",
 p:"N channel of the GDP climatology, 0 to 1713 drifter-days per square degree. The three colours split the sampled ocean near its own terciles, 158 and 337 drifter-days. Coverage by band computed from this field."},
 ocean_fronts:{k:"obj",t:"The five fronts of the Circumpolar Current",
 b:"The ACC is not a current, it is a set of jets separated by fronts, and the fronts are where the water changes character. From north to south: the northern branch of the Subantarctic Front, the Subantarctic Front, the <b>Polar Front</b>, the Southern ACC Front and the Southern Boundary. These positions are measured — derived from the mean dynamic topography of the sea surface, not drawn by hand. The Polar Front is the sharpest temperature step in the open ocean.",
 p:"Park & Durand (2019), altimetry-derived ACC fronts from the CNES-CLS18 MDT. SEANOE, doi:10.17882/59800, CC BY 4.0."},
 deep_schematic:{k:"mech",t:"What is schematic here, exactly",
 b:"The surface is measured. <b>The deep limbs are not.</b> There is no measured global map of the deep circulation and there cannot be one from present instruments — the overturning is observed at a handful of lines, not everywhere. So the deep paths are illustration. What is real about them is where they are made to pass: the Denmark Strait and Faroe Bank sills, the Charlie-Gibbs and Romanche fracture zones, the Vema Channel, and the four Antarctic bottom-water sources, each at its published position and sill depth. A cartoon threaded through real gateways.",
 p:"Paths after Talley (2013) and Lumpkin & Speer (2007). Gateway depths cited individually. Animation speed: RAPID 26.5°N monthly mean, relative to the record mean."},
 depth_exag:{k:"mech",t:"The depth you are seeing is exaggerated",
 b:"The deep limbs are drawn inside the globe at their real depths — but the ocean is four kilometres deep on a planet with a radius of six thousand four hundred, which is six hundredths of one per cent. At true scale the entire deep circulation would be thinner than the line used to draw the coast. The vertical scale here is stretched about <b>165 times</b> so that North Atlantic Deep Water can be seen passing underneath the warm water returning north above it. Horizontal positions are not stretched.",
 p:"6000 m mapped to 0.155 of the globe radius. Vertical exaggeration ~165×, horizontal 1×."},
 limb_nadw:{k:"obj",t:"North Atlantic Deep Water",
 b:"Water that has crossed the Atlantic losing heat all the way, sinking in the Nordic and Labrador seas and returning south at one and a half to four kilometres down, hugging the western side of the basin. Two thirds of it enters over the Greenland–Scotland ridge as dense overflow: 3.2 Sv through the Denmark Strait, 2.1 Sv through the Faroe Bank Channel, each accelerating and entraining as it falls down the slope behind the sill.",
 p:"Denmark Strait 3.20 ± 0.50 Sv, Jochumsen et al. (2017). Faroe Bank Channel 2.1 ± 0.2 Sv, Østerhus et al. (2008). Subpolar overturning 16.7 ± 0.6 Sv, OSNAP."},
 limb_aabw:{k:"obj",t:"Antarctic Bottom Water",
 b:"The densest water in the world ocean, and the floor of every basin on the planet. It is made on the Antarctic shelf, where sea ice forming in coastal polynyas rejects its salt into the water beneath and the brine runs off the shelf edge. Four sources are known: the Weddell Sea, the Ross Sea, the Adélie and George V coast, and the Cape Darnley polynya — the last of which was only identified in 2013 and supplies 6–13% of the total. Estimates of the whole range from 5 to 20 Sv depending on how you count.",
 p:"Cape Darnley 0.3–0.7 Sv, 6–13% of the circumpolar total. Ohshima et al. (2013), Nature Geoscience, doi:10.1038/ngeo1738."},
 limb_up:{k:"mech",t:"Where the deep water comes back",
 b:"For a thousand years of downward flow there has to be an equal return upward, and for most of the last century nobody could say where. The modern answer is mostly here: in the Southern Ocean, at the one band of latitude with no continent to stop the wind, the westerlies pull surface water northward and deep water rises to replace it. The Circumpolar Current is not only a current; it is the place the abyss touches the sky.",
 p:"Southern Ocean upwelling after Marshall & Speer (2012). Schematic — the rate is not measured here."},
 limb_sink:{k:"mech",t:"The sinking, drawn to scale in depth",
 b:"Six places on Earth where surface water becomes deep water. Two in the north — the Nordic seas and the Labrador Sea — where water loses heat to a winter atmosphere until it is dense enough to fall. Four in the south, where it is not cooling that does it but salt: sea ice forms, expels brine, and the water underneath becomes the heaviest in the ocean. Everything else on this globe is a consequence of these six patches.",
 p:"Positions measured; descent rate and path schematic."},
thc_schematic:{k:"mech",t:"Why the conveyor is a cartoon",''')

# the old explainer body is now wrong in one particular: the surface is measured
P("explainers.old",
  ''' b:"The ribbon on the globe is a <b>schematic</b>, drawn after the classic Broecker figure. There is no measured global map of this circulation and there cannot be one from present instruments: the real flow is depth-varying, full of eddies, and does not travel in a tidy loop. Its animation speed here is driven by the actual monthly RAPID measurement, so it slows when the real circulation slows — but the path itself is illustration.",
 p:"Path: hand-drawn. Speed: RAPID 26.5°N monthly mean, relative to the 17.0 Sv record mean."},''',
  '''  b:"It was, in the first version of this deck: one hand-drawn ribbon, dashes marching along it, marked SIM. Half of that is now gone. The surface limb is a measured velocity field and the ACC fronts are measured positions; only the deep and bottom limbs are still drawn, and they are drawn through real gateways at real depths. The single remaining piece of pure illustration is the path the deep water takes between one sill and the next — and that stays illustration, because the deep ocean is observed at lines, not everywhere.",
  p:"Surface: measured. Fronts: measured. Deep path: hand-drawn. Speed: RAPID 26.5°N monthly mean, relative to the 17.0 Sv record mean."},''')

# gateway explainers are generated from the data so a new node cannot be forgotten
P("exIndex.nodes",
  '''function exIndex(){
  const head=$("#exIndexHead"), box=$("#exIndex");''',
  '''// one explainer per gateway, built from the register so the two cannot drift apart
(function ocNodeExplainers(){
  const KINDOF={sill:"A sill",gate:"A gateway"};
  for(const nd of OCEAN.nodes){
    EXPL["node_"+nd.id]={k:"obj",t:nd.label,
      b:`${KINDOF[nd.kind]||"A gateway"} of the deep circulation, at its true position `+
        `(${Math.abs(nd.at[1]).toFixed(1)}°${nd.at[1]<0?"S":"N"} ${Math.abs(nd.at[0]).toFixed(1)}°${nd.at[0]<0?"W":"E"}) `+
        `and its published depth of <b>${nd.depth} m</b>. The line that passes through it is schematic; this point is not.`,
      p:nd.cite};
  }
})();

function exIndex(){
  const head=$("#exIndexHead"), box=$("#exIndex");''')


# ---------------------------------------------------------------- 11. boot
P("graticule",
  '''    g.strokeStyle="rgba(122,150,175,.14)"; g.lineWidth=1;
    for(let lat=-75;lat<=75;lat+=15){
      const ring=[]; for(let lon=-180;lon<=180;lon+=4){ ring.push(lon,lat); }
      gpath(g,ring,B,cx,cy,s,true);
    }
    for(let lon=-180;lon<180;lon+=30){
      const ring=[]; for(let lat=-88;lat<=88;lat+=3){ ring.push(lon,lat); }
      gpath(g,ring,B,cx,cy,s,true);
    }
    g.stroke();
    // the two latitudes the presets look down from
    g.strokeStyle="rgba(127,227,245,.30)"; g.setLineDash([4,4]);
    for(const lat of [60,-60]){
      const ring=[]; for(let lon=-180;lon<=180;lon+=4){ ring.push(lon,lat); }
      gpath(g,ring,B,cx,cy,s,true);
    }
    g.stroke(); g.setLineDash([]);''',
  '''    g.strokeStyle="rgba(122,150,175,.14)"; g.lineWidth=1;
    g.beginPath();
    for(let lat=-75;lat<=75;lat+=15){
      const ring=[]; for(let lon=-180;lon<=180;lon+=4){ ring.push(lon,lat); }
      gpathTo(g,ring,B,cx,cy,s,true);
    }
    for(let lon=-180;lon<180;lon+=30){
      const ring=[]; for(let lat=-88;lat<=88;lat+=3){ ring.push(lon,lat); }
      gpathTo(g,ring,B,cx,cy,s,true);
    }
    g.stroke();
    // the two latitudes the presets look down from
    g.strokeStyle="rgba(127,227,245,.30)"; g.setLineDash([4,4]);
    g.beginPath();
    for(const lat of [60,-60]){
      const ring=[]; for(let lon=-180;lon<=180;lon+=4){ ring.push(lon,lat); }
      gpathTo(g,ring,B,cx,cy,s,true);
    }
    g.stroke(); g.setLineDash([]);''')

# the honesty ledger in the footer described a conveyor that no longer exists
P("footer.ledger",
  '''      <p>The <b>thermohaline conveyor on the globe is a schematic</b> — there is no measured global map of this circulation. Its path is drawn after the classic Broecker figure; only its speed is real, scaled by the observed monthly RAPID value. The deep-water formation sites and the RAPID and OSNAP lines are at their true locations. ITS_LIVE, Argo and the ground track remain illustrative and are marked <span class="prov" style="padding:0 4px"><span class="tag sim">SIM</span></span> wherever they appear.</p>''',
  '''      <p>The ocean circulation is now three layers, and only one of them is drawn. The <b>near-surface currents are measured</b> — every filament is a particle advected through the <code>NOAA Global Drifter Program</code> velocity climatology, so the Gulf Stream, the Agulhas and the jets of the Circumpolar Current are in the data rather than the artwork; where the drifters never went the readout says <i>no observation</i>. The <b>five ACC fronts are measured</b> too, from the CNES-CLS18 mean dynamic topography. The <b>deep and bottom-water limbs are still a schematic</b> and are marked <span class="prov" style="padding:0 4px"><span class="tag sim">SIM</span></span>: there is no measured global map of the deep circulation and there cannot be one from present instruments. What is real about them is where they pass — the Denmark Strait and Faroe Bank sills, the Charlie-Gibbs and Romanche fracture zones, the Vema Channel, the four Antarctic bottom-water sources — each at its published position and sill depth, and their animation speed follows the observed monthly RAPID value. They are drawn inside the globe at their true depths, on a vertical scale stretched about 165 times so that they can be seen at all. ITS_LIVE, Argo and the ground track remain illustrative and are marked <span class="tag sim">SIM</span> wherever they appear.</p>''')

P("boot",
  '''sync(); drawTL();
loadActive();''',
  '''sync(); drawTL();
loadActive();
ocLoad();
CAM.idle=performance.now();''')

# resizing changes how many particles are worth carrying
P("resize",
  '''new ResizeObserver(()=>{ drawTL(); }).observe(tl);''',
  '''new ResizeObserver(()=>{ drawTL(); }).observe(tl);
(function(){ let t=0; new ResizeObserver(()=>{ clearTimeout(t); t=setTimeout(()=>{ if(OC.ready&&Math.abs(ocCount()-OC.nPart)>320) ocSeed(); },320); }).observe(map); })();''')


# ------------------------------------------------------- 12. the CURRENT readout cell
P("readout.cell",
  '''            <div class="readout" id="conc"><b>CONC</b> ———</div>''',
  '''            <div class="readout" id="conc"><b>CONC</b> ———</div>
            <div class="readout" id="curr" data-ex="ocean_flow"><b>CURRENT</b> ———</div>''')

# the globe explainer no longer describes a globe you can only drag
P("mode_globe",
  ''' b:"One Earth, semi-transparent, so you can see the far pole through the planet. Drag to orbit; the two presets look down from 60°N and 60°S. Below 45° the deck has no ice field to draw — that is where the polar grid ends, not where the data ends.",
 p:"Orthographic projection of the same 25 km field; coastlines are Natural Earth 110m."},''',
  ''' b:"One Earth, semi-transparent, so you can see the far pole through the planet, and the deep limbs of the circulation running underneath the surface inside it. Drag to orbit — it carries momentum and keeps turning when you let go. Scroll or pinch to zoom, double-click to zoom in, arrow keys to orbit, <b>0</b> to reset. Left alone for a while it turns by itself. Below 45° the deck has no <i>ice</i> field to draw — that is where the polar grid ends, not where the data ends; the ocean currents are drawn everywhere the drifters went.",
 p:"Orthographic projection. Ice field on the 25 km polar grid; currents on a 1/4° global grid; coastlines Natural Earth."},''')


# ------------------------------------------- 13. the seasonal and density layer
# state the two new flow controls carry
P("state.flow",
  '''           baseImg:"relief", driftX:1 };''',
  '''           baseImg:"relief", driftX:1, flowCol:"speed", flowSeason:true };''')

# the flow layer is no longer an annual mean
P("layer.flow.src",
  ''' {id:"flow", nm:"Near-surface currents",   src:"NOAA Global Drifter Program · 1/4° · annual mean", on:true, ex:"ocean_flow"},''',
  ''' {id:"flow", nm:"Near-surface currents",   src:"NOAA Global Drifter Program · 1/4° · monthly climatology", on:true, ex:"ocean_flow"},''')

# a control for what the filaments are coloured by, in the deck's own idiom
P("ui.flowbar",
  '''            <div class="gctl" id="driftBar" role="group" aria-label="Drift vector length">''',
  '''            <div class="gctl" id="flowBar" role="group" aria-label="Current colouring">
              <button data-fc="speed" aria-pressed="true"  data-ex="ocean_flow">Speed</button>
              <button data-fc="temp"  aria-pressed="false" data-ex="ocean_temp">Temp</button>
              <button data-fc="dens"  aria-pressed="false" data-ex="drifter_days">Coverage</button>
              <button data-fs="1" id="flowSeasonBtn" aria-pressed="true" data-ex="seasonal_flow">Season</button>
              <span id="flowNote" style="color:var(--ink3);letter-spacing:.04em"></span>
            </div>
            <div class="gctl" id="driftBar" role="group" aria-label="Drift vector length">''')

P("ui.flowbar.handlers",
  '''  $$("#driftBar button").forEach(b=>b.addEventListener("click",()=>{''',
  '''  $$("#flowBar button[data-fc]").forEach(b=>b.addEventListener("click",()=>{
    st.flowCol = b.dataset.fc;
    $$("#flowBar button[data-fc]").forEach(o=>o.setAttribute("aria-pressed", String(o===b)));
    flowNote(); paintAll();
  }));
  { const sb=$("#flowSeasonBtn"); if(sb) sb.addEventListener("click",()=>{
      st.flowSeason = !st.flowSeason;
      sb.setAttribute("aria-pressed", String(st.flowSeason));
      flowNote(); paintAll();
    }); }
  $$("#driftBar button").forEach(b=>b.addEventListener("click",()=>{''')

# the flow layer's own line of provenance, refreshed wherever it can change
P("flownote",
  '''function projLabel(){''',
  '''const MONNM=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
/* What the current layer is showing, said plainly, because the two things it
   can show are easy to confuse: a climatological September is the average of
   every September in the record, not September of the year on the dial. */
function flowNote(){
  const el=$("#flowNote"); if(!el) return;
  const bar=$("#flowBar"); if(bar) bar.hidden = !st.lay.flow;
  if(!st.lay.flow){ el.textContent=""; return; }
  if(!OC.ready){ el.textContent="loading"; return; }
  if(!OC.sok){ el.textContent="annual mean"; return; }
  el.textContent = st.flowSeason
    ? (MONNM[Math.floor(OC.mon)%12]+" climatology")
    : "annual mean";
  el.style.color = st.flowSeason ? "var(--ink3)" : "var(--ink4)";
}

function projLabel(){''')

# the month follows the scrubber
P("sync.month",
  '''function sync(){
  const hk=hemiKey(), k=monIdx(), ym=ymFor(k), yy=ym[0], mm=ym[1];
  buildCur();''',
  '''function sync(){
  const hk=hemiKey(), k=monIdx(), ym=ymFor(k), yy=ym[0], mm=ym[1];
  buildCur();
  ocSetMonth(); flowNote();''')

# and keeps following it while the deck plays
P("frame.month",
  '''  camStep(dt);
  if(st.lay.flow){ ocStep(dt); ocBudget(dt); }''',
  '''  camStep(dt);
  if(st.lay.flow){ if(st.playing) ocSetMonth(); ocStep(dt); ocBudget(dt); }''')

P("boot.flownote",
  '''ocLoad();
CAM.idle=performance.now();''',
  '''ocLoad();
flowNote();
CAM.idle=performance.now();''')



# ---------------------------------------- 14. saying what the season actually is
P("explainer.flow.seasonal",
  ''' p:"NOAA GDP near-surface velocity climatology v3.10, 1/4°, drogued at 15 m, CC BY 4.0. Laurindo, Mariano & Lumpkin (2017), doi:10.1016/j.dsr.2017.04.009. Annual mean: it does not move with the scrubber."},''',
  ''' p:"NOAA GDP near-surface velocity climatology v3.10, 1/4°, drogued at 15 m, CC BY 4.0. Laurindo, Mariano & Lumpkin (2017), doi:10.1016/j.dsr.2017.04.009."},
seasonal_flow:{k:"num",t:"It follows the scrubber — but it is a climatology",
 b:"The currents change with the month on the dial. Run the timeline and watch the <b>Somali Current reverse</b> with the monsoon, the equatorial bands tighten, the Circumpolar Current lean north and south with the season. What you must not read into it: a climatological September is the average of <b>every</b> September in the record, not September of the year showing on the dial. The ice above it is that month, that year, measured. The water is that month, averaged over four decades. Two different kinds of true, on the same screen, and the readout names which one you are looking at. Turn <b>Season</b> off to fall back to the annual mean.",
 p:"Twelve climatological months as a 1° anomaly on the 1/4° annual mean. Against the true monthly field the annual mean alone is 4.82 cm/s RMS; with the anomaly, 1.77 cm/s. Where a month has no observation of its own — 4% of cells — the value falls back to the annual mean and the readout says so."},''')

P("explainer.rate",
  ''' b:"The animation runs at a fixed rate: about <b>five days of ocean per second</b>. That number is a display choice and nothing else — it is not modulated by the timeline, because the field is an annual mean and has no month. The deep limbs are the ones that change speed, and they change with the measured RAPID value.",
 p:"Display rate only. Velocity itself is the measured climatology, unscaled."},''',
  ''' b:"The animation runs at a fixed rate: about <b>eighteen days of ocean per second</b>. That number is a display choice and nothing else. It is not modulated by anything: the <i>velocities</i> change with the month on the scrubber, but the rate they are played back at does not, so a fast current always looks fast. The deep limbs are the ones whose speed changes, and they change with the measured RAPID value.",
 p:"Display rate only. Velocity itself is the measured climatology, unscaled."},''')

# the readout has to distinguish the two kinds of true
P("hover.month",
  '''  const pts=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];
  el.innerHTML=`<b>CURRENT</b> ${sp.toFixed(1)} cm/s → ${pts[Math.round(brg/22.5)%16]} (${brg.toFixed(0)}°)`;''',
  '''  const pts=["N","NNE","NE","ENE","E","ESE","SE","SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"];
  // which of the two it is, every time — a climatological month and an annual
  // mean are both measured, and they are not the same claim
  const when = OC_S.seasonal ? MONNM[Math.floor(OC.mon)%12]+" clim." : "annual mean";
  const dens = st.flowCol==="dens"
    ? ` · ${Math.round(Math.expm1(OC_S.n/255*Math.log1p(OCEAN.flow.nmax)))} drifter-days/deg²` : "";
  el.innerHTML=`<b>CURRENT</b> ${sp.toFixed(1)} cm/s → ${pts[Math.round(brg/22.5)%16]} (${brg.toFixed(0)}°) <span style="color:var(--ink4)">${when}${dens}</span>`;''')

# the coverage ramp needs its thresholds on screen while it is showing
P("flownote.dens",
  '''  el.textContent = st.flowSeason
    ? (MONNM[Math.floor(OC.mon)%12]+" climatology")
    : "annual mean";
  el.style.color = st.flowSeason ? "var(--ink3)" : "var(--ink4)";''',
  '''  const when = st.flowSeason ? (MONNM[Math.floor(OC.mon)%12]+" climatology") : "annual mean";
  if(st.flowCol==="dens"){
    // the legend is derived from the ramp, never typed beside it, so the two
    // cannot drift apart when a threshold is retuned
    const R=ocRamp(), L=Math.log1p(OCEAN.flow.nmax);
    const cut=b=>Math.round(Math.expm1(b/255*L));
    el.innerHTML = when
      + \' · <span style="color:rgb(\'+R[0].col+\')">&lt;\'+cut(R[0].max)+\'</span>\'
      + \' <span style="color:rgb(\'+R[1].col+\')">\'+cut(R[0].max)+\'–\'+cut(R[1].max)+\'</span>\'
      + \' <span style="color:rgb(\'+R[2].col+\')">&gt;\'+cut(R[1].max)+\'</span> drifter-days/deg²\';
  } else {
    el.textContent = when;
  }
  el.style.color = st.flowSeason ? "var(--ink3)" : "var(--ink4)";''')

# the control bar hides with its layer
P("layers.flownote",
  '''  { const bb=$("#baseBar"), db=$("#driftBar");
    if(bb) bb.hidden = !st.lay.sat;
    if(db) db.hidden = !st.lay.drift; }''',
  '''  { const bb=$("#baseBar"), db=$("#driftBar");
    if(bb) bb.hidden = !st.lay.sat;
    if(db) db.hidden = !st.lay.drift; }
  try{ flowNote(); }catch(e){}''')

P("footer.seasonal",
  '''The <b>near-surface currents are measured</b> — every filament is a particle advected through the <code>NOAA Global Drifter Program</code> velocity climatology, so the Gulf Stream, the Agulhas and the jets of the Circumpolar Current are in the data rather than the artwork; where the drifters never went the readout says <i>no observation</i>.''',
  '''The <b>near-surface currents are measured</b> — every filament is a particle advected through the <code>NOAA Global Drifter Program</code> velocity climatology, so the Gulf Stream, the Agulhas and the jets of the Circumpolar Current are in the data rather than the artwork; where the drifters never went the readout says <i>no observation</i>. They move with the scrubber, but as a <b>climatology</b>: a climatological September is the average of every September in the record, not September of the year on the dial, and the readout says which you are looking at. Switch the colouring to <b>Coverage</b> to see the other half of that story — how unevenly the ocean has actually been sampled.''')



# ------------------------------------------------- 15. the temperature colouring
P("flownote.temp",
  '''  if(st.flowCol==="dens"){''',
  '''  if(st.flowCol==="temp"){
    const R=ocRamp();
    el.innerHTML = when
      + \' · <span style="color:rgb(\'+R[0].col+\')">&lt;\'+R[0].max+\'°</span>\'
      + \' <span style="color:rgb(\'+R[1].col+\')">\'+R[0].max+\'–\'+R[1].max+\'°</span>\'
      + \' <span style="color:rgb(\'+R[2].col+\')">&gt;\'+R[1].max+\'°C</span>\'
      + (OC.tok ? \'\' : \' · loading\');
  } else if(st.flowCol==="dens"){''')

# temperature belongs in the readout whatever the colouring is: it is the half of
# "thermohaline" the deck was not showing
P("hover.temp",
  '''  const dens = st.flowCol==="dens"
    ? ` · ${Math.round(Math.expm1(OC_S.n/255*Math.log1p(OCEAN.flow.nmax)))} drifter-days/deg²` : "";''',
  '''  const dens = st.flowCol==="dens"
    ? ` · ${Math.round(Math.expm1(OC_S.n/255*Math.log1p(OCEAN.flow.nmax)))} drifter-days/deg²` : "";
  const tC = ocTemp(p.lon, p.lat);
  const temp = tC===null ? "" : ` · ${tC.toFixed(1)}°C`;''')
P("hover.temp.render",
  '''${pts[Math.round(brg/22.5)%16]} (${brg.toFixed(0)}°) <span style="color:var(--ink4)">${when}${dens}</span>`;''',
  '''${pts[Math.round(brg/22.5)%16]} (${brg.toFixed(0)}°)<b style="color:var(--ink2)">${temp}</b> <span style="color:var(--ink4)">${when}${dens}</span>`;''')

P("explainer.temp",
  '''drifter_days:{k:"num",t:"Where we actually know",''',
  '''ocean_temp:{k:"num",t:"The thermo in thermohaline",
 b:"Colour the filaments by <b>Temp</b> and the conveyor stops being a diagram. The Gulf Stream leaves the tropics at about <b>24 °C</b> and runs northeast in orange; the Labrador Current comes back past it at <b>3 °C</b> in blue; the Circumpolar Current is a cold band all the way round. That contrast is the engine — water is moved by being heated and cooled and by gaining and losing salt, and until this ramp existed every filament on this map was the same white whichever way it was carrying heat. The temperature is measured by the thermistor on the same drifters that measured the velocity.",
 p:"GDP drifter SST climatology, annual mean, 1/2°, CC BY 4.0. Breaks at 10 and 22 °C. Eighty cells reading below the freezing point of seawater — beached drifters and failed thermistors — are dropped rather than clamped."},
limb_warm:{k:"obj",t:"The warm upper limb",
 b:"The half that goes north. Water crosses from the Indian Ocean round the Cape, west across the South Atlantic, up through the Caribbean and the Florida Straits, and out along the Gulf Stream and the North Atlantic Current towards the Nordic and Labrador seas, in the <b>upper few hundred metres</b>. It carries roughly a <b>petawatt</b> of heat northward — which is why this circulation is something anyone living in northwest Europe has a stake in. The path is schematic like the deep limbs; the water on it is measured, and you can watch it in the surface field underneath.",
 p:"Upper limb after Talley (2013). Drawn at 90–300 m. The surface velocity along it is measured; the line is illustration."},
drifter_days:{k:"num",t:"Where we actually know",''')

P("footer.temp",
  '''Switch the colouring to <b>Coverage</b> to see the other half of that story — how unevenly the ocean has actually been sampled.''',
  '''Switch the colouring to <b>Temp</b> and the conveyor stops being a diagram — the Gulf Stream runs north at 24 °C in orange, the Labrador Current comes back past it at 3 °C in blue, and the engine is visible. Switch to <b>Coverage</b> for the other half of the story: how unevenly the ocean has actually been sampled.''')


def main():
    deck, ocean_js_path = sys.argv[1], sys.argv[2]
    dry = "--dry" in sys.argv

    src = open(deck, encoding="utf-8", newline="").read()
    ocean_js = open(ocean_js_path, encoding="utf-8").read()

    # Anchors are checked and applied in order against a working copy, so a
    # patch may anchor on text an earlier patch introduced. Nothing is written
    # unless every one of them matched exactly the number of times it claimed.
    out, fails, applied = src, [], []
    for name, anchor, new, count in PATCHES:
        n = out.count(anchor)
        if n != count:
            fails.append(f"  [{name}] matched {n} times, need {count}"
                         + ("   (depends on an earlier patch that did not apply)" if applied and n == 0 else ""))
            break
        out = out.replace(anchor, new, count)
        applied.append(name)
    if fails:
        print("ABORT — nothing written:")
        print("\n".join(fails))
        if applied:
            print(f"  applied cleanly before the failure: {', '.join(applied)}")
        raise SystemExit(2)
    for name in applied:
        print(f"  ok  {name}")
    out = patch_data(out, ocean_js)
    print("  ok  data")

    if dry:
        print(f"\ndry run — {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB, nothing written")
        return

    shutil.copyfile(deck, deck + ".bak")
    with open(deck, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    print(f"\nwritten {deck}  {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB  (backup at {deck}.bak)")


if __name__ == "__main__":
    main()
