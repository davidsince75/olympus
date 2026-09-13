"""
patch_globe_surface — make the globe draw what its own switches promise.

The globe was a wireframe with an ice shell. `drawGlobe` had no equivalent of
`drawDeckBase` and never called `drawDeckLive`, so five controls that stayed on
screen in GLOBE did nothing when pressed: Relief, Today, the auroral oval, the
sea-ice drift field and its x1/x5/x15 exaggeration, and the SAR footprints. A
sixth was mis-wired: `drawSitesGlobe` draws the station network, and it was only
called when the deep-limb layer was on, so turning the limbs off took the
stations with it.

Nine substitutions, each required, each anchored on an exact string that must
match exactly once or the script aborts without writing.

  1  SATIMG                 one global plate carree sheet per layer, with its
                            own provenance, alongside the two polar squares
  2  preloadImagery         load that sheet; drop an onload hook that called a
                            function named `paint`, which does not exist
  3  xy()                   take a projector from the view that is drawing, and
                            report whether the point it returned is visible
  4  drawDeckLiveRaw        cull points the globe's far side hides
  5  globeShell             do not paint the land slab over the photograph
  6  globe surface block    the per-cell resampler, the photograph, the living
                            layer on the globe
  7  drawGlobe              draw both, in the right order
  8  drawSitesGlobe         the stations answer to the station switch
  9  copy                   layer source line and three explainers

Usage
    python3 build/patch_globe_surface.py --deck src/deck.html --out dist/deck.html
                                         --imagery data/imagery
"""

import argparse
import base64
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITS = []


def sub(label, old, new):
    EDITS.append((label, old, new))


def apply_all(src):
    for label, old, new in EDITS:
        n = src.count(old)
        if n != 1:
            raise SystemExit(f"{label}: expected exactly one match, found {n}")
        src = src.replace(old, new)
        print(f"  {label}: applied")
    return src


# ---------------------------------------------------------------- 2. preload
sub("preloadImagery", """(function preloadImagery(){
  if(typeof SATIMG === "undefined" || !SATIMG || !SATIMG.layers) return;
  for(const L of SATIMG.layers){
    for(const hemi of Object.keys(L.data || {})){
      const im = new Image();
      im.onload = () => { try{ paint(); }catch(e){} };
      im.src = L.data[hemi];
      DIMGS[L.key + hemi] = im;
    }
  }
})();""", """(function preloadImagery(){
  if(typeof SATIMG === "undefined" || !SATIMG || !SATIMG.layers) return;
  for(const L of SATIMG.layers){
    for(const hemi of Object.keys(L.data || {})){
      const im = new Image();
      im.src = L.data[hemi];
      DIMGS[L.key + hemi] = im;
    }
    // the globe's sheet: plate carree and global, because an orthographic view
    // sees past the edge of a polar square
    if(L.g){ const im = new Image(); im.src = L.g; DIMGS[L.key + "G"] = im; }
  }
  // there is no repaint hook here: the deck redraws every frame anyway, and the
  // one that used to be here called a function named `paint` that does not exist.
})();""")

# ------------------------------------------------------------------- 3. xy()
sub("xy projector", """function xy(g,cx,cy,s,S,lat,lon){
  const p = proj(lon,lat,S);
  return [cx + p[0]*s, cy - p[1]*s];
}""", """/* The living layer is written once, in latitude and longitude. Which view
   projects it is the view's business: a polar disc has no far side and can
   answer for every point it is given, the globe has one and must say so.
   LIVEP is the current view's projector; LIVEVIS is its answer about the point
   it just returned. A disc leaves LIVEP null and LIVEVIS true. */
let LIVEP=null, LIVEVIS=true;
function xy(g,cx,cy,s,S,lat,lon){
  if(LIVEP) return LIVEP(lat,lon);
  LIVEVIS = true;
  const p = proj(lon,lat,S);
  return [cx + p[0]*s, cy - p[1]*s];
}""")

