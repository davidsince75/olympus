#!/usr/bin/env python3
"""
Olympus - the aurora you could only find by switching it off.

Two defects, one visible symptom.

1. The ramp was cut at round numbers.  `k = min(1,(v-3)/18)` and
   `alpha = 0.02 + 0.34k^2` were written for a field that reaches 18.  This
   record does not.  At Kp 1.33 the packed grids peak at 14 (north) and 16
   (south) and the median *drawn* cell is 5, so nine tenths of the oval was
   painted between alpha 0.02 and 0.05 under a `lighter` composite over a
   0.40-scrimmed photograph.  It was there.  It could not be seen.
   The ramp is now normalised on the record's own maximum, taken across both
   hemispheres so the twin discs stay comparable, and the alpha curve is
   lifted out of the quadratic that was crushing the mid-range.

2. Nothing moved.  The oval is one observation, but it is not fixed in
   longitude: OVATION is a pattern in magnetic local time and the Earth turns
   westward through it at 15 degrees an hour.  That is real, and far too slow
   to watch.  It is run here at x3600 - one turn in twenty-four seconds -
   labelled on the layer line and explained in the learning layer.  The grid
   is never altered; it is re-projected at a shifted longitude.

   On a polar stereographic disc a shift in longitude is *exactly* a rotation
   about the pole (r depends only on |lat|), so the disc sheet is still drawn
   once and simply turned - the spin costs nothing.  The globe has no such
   symmetry and must redraw, so its aurora sheet gets its own cache key with a
   quantised phase, split from the drift and footprint sheet which still does
   not move, and the quantisation step tunes itself on what the redraw costs
   on this machine.

Exact-string anchors, each must match exactly once or nothing is written.

  python build/patch_aurora.py dist/deck.html [--dry]
"""
import sys, os, shutil

EDITS = []


def edit(name, old, new):
    EDITS.append((name, old, new))


# ---------------------------------------------------------------- 1. constants
edit("aurora: spin, pulse and the field's own range",
"""const DAUR = {};
function deckAurora(S){""",
"""/* The oval is one frame - 2026-09-04T10:20Z - and it is not fixed in longitude.
   OVATION is a pattern in magnetic local time; what turns is the Earth, westward
   through it at 15 degrees an hour. Real, and far too slow to watch, so it is run
   at AUR_SPIN x real: one turn in twenty-four seconds. The grid is never altered,
   only re-projected at a shifted longitude, and the rate is stated on the layer
   line. The slow breathing on top of it is decoration and claims nothing. */
const AUR_SPIN = 3600;                       // x real time
const AUR_DEG_S = 15 * AUR_SPIN / 3600;      // degrees of longitude per second
const AUR_STILL = !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
function aurSpin(){ return AUR_STILL ? 0 : -((performance.now()/1000) * AUR_DEG_S) % 360; }
function aurPulse(){ return AUR_STILL ? 1 : 0.90 + 0.10*Math.sin(performance.now()/1000 * 2*Math.PI/6.5); }

/* A disc turns for free. The globe redraws, so its phase is quantised and the
   step is tuned by what the redraw actually costs here - the absolute figure is
   meaningless across machines, the differential is not. */
/* One degree of latitude by two of longitude is a visible quad at disc scale,
   and a grid of hard-edged rectangles is not what emission looks like. The sheet
   is softened once, when it is built, so the composite stays a single drawImage
   and the spin costs nothing extra. */
const AURB = document.createElement("canvas");
function aurSoften(cv, px){
  if(!(px >= 1)) return;
  const x = cv.getContext("2d");
  if(typeof x.filter !== "string") return;      // no filter here: leave it sharp
  if(AURB.width !== cv.width || AURB.height !== cv.height){ AURB.width = cv.width; AURB.height = cv.height; }
  const b = AURB.getContext("2d");
  b.setTransform(1,0,0,1,0,0);
  b.globalCompositeOperation = "copy";
  b.filter = "blur(" + px.toFixed(1) + "px)";
  b.drawImage(cv,0,0);
  b.filter = "none";
  b.globalCompositeOperation = "source-over";
  x.save();
  x.setTransform(1,0,0,1,0,0);
  x.globalCompositeOperation = "copy";
  x.drawImage(AURB,0,0);
  x.restore();
}

const AURQ = { step: 2, ema: 0 };
function aurCost(ms){
  AURQ.ema = AURQ.ema ? AURQ.ema*0.8 + ms*0.2 : ms;
  if(AURQ.ema > 5 && AURQ.step < 12) AURQ.step *= 2;
  else if(AURQ.ema < 1.5 && AURQ.step > 2) AURQ.step /= 2;
}

const AUR_CUT = 4;   // the low tail, so the oval reads as a band and not a disc
let AURTOP = 0;
/* The ramp is normalised on the record's own maximum, not on a round number,
   and the maximum is taken across both hemispheres so the twin discs can be
   compared with each other. */
function aurTop(){
  if(AURTOP) return AURTOP;
  let m = 0;
  for(const h of [false,true]){
    const g8 = deckAurora(h); if(!g8) continue;
    for(let i=0;i<g8.length;i++) if(g8[i] > m) m = g8[i];
  }
  return (AURTOP = Math.max(AUR_CUT + 1, m));
}

const DAUR = {};
function deckAurora(S){""")