# -------------------------------------------------------- 4. drawDeckLiveRaw
sub("aurora culling", """        const a0 = xy(g,cx,cy,s,S,sgn*lat,lo),      a1 = xy(g,cx,cy,s,S,sgn*lat,lo+2);
        const a2 = xy(g,cx,cy,s,S,sgn*(lat+1),lo+2), a3 = xy(g,cx,cy,s,S,sgn*(lat+1),lo);
        const p=paths[b];""", """        // a quad with any corner on the far side of the globe would be folded
        // back onto the near side, so it is dropped rather than drawn wrong
        const a0 = xy(g,cx,cy,s,S,sgn*lat,lo);        if(!LIVEVIS) continue;
        const a1 = xy(g,cx,cy,s,S,sgn*lat,lo+2);      if(!LIVEVIS) continue;
        const a2 = xy(g,cx,cy,s,S,sgn*(lat+1),lo+2);  if(!LIVEVIS) continue;
        const a3 = xy(g,cx,cy,s,S,sgn*(lat+1),lo);    if(!LIVEVIS) continue;
        const p=paths[b];""")

sub("SAR culling", """      const pts = it.poly.map(([lon,lat]) => xy(g,cx,cy,s,S,lat,lon));
      if(pts.length < 3) continue;""", """      let vis = true;
      const pts = it.poly.map(([lon,lat]) => {
        const q = xy(g,cx,cy,s,S,lat,lon); if(!LIVEVIS) vis = false; return q;
      });
      if(!vis || pts.length < 3) continue;""")

sub("drift culling", """      const p = xy(g,cx,cy,s,S,la0,lo0), q0 = xy(g,cx,cy,s,S,la1,lo1);
      const qx = p[0] + (q0[0]-p[0])*X, qy = p[1] + (q0[1]-p[1])*X;""", """      const p  = xy(g,cx,cy,s,S,la0,lo0); if(!LIVEVIS) continue;
      const q0 = xy(g,cx,cy,s,S,la1,lo1); if(!LIVEVIS) continue;
      const qx = p[0] + (q0[0]-p[0])*X, qy = p[1] + (q0[1]-p[1])*X;""")

# --------------------------------------------------------------- 5. globeShell
# The photograph must be registered to the same camera as the ice shell, and the
# LUT's camera is throttled while the globe is being dragged. Record it.
sub("globeLUT records its camera",
    "  GLB.cam=key; GLB.n=n; GLB.lut={near,far,landN,landF,disc,n};",
    "  GLB.cam=key; GLB.n=n; GLB.clat=lat0; GLB.clon=lon0;\n"
    "  GLB.lut={near,far,landN,landF,disc,n,tu,tv};")

# The lookup table already pays for an asin and an atan2 per cell per side. The
# photograph needs the near side's latitude and longitude and nothing else, so
# it is taken here rather than computed a second time.
sub("globeLUT allocates texture coordinates",
    "  const landN=new Uint8Array(n*n), landF=new Uint8Array(n*n), disc=new Uint8Array(n*n);",
    "  const landN=new Uint8Array(n*n), landF=new Uint8Array(n*n), disc=new Uint8Array(n*n);\n"
    "  const tu=new Float32Array(n*n).fill(-1), tv=new Float32Array(n*n);")

sub("globeLUT fills texture coordinates",
    "        if(isLand(lat,lon)) (side?landF:landN)[k]=1;",
    "        if(isLand(lat,lon)) (side?landF:landN)[k]=1;\n"
    "        if(!side){ tu[k]=(lon+180)/360; tv[k]=(90-lat)/180; }")

sub("globeShell land slab", """function globeShell(which,n){
  const L=GLB.lut[which], LD=GLB.lut[which==="near"?"landN":"landF"];
  const d=GLB.img.data, rgb=[0,0,0];
  const sh=CURF.sh, nh=CURF.nh;
  for(let k=0;k<n*n;k++){
    const o=k*4, v=L[k];
    if(LD[k]){ d[o]=46; d[o+1]=65; d[o+2]=82; d[o+3]=255; continue; }""",
"""function globeShell(which,n,photo){
  const L=GLB.lut[which], LD=GLB.lut[which==="near"?"landN":"landF"];
  const d=GLB.img.data, rgb=[0,0,0];
  const sh=CURF.sh, nh=CURF.nh;
  // The flat land slab exists because there is otherwise nothing under the ice.
  // With the photograph in place it is worse than redundant: on the near side
  // the land is already in the picture, and on the far side the slab washes a
  // continent-shaped grey over the photograph — Greenland and Siberia tinting
  // Antarctica. The far side still reads, through its ice and its coastlines.
  const slab = !photo;
  for(let k=0;k<n*n;k++){
    const o=k*4, v=L[k];
    if(LD[k]){ if(slab){ d[o]=46; d[o+1]=65; d[o+2]=82; d[o+3]=255; } else d[o+3]=0; continue; }""")

# ------------------------------------------------- 6. the globe surface block
SURFACE = r'''
/* ---------------- the globe's own surface ----------------
   A disc draws a baked polar square and is done: the square was reprojected at
   build time onto the same grid the disc draws, so it aligns by construction.
   An orthographic globe cannot do that. Every screen cell is its own latitude
   and longitude, so the picture has to be resampled per cell, and the source
   has to be global — the polar squares stop at r = rmax, which is latitude 33 N
   and 26 S, and on a globe that is a bare band across the tropics rather than a
   frame you never see past. So the globe gets its own plate carree sheet,
   fetched at build time from the same GIBS layer as the squares.

   Two costs are managed here rather than paid every frame. The per-cell table
   of texture coordinates is an asin and an atan2 per cell, so it is cached on
   the camera and run coarse while the camera moves and fine once it stops. The
   decoded sheet is several megabytes, so only the layer being drawn is held. */

const GSURF={key:"", n:0, tu:null, tv:null};
const NIMG_STILL=768;

function globeSurf(n,lat0,lon0){
  const key=n+"|"+lat0.toFixed(2)+"|"+lon0.toFixed(2);
  if(GSURF.key===key) return GSURF;
  const {f,r,u}=globeBasis(lat0,lon0);
  const tu=new Float32Array(n*n), tv=new Float32Array(n*n);
  for(let j=0;j<n;j++){
    const sy=1-(j+0.5)/n*2;
    for(let i=0;i<n;i++){
      const sx=(i+0.5)/n*2-1, rho2=sx*sx+sy*sy, k=j*n+i;
      if(rho2>1){ tu[k]=-1; continue; }
      const z=Math.sqrt(1-rho2);
      const X=sx*r[0]+sy*u[0]+z*f[0];
      const Y=sx*r[1]+sy*u[1]+z*f[1];
      const Z=sx*r[2]+sy*u[2]+z*f[2];
      const lat=Math.asin(Math.max(-1,Math.min(1,Z)))/D;
      const lon=Math.atan2(Y,X)/D;
      tu[k]=(lon+180)/360; tv[k]=(90-lat)/180;
    }
  }
  GSURF.key=key; GSURF.n=n; GSURF.tu=tu; GSURF.tv=tv;
  return GSURF;
}

// the layer's global sheet, decoded once into something that can be sampled
const GTEX={key:"", w:0, h:0, d:null};
function globeTex(L){
  if(GTEX.key===L.key && GTEX.d) return GTEX;
  const im=DIMGS[L.key+"G"];
  if(!im || !im.complete || !im.naturalWidth) return null;
  const c=document.createElement("canvas");
  c.width=im.naturalWidth; c.height=im.naturalHeight;
  const x=c.getContext("2d",{willReadFrequently:true});
  x.drawImage(im,0,0);
  GTEX.key=L.key; GTEX.w=c.width; GTEX.h=c.height;
  GTEX.d=x.getImageData(0,0,c.width,c.height).data;
  c.width=c.height=0;
  return GTEX;
}

/* Two sheets, coarse and fine. The coarse one is at the ice shell's own
   resolution and is built inline: it is the picture you drag. The fine one is
   fifteen times the work, so it is built in a task *between* frames rather than
   inside one, and only once the camera has stopped — so letting go of the globe
   sharpens the photograph instead of dropping a frame.

   Both are keyed on GLB.clat/GLB.clon, the camera the ice shell's lookup table
   was built for, not the live camera. While the globe is being dragged that
   table is deliberately held, and the photograph must be held with it or the
   two would be registered to different views. */
const GIMG={coarse:null, fine:null, pend:0};
function gimgSlot(which,n){
  let sl=GIMG[which];
  if(!sl){ sl=GIMG[which]={cv:document.createElement("canvas"), cx:null, img:null, key:""}; }
  if(sl.cv.width!==n){
    sl.cv.width=sl.cv.height=n;
    sl.cx=sl.cv.getContext("2d");
    sl.img=sl.cx.createImageData(n,n);
    sl.key="";
  }
  if(!sl.cx){ sl.cx=sl.cv.getContext("2d"); sl.img=sl.cx.createImageData(n,n); }
  return sl;
}
function globeImgBuild(L,n,which,key,lat0,lon0){
  const T=globeTex(L); if(!T) return null;
  const sl=gimgSlot(which,n);
  // at the lookup table's own resolution the coordinates are already computed
  const SF=(n===GLB.n && GLB.lut && GLB.lut.tu) ? GLB.lut : globeSurf(n,lat0,lon0);
  const d=sl.img.data, td=T.d, tw=T.w, th=T.h;
  for(let k=0;k<n*n;k++){
    const o=k*4, uu=SF.tu[k];
    if(uu<0){ d[o+3]=0; continue; }
    let px=(uu*tw)|0; if(px>=tw) px=tw-1; if(px<0) px=0;
    let py=(SF.tv[k]*th)|0; if(py>=th) py=th-1; if(py<0) py=0;
    const t=(py*tw+px)*4;
    d[o]=td[t]; d[o+1]=td[t+1]; d[o+2]=td[t+2]; d[o+3]=255;
  }
  sl.cx.putImageData(sl.img,0,0);
  sl.key=key+"|"+n;
  return sl;
}

/* The photograph goes on before everything else, in place of the flat body
   fill, and the far-side passes are drawn over it at their own low alphas — so
   the planet stays translucent and the far pole still shows through it. The
   scrim that pushes the picture back behind the measurements is applied in the
   body-fill slot, where the flat fill used to be, so both views dim it the
   same way. */
function drawGlobeBase(g,cx,cy,s,n,nFine){
  if(!st.lay.sat) return false;
  const L=deckBaseLayer(); if(!L || !L.g) return false;
  if(!globeTex(L)) return false;
  if(GLB.clat===undefined) return false;
  const lat0=GLB.clat, lon0=GLB.clon;
  const key=L.key+"|"+lat0.toFixed(2)+"|"+lon0.toFixed(2);
  let cv=null;
  if(nFine && GIMG.fine && GIMG.fine.key===key+"|"+nFine) cv=GIMG.fine.cv;
  if(!cv){
    let sl=GIMG.coarse;
    if(!sl || sl.key!==key+"|"+n) sl=globeImgBuild(L,n,"coarse",key,lat0,lon0);
    if(!sl) return false;
    cv=sl.cv;
    if(nFine && nFine>n && !GIMG.pend){
      GIMG.pend=setTimeout(()=>{ GIMG.pend=0;
        try{ globeImgBuild(L,nFine,"fine",key,lat0,lon0); }catch(e){} }, 0);
    }
  }
  g.save();
  g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();
  g.imageSmoothingEnabled=true; g.imageSmoothingQuality="high";
  g.drawImage(cv,cx-s,cy-s,s*2,s*2);
  g.restore();
  return true;
}

/* The living layer on the globe: the same data and the same code as the disc,
   with a different projector. It is sheeted and composited exactly as the disc
   does it, and keyed on GLB.cam — the ice shell's own camera key — so the two
   are rebuilt on the same tick and can never be registered to different views. */
const GLIVE={};
function globeLiveSheet(which,s,dpr){
  let c=GLIVE[which];
  const w=Math.max(2,Math.round(s*2*dpr));
  if(!c){ c={cv:document.createElement("canvas")}; GLIVE[which]=c; }
  if(c.cv.width!==w){ c.cv.width=c.cv.height=w; c.key=null; }
  return c;
}
function drawDeckLiveGlobe(g,B,cx,cy,s){
  if(typeof LIVE === "undefined" || !LIVE) return;
  if(!(st.lay.aur || st.lay.sar1 || st.lay.drift)) return;
  const dpr=Math.min(2,window.devicePixelRatio||1);
  const key=[GLB.cam, Math.round(s*dpr), st.lay.aur?1:0, st.lay.sar1?1:0,
             st.lay.drift?1:0, (st.driftX||1)].join("|");
  const A=globeLiveSheet("a",s,dpr), Bs=globeLiveSheet("b",s,dpr);
  if(A.key!==key){
    const prev=LIVEP;
    // 0.02 rather than 0 keeps a vector from being drawn edge-on at the limb,
    // where an orthographic projection compresses it to nothing
    LIVEP=(lat,lon)=>{
      const q=gproj(lon,lat,B);
      LIVEVIS = q[2] > 0.02;
      return [s + q[0]*s, s - q[1]*s];
    };
    for(const [sheet,part] of [[A,"aur"],[Bs,"rest"]]){
      const x=sheet.cv.getContext("2d");
      x.setTransform(1,0,0,1,0,0);
      x.clearRect(0,0,sheet.cv.width,sheet.cv.height);
      x.setTransform(dpr,0,0,dpr,0,0);
      // both hemispheres: on a globe you can have the aurora of one and the
      // drift of the other on screen at the same time
      drawDeckLiveRaw(x,s,s,s,true,part);
      drawDeckLiveRaw(x,s,s,s,false,part);
    }
    LIVEP=prev; LIVEVIS=true;
    A.key=Bs.key=key;
  }
  g.save();
  g.imageSmoothingEnabled=true;
  if(st.lay.aur){
    g.globalCompositeOperation="lighter";
    g.drawImage(A.cv,cx-s,cy-s,s*2,s*2);
    g.globalCompositeOperation="source-over";
  }
  g.drawImage(Bs.cv,cx-s,cy-s,s*2,s*2);
  g.restore();
}

function drawGlobe(g,cx,cy,s0,w,h){'''