# ------------------------------------------------------------ 2. the ramp + dlon
edit("aurora: ramp normalised on the field, colour exaggerated, longitude offset",
"""function drawDeckLiveRaw(g,cx,cy,s,S,part){
  if(part==="aur"){
    const A = LIVE.aurora, grid = st.lay.aur ? deckAurora(S) : null;
    if(!(A && grid)) return;
    const sgn = S ? -1 : 1, NB=10;
    const paths=[]; for(let b=0;b<NB;b++) paths.push(new Path2D());
    for(let li=0; li<A.nlat-1; li++){
      const lat = A.lat0 + li;
      for(let lo=0; lo<A.nlon; lo+=2){
        const v = Math.max(grid[li*A.nlon+lo], grid[li*A.nlon+((lo+1)%A.nlon)]);
        if(v < 4) continue;
        const k = Math.min(1,(v-3)/18);
        const b = Math.min(NB-1, Math.floor(k*NB));
        // a quad with any corner on the far side of the globe would be folded
        // back onto the near side, so it is dropped rather than drawn wrong
        const a0 = xy(g,cx,cy,s,S,sgn*lat,lo);        if(!LIVEVIS) continue;
        const a1 = xy(g,cx,cy,s,S,sgn*lat,lo+2);      if(!LIVEVIS) continue;
        const a2 = xy(g,cx,cy,s,S,sgn*(lat+1),lo+2);  if(!LIVEVIS) continue;
        const a3 = xy(g,cx,cy,s,S,sgn*(lat+1),lo);    if(!LIVEVIS) continue;
        const p=paths[b];
        p.moveTo(a0[0],a0[1]); p.lineTo(a1[0],a1[1]); p.lineTo(a2[0],a2[1]); p.lineTo(a3[0],a3[1]);
        p.closePath();
      }
    }
    g.globalCompositeOperation = "lighter";
    for(let b=0;b<NB;b++){
      const k=(b+0.5)/NB;
      g.fillStyle = `rgba(${Math.round(60+165*k*k)},${Math.round(226-70*k*k)},${Math.round(180+60*k)},${(0.02+0.34*k*k).toFixed(3)})`;
      g.fill(paths[b]);
    }
    g.globalCompositeOperation = "source-over";
    return;
  }""",
"""function drawDeckLiveRaw(g,cx,cy,s,S,part,dlon){
  if(part==="aur"){
    const A = LIVE.aurora, grid = st.lay.aur ? deckAurora(S) : null;
    if(!(A && grid)) return;
    const sgn = S ? -1 : 1, NB=10, dl = dlon || 0;
    // normalised on the record, not on a round number: (v-3)/18 assumed a field
    // that reaches 18 and this one reaches 16, which is why it was invisible
    const span = Math.max(1, aurTop() - AUR_CUT + 1);
    const paths=[]; for(let b=0;b<NB;b++) paths.push(new Path2D());
    for(let li=0; li<A.nlat-1; li++){
      const lat = A.lat0 + li;
      for(let lo=0; lo<A.nlon; lo+=2){
        const v = Math.max(grid[li*A.nlon+lo], grid[li*A.nlon+((lo+1)%A.nlon)]);
        if(v < AUR_CUT) continue;
        const k = Math.min(1,(v - AUR_CUT + 1)/span);
        const b = Math.min(NB-1, Math.floor(k*NB));
        // a quad with any corner on the far side of the globe would be folded
        // back onto the near side, so it is dropped rather than drawn wrong
        const a0 = xy(g,cx,cy,s,S,sgn*lat,lo+dl);        if(!LIVEVIS) continue;
        const a1 = xy(g,cx,cy,s,S,sgn*lat,lo+2+dl);      if(!LIVEVIS) continue;
        const a2 = xy(g,cx,cy,s,S,sgn*(lat+1),lo+2+dl);  if(!LIVEVIS) continue;
        const a3 = xy(g,cx,cy,s,S,sgn*(lat+1),lo+dl);    if(!LIVEVIS) continue;
        const p=paths[b];
        p.moveTo(a0[0],a0[1]); p.lineTo(a1[0],a1[1]); p.lineTo(a2[0],a2[1]); p.lineTo(a3[0],a3[1]);
        p.closePath();
      }
    }
    g.globalCompositeOperation = "lighter";
    for(let b=0;b<NB;b++){
      const k=(b+0.5)/NB;
      // 557.7 nm green low in the curtain, 630 nm red and N2+ violet at the top:
      // the ramp runs the way the emission does, exaggerated
      g.fillStyle = `rgba(${Math.round(40+215*Math.pow(k,1.4))},${Math.round(255-120*k*k)},${Math.round(120+105*Math.pow(k,1.5))},${(0.10+0.58*Math.pow(k,1.25)).toFixed(3)})`;
      g.fill(paths[b]);
    }
    g.globalCompositeOperation = "source-over";
    return;
  }""")