sub("globe surface block", "\nfunction drawGlobe(g,cx,cy,s0,w,h){", SURFACE)

# ----------------------------------------------------------------- 7. drawGlobe
sub("globe: photograph first", """  g.fillStyle=og; g.fillRect(cx-s,cy-s,s*2,s*2);

  // ---- far shell, seen through the body of the Earth""",
"""  g.fillStyle=og; g.fillRect(cx-s,cy-s,s*2,s*2);

  // ---- the photograph, resampled per screen cell. Coarse while the camera is
  //      moving, at the ice shell's own resolution; fine once it stops.
  const photo = drawGlobeBase(g,cx,cy,s, n, moving ? 0 :
    Math.max(n, Math.min(NIMG_STILL,
      Math.round(s*2*Math.min(2,window.devicePixelRatio||1)))));

  // ---- far shell, seen through the body of the Earth""")

sub("globe: body fill", """  // ---- the Earth itself, translucent
  g.fillStyle="rgba(7,16,24,.62)"; g.beginPath(); g.arc(cx,cy,s,0,7); g.fill();""",
"""  // ---- the Earth itself, translucent. With the photograph on, this is the
  //      scrim that keeps the measurements the brightest thing on screen —
  //      the same 0.40-ish veil the disc views put over their own imagery.
  g.fillStyle = photo ? "rgba(6,12,20,.44)" : "rgba(7,16,24,.62)";
  g.beginPath(); g.arc(cx,cy,s,0,7); g.fill();""")

sub("globe: near shell", """    g.drawImage(globeShell("near",n),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;""",
"""    g.drawImage(globeShell("near",n,photo),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;""")

sub("globe: far shell", """    g.drawImage(globeShell("far",n),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;""",
"""    g.drawImage(globeShell("far",n,photo),cx-s,cy-s,s*2,s*2); g.globalAlpha=1;""")

sub("globe: living layer and sites", """  // ---- near coastlines
  g.beginPath();
  for(const ring of EX.coast){ gpathTo(g,ring,B,cx,cy,s,true); }
  g.strokeStyle="rgba(140,168,190,.72)"; g.lineWidth=0.9; g.stroke();

  if(st.lay.deep) drawSitesGlobe(g,B,cx,cy,s);""",
"""  // ---- the living layer: aurora, SAR footprints, ice drift
  drawDeckLiveGlobe(g,B,cx,cy,s);

  // ---- near coastlines
  g.beginPath();
  for(const ring of EX.coast){ gpathTo(g,ring,B,cx,cy,s,true); }
  g.strokeStyle="rgba(140,168,190,.72)"; g.lineWidth=0.9; g.stroke();

  drawSitesGlobe(g,B,cx,cy,s);""")

# ------------------------------------------------------------ 8. drawSitesGlobe
sub("stations off the deep switch", """function drawSitesGlobe(g,B,cx,cy,s){
  const pulse=0.5+0.5*Math.sin(performance.now()/620), labels=[];
  for(const site of EX.sites){""",
"""function drawSitesGlobe(g,B,cx,cy,s){
  const pulse=0.5+0.5*Math.sin(performance.now()/620), labels=[];
  // The formation sites belong to the deep layer and the stations below belong
  // to the station layer. They were sharing one switch, so turning the limbs
  // off took the station network off the globe with them.
  for(const site of (st.lay.deep ? EX.sites : [])){""")