# ------------------------------------------------------------------- 3. the disc
edit("aurora: the disc softens its sheet, then spins it instead of rebuilding it",
"""    A.key=B.key=key;
  }
  g.save();
  g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();
  g.imageSmoothingEnabled=true;
  if(st.lay.aur){
    g.globalCompositeOperation="lighter";
    g.drawImage(A.cv,cx-s,cy-s,s*2,s*2);
    g.globalCompositeOperation="source-over";
  }
  g.drawImage(B.cv,cx-s,cy-s,s*2,s*2);
  g.restore();
}""",
"""    aurSoften(A.cv, Math.max(1, Math.round(s*dpr*0.010)));
    A.key=B.key=key;
  }
  g.save();
  g.beginPath(); g.arc(cx,cy,s,0,7); g.clip();
  g.imageSmoothingEnabled=true;
  if(st.lay.aur){
    // r depends only on |lat|, so on this projection a shift of d degrees in
    // longitude is exactly a rotation of d about the pole - mirrored in the
    // south, where the projection flips the sign of y. The sheet is drawn once
    // and turned; the spin costs a transform.
    g.save();
    g.globalCompositeOperation="lighter";
    g.globalAlpha=aurPulse();
    g.translate(cx,cy);
    g.rotate((S?1:-1)*aurSpin()*D);
    g.drawImage(A.cv,-s,-s,s*2,s*2);
    g.restore();
  }
  g.drawImage(B.cv,cx-s,cy-s,s*2,s*2);
  g.restore();
}""")

# ------------------------------------------------------------------ 4. the globe
edit("aurora: the globe rebuilds only the aurora sheet, on a quantised phase",
"""  const dpr=Math.min(2,window.devicePixelRatio||1);
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
}""",
"""  const dpr=Math.min(2,window.devicePixelRatio||1);
  const key=[GLB.cam, Math.round(s*dpr), st.lay.aur?1:0, st.lay.sar1?1:0,
             st.lay.drift?1:0, (st.driftX||1)].join("|");
  // An orthographic view has no rotational symmetry about the pole, so the
  // aurora cannot be spun the way the disc spins it - it has to be redrawn.
  // Its sheet therefore carries the phase in its own key, quantised, and is
  // split from the sheet that carries the drift and the footprints, which
  // still do not move and must not be redrawn with it.
  const phq = AUR_STILL ? 0 : Math.round(aurSpin()/AURQ.step)*AURQ.step;
  const keyA = key + "|" + phq;
  const A=globeLiveSheet("a",s,dpr), Bs=globeLiveSheet("b",s,dpr);
  const prev=LIVEP;
  // 0.02 rather than 0 keeps a vector from being drawn edge-on at the limb,
  // where an orthographic projection compresses it to nothing
  const gp=(lat,lon)=>{
    const q=gproj(lon,lat,B);
    LIVEVIS = q[2] > 0.02;
    return [s + q[0]*s, s - q[1]*s];
  };
  const paint=(sheet,part,dl)=>{
    LIVEP=gp;
    const x=sheet.cv.getContext("2d");
    x.setTransform(1,0,0,1,0,0);
    x.clearRect(0,0,sheet.cv.width,sheet.cv.height);
    x.setTransform(dpr,0,0,dpr,0,0);
    // both hemispheres: on a globe you can have the aurora of one and the
    // drift of the other on screen at once
    drawDeckLiveRaw(x,s,s,s,true,part,dl);
    drawDeckLiveRaw(x,s,s,s,false,part,dl);
    LIVEP=prev; LIVEVIS=true;
  };
  if(A.key!==keyA){
    const t0=performance.now();
    paint(A,"aur",phq);
    aurSoften(A.cv, Math.max(1, Math.round(s*dpr*0.010)));
    aurCost(performance.now()-t0);
    A.key=keyA;
  }
  if(Bs.key!==key){ paint(Bs,"rest",0); Bs.key=key; }
  g.save();
  g.imageSmoothingEnabled=true;
  if(st.lay.aur){
    g.globalCompositeOperation="lighter";
    g.globalAlpha=aurPulse();
    g.drawImage(A.cv,cx-s,cy-s,s*2,s*2);
    g.globalAlpha=1;
    g.globalCompositeOperation="source-over";
  }
  g.drawImage(Bs.cv,cx-s,cy-s,s*2,s*2);
  g.restore();
}""")