# ------------------------------------------------------------------- 9. copy
sub("sat layer source line",
    'src:"NASA GIBS · EPSG:3413 native · 3031→3976 south"',
    'src:"NASA GIBS · EPSG:3413 native · 3031→3976 south · plate carrée on the globe"')

sub("mode_globe explainer",
    "the ocean currents are drawn everywhere the drifters went.\",",
    "the ocean currents are drawn everywhere the drifters went. The base imagery here is not "
    "the polar squares the discs draw — those stop at 33°N and 26°S — but one global plate "
    "carrée sheet of the same GIBS layer, resampled per screen cell, coarse while you are "
    "dragging and fine once you let go.\",")

sub("bluemarble explainer provenance",
    'p:"NASA GIBS BlueMarble_ShadedRelief_Bathymetry. A composite with no date, and no time '
    'dimension in the service."}',
    'p:"NASA GIBS BlueMarble_ShadedRelief_Bathymetry. A composite with no date, and no time '
    'dimension in the service. Two polar squares for the discs, one global plate carrée sheet '
    'for the globe — same layer, three reprojections, recorded in data/imagery."}')

sub("truecolor explainer",
    "It is a near-real-time product, not the science-grade surface reflectance.\",",
    "It is a near-real-time product, not the science-grade surface reflectance. The discs show "
    "<b>one day</b>: near the poles Terra’s orbits converge and overlap, so a day is complete "
    "there. The globe cannot be — at the equator consecutive orbits leave un-imaged wedges "
    "between them, 11 % of the tropics in a single day — so its sheet is composited over "
    "<b>two days</b>, each pixel taken from the more recent day that imaged it. Two is what it "
    "takes; more would only age the picture. What is still black is <b>polar night</b>, and no "
    "number of days will fill that.\",")

# ------------------------------------------------------------- 10. dead code
sub("dead schematic SAR block", """  if(st.lay.sar){
    g.strokeStyle="rgba(200,128,47,.55)"; g.lineWidth=1; g.setLineDash([3,3]);
    for(let k=0;k<5;k++){
      const a=(now*0.06+k*0.4)%(Math.PI*2);
      g.save(); g.translate(cx,cy); g.rotate(a);
      g.strokeRect(-0.10*s, 0.24*s, 0.20*s, 0.30*s); g.restore();
    }
    g.setLineDash([]);
  }
""", """  // (a schematic SAR block used to sit here, switched on `st.lay.sar`. There is
  //  no layer with that id — it is `sar1`, and it draws real footprints — so the
  //  block had been unreachable since the real one landed.)
""")

# The imagery date readout and the feed row both read `L.day`. There is no such
# field on a layer: the manifest puts the observation date on `time`, and `day`
# lives on SATIMG itself, so the true-colour layer has always reported itself as
# a static composite with no date.
sub("imagery date, first paint",
    '{ const L0 = deckBaseLayer(); const el=$("#imgDay"); if(el) el.textContent = (L0 && L0.day) ? L0.day : "static composite"; }',
    'imgNote();')

sub("imagery date, on switch",
    '{ const L = deckBaseLayer(); $("#imgDay").textContent = (L && L.day) ? L.day : "static composite"; }',
    'imgNote();')

# The readout must say what is on screen. The polar squares are one day: near the
# poles Terra's orbits converge and overlap, so a day is complete there. The
# globe's sheet is composited over two, because at the equator consecutive orbits
# leave un-imaged wedges between them. Reporting "one day" while drawing two would
# be the same class of error as the `day` field this used to read.
sub("imgNote",
    "function projLabel(){",
    """function imgNote(){
  const el=$("#imgDay"); if(!el) return;
  const L=deckBaseLayer();
  if(!L){ el.textContent=""; return; }
  const gd = (st.mode==="GLOBE" && st.lay.sat && L.gdays && L.gdays.length>1) ? L.gdays : null;
  el.textContent = gd ? (gd[gd.length-1]+" \u2192 "+gd[0]+" \u00b7 "+gd.length+"-day composite")
                      : (L.time ? L.time : "static composite");
}
function projLabel(){""")

sub("imgNote follows the view",
    "  projLabel();\n\n  // the stream describes the month on screen, so it moves with it",
    "  projLabel(); imgNote();\n\n  // the stream describes the month on screen, so it moves with it")

sub("imagery date, feed row",
    'if(bl)       F.push(["GIBS imagery", bl.day || "static", "live", bl.key === "today" ? "truecolor" : "bluemarble"]);',
    'if(bl)       F.push(["GIBS imagery", bl.time || "static", "live", bl.key === "today" ? "truecolor" : "bluemarble"]);')

sub("dead scale variable",
    "    const rPix=76/st.s, km=rPix*areaW(0.5)>0?0:0;",
    "    const rPix=76/st.s;")


def data_uri(path):
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("ascii")


def patch_satimg(src, img_dir):
    pat = re.compile(r"^const SATIMG = (.*?);\s*$", re.M)
    hits = list(pat.finditer(src))
    if len(hits) != 1:
        raise SystemExit(f"SATIMG: expected one declaration, found {len(hits)}")
    sat = json.loads(hits[0].group(1))
    man = json.load(io.open(os.path.join(img_dir, "manifest_global.json"), encoding="utf-8"))
    bykey = {r["layer"]: r for r in man["images"]}
    added = []
    for L in sat["layers"]:
        rec = bykey.get(L["key"])
        if not rec:
            raise SystemExit(f"no global sheet for layer {L['key']}")
        L["g"] = data_uri(os.path.join(img_dir, rec["file"]))
        L["gw"] = rec["width"]
        L["gh"] = rec["height"]
        L["gdays"] = rec.get("days") or ([rec["time"]] if rec.get("time") else [])
        L["gsrc"] = {"projection": rec["projection"], "time": rec["time"],
                     "days": rec.get("days"), "composite": rec.get("composite"),
                     "unimaged_fraction": rec.get("unimaged_fraction"),
                     "bytes": rec["bytes"], "sources": rec.get("sources") or rec.get("source")}
        nd = len(L["gdays"])
        added.append(f"{L['key']} {rec['width']}x{rec['height']} {rec['bytes']/1024:.0f} KB"
                     + (f" ({nd}-day composite)" if nd > 1 else ""))
    sat["note"] = sat["note"] + (
        " The globe cannot use either square — they stop at r = rmax, latitude 33 N and 26 S — "
        "so it is drawn from a global EPSG:4326 sheet of the same GIBS layer, resampled per "
        "screen cell. A single day of MODIS Terra is complete on the polar squares, where the "
        "orbits converge, and is not complete globally, so the timed global sheet is composited "
        "over two days - each pixel from the more recent day that imaged it. What remains black "
        "is polar night.")
    sj = json.dumps(sat, separators=(",", ":"))
    m = hits[0]
    out = src[:m.start()] + f"const SATIMG = {sj};" + src[m.end():]
    print("  SATIMG: + " + "; ".join(added))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", default=os.path.join(ROOT, "src", "deck.html"))
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "deck.html"))
    ap.add_argument("--imagery", default=os.path.join(ROOT, "data", "imagery"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = io.open(args.deck, encoding="utf-8").read()
    print(f"in  {args.deck}  {len(src)/1024/1024:.2f} MB")
    out = apply_all(src)
    out = patch_satimg(out, args.imagery)

    for stale in ("if(st.lay.sar){", "try{ paint(); }"):
        if stale in out:
            raise SystemExit(f"still present after patch: {stale}")

    if args.dry_run:
        print("dry run — nothing written")
        return
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with io.open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    size = os.path.getsize(args.out)
    print(f"out {args.out}  {size/1024/1024:.2f} MB")
    if size > 16 * 1024 * 1024:
        print("WARNING: over the 16 MB artifact ceiling", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