# ------------------------------------------------------------------- 5. the label
edit("aurora: the rate is stated on the layer line",
""" {id:"aur",  nm:"Auroral oval", src:"NOAA SWPC OVATION · model", on:true, ex:"ovation"},""",
""" {id:"aur",  nm:"Auroral oval", src:"NOAA SWPC OVATION · model · one frame, turned ×3600", on:true, ex:"ovation"},""")

# -------------------------------------------------------------- 6. the explainer
edit("aurora: the learning layer says what the motion is and is not",
"""ovation:{k:"ins",t:"The aurora is a forecast",
 b:"Not a photograph, and stamped <b>MODEL</b> for that reason. A spacecraft at L1, 1.5 million km upstream, measures the solar wind speed and the interplanetary magnetic field; OVATION-Prime turns those into the energy flux of particles precipitating into the atmosphere, from which a viewing probability follows. The roughly half-hour lead time is nothing more than how long the solar wind takes to cross the remaining distance to Earth.",
 p:"NOAA SWPC OVATION-Prime 30-minute forecast. Packed here as two 360 × 46 grids from 45° poleward."},""",
"""ovation:{k:"ins",t:"The aurora is a forecast",
 b:"Not a photograph, and stamped <b>MODEL</b> for that reason. A spacecraft at L1, 1.5 million km upstream, measures the solar wind speed and the interplanetary magnetic field; OVATION-Prime turns those into the energy flux of particles precipitating into the atmosphere, from which a viewing probability follows. The roughly half-hour lead time is nothing more than how long the solar wind takes to cross the remaining distance to Earth.<br><br>What you see turning is not the oval. OVATION is a pattern in <b>magnetic local time</b>, anchored to the Sun rather than to the ground, and the Earth rotates westward through it at 15° an hour. That is real and far too slow to watch, so it is run here at <b>×3600</b> — one turn in twenty-four seconds. The grid itself is never altered; it is re-projected at a shifted longitude. The slow breathing of the brightness is decoration and means nothing.<br><br>The colour is <b>stretched</b>, and deliberately. This frame was taken at <b>Kp 1.33</b> — a very quiet sky — and peaks at 16 on the forecast's own 0–100 scale. Drawn at true scale it is a rumour. The ramp is normalised on this record's own maximum across both hemispheres, so the two discs can be read against each other but <i>not</i> against a storm.",
 p:"NOAA SWPC OVATION-Prime 30-minute forecast. Packed here as two 360 × 46 grids from 45° poleward. One frame, held; the turn is the Earth's, at ×3600; the brightness ramp is normalised on this frame's own maximum, not on an absolute scale."},""")


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    deck = sys.argv[1]
    dry = "--dry" in sys.argv
    src = open(deck, encoding="utf-8", newline="").read()
    out = src
    for name, old, new in EDITS:
        n = out.count(old)
        if n != 1:
            raise SystemExit(f"ABORT - anchor '{name}' matched {n} times, need exactly 1. Nothing written.")
        out = out.replace(old, new, 1)
        print(f"  ok  {name}")
    if dry:
        print(f"dry run - {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB, nothing written")
        return
    shutil.copyfile(deck, deck + ".preaurora")
    open(deck, "w", encoding="utf-8", newline="").write(out)
    print(f"written {deck}  {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB")


if __name__ == "__main__":
    main()
