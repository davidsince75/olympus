/* ============================ deck: the ocean circulation plane ============================
   Three registers, kept apart, each with its own observation time:

     FLOW    MEASURED   near-surface velocity, NOAA Global Drifter Program climatology.
                        Particles are advected through the real field. Annual mean:
                        it does not move with the scrubber, and says so.
     FRONTS  MEASURED   five ACC frontal axes, Park & Durand, from the CNES-CLS18 MDT.
     DEEP    SCHEMATIC  the deep and bottom limbs. Gateways real, path illustration.
                        Animation speed driven by the observed monthly RAPID value.

   The deep limbs carry a depth per vertex and are drawn at that depth inside the
   translucent globe, at the vertical exaggeration stated in OCEAN.depth.exag.
   ========================================================================================= */

const OC = {
  ready:false, w:0, h:0, u:null, v:null, nobs:null, ok:null,
  sdu:null, sdv:null, sok:null, sw:0, sh:0, slon0:0, slat0:0, sdd:1, samax:1.6,
  tmp:null, tok:null, tw:0, th:0, tlon0:0, tlat0:0, tdd:0.5, tmin:-2, tmax:34,
  mon:0, monA:0, monB:0, monF:0, monObs:true,
  lon0:0, lat0:0, dd:0.25, vmax:1.5,
  P:0, plon:null, plat:null, page:null, pspd:null, pdns:null, ptmp:null,
  TR:9, trail:null, thead:0, nPart:0, pacc:0,
  lastT:0, seeded:false, warm:0, drawn:0, frameMs:0
};

/* Flow is played at a fixed, stated rate: GAIN degrees of great circle per
   second of wall clock, per m/s of current. It is a display rate and not a
   measurement, and it is the only number here that was chosen by eye.

   Two timescales, because they do different jobs. The particle advances every
   frame, so the motion is smooth. Its trail is a decimated history, pushed
   every OC_PUSH seconds, so a short trail can still span a long enough stretch
   of ocean to be visible — at 60 Hz an undecimated seven-frame trail on the
   Gulf Stream is about two pixels long, which is why the first version of this
   layer drew nothing but grain. */
const OC_GAIN = 14;
const OC_PUSH = 1/14;
const OC_DAYS_PER_SEC = +(OC_GAIN * 111320 / 86400).toFixed(0);

function ocReduced(){
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; }
  catch(e){ return false; }
}

/* ---------------- decode the measured velocity field ---------------- */
function ocLoad(){
  if(OC.ready || OC.loading) return;
  OC.loading = true;
  const F = OCEAN.flow;
  const im = new Image();
  im.src = F.png;
  const finish = () => {
    try{
      const cv = document.createElement("canvas");
      cv.width = F.w; cv.height = F.h;
      const cx = cv.getContext("2d",{willReadFrequently:true});
      cx.drawImage(im,0,0);
      const px = cx.getImageData(0,0,F.w,F.h).data;
      const n = F.w*F.h;
      const u = new Float32Array(n), v = new Float32Array(n);
      const nobs = new Uint8Array(n), ok = new Uint8Array(n);
      for(let k=0;k<n;k++){
        const o=k*4;
        if(px[o+3] < 128){ continue; }
        const eu=(px[o]-128)/127, ev=(px[o+1]-128)/127;
        u[k] = Math.sign(eu)*eu*eu*F.vmax;
        v[k] = Math.sign(ev)*ev*ev*F.vmax;
        nobs[k] = px[o+2];
        ok[k] = 1;
      }
      OC.w=F.w; OC.h=F.h; OC.u=u; OC.v=v; OC.nobs=nobs; OC.ok=ok;
      OC.lon0=F.lon0; OC.lat0=F.lat0; OC.dd=F.d; OC.vmax=F.vmax;
      cv.width=cv.height=0;
      OC.ready=true;
      OCEAN.flow.png=null;            // release the base64 once decoded
      ocSeed();
      sync();
      ocLoadSeasonal();               // the season arrives after the mean, never before
      ocLoadSST();
    }catch(e){ OC.err=String(e); }
  };
  if(im.decode) im.decode().then(finish).catch(()=>{ im.onload=finish; im.onerror=finish; });
  else { im.onload=finish; im.onerror=finish; }
}

/* The seasonal sheet: twelve climatological months as an anomaly on the annual
   mean, tiled 4 x 3. Kept as the raw encoded bytes rather than decoded floats —
   a byte per component per cell is 1.4 MB against 5.5 MB, and the decode is one
   multiply at sample time. */
function ocLoadSeasonal(){
  const S = OCEAN.seasonal;
  if(!S || !S.png) return;
  const im = new Image();
  im.src = S.png;
  const finish = () => {
    try{
      const cv = document.createElement("canvas");
      cv.width = S.w*S.cols; cv.height = S.h*S.rows;
      const cx = cv.getContext("2d",{willReadFrequently:true});
      cx.drawImage(im,0,0);
      const px = cx.getImageData(0,0,cv.width,cv.height).data;
      const n = S.w*S.h;
      const du=new Int8Array(n*S.nm), dv=new Int8Array(n*S.nm), ok=new Uint8Array(n*S.nm);
      for(let m=0;m<S.nm;m++){
        const tc=m%S.cols, tr=(m/S.cols)|0, base=m*n;
        for(let y=0;y<S.h;y++){
          let o=(((tr*S.h)+y)*cv.width + tc*S.w)*4, b=base+y*S.w;
          for(let x=0;x<S.w;x++,o+=4){
            if(px[o+3]<128) continue;
            du[b+x]=px[o]-128; dv[b+x]=px[o+1]-128; ok[b+x]=1;
          }
        }
      }
      OC.sdu=du; OC.sdv=dv; OC.sok=ok;
      OC.sw=S.w; OC.sh=S.h; OC.slon0=S.lon0; OC.slat0=S.lat0; OC.sdd=S.d; OC.samax=S.amax;
      cv.width=cv.height=0;
      OCEAN.seasonal.png=null;
      sync();
    }catch(e){ OC.serr=String(e); }
  };
  if(im.decode) im.decode().then(finish).catch(()=>{ im.onload=finish; im.onerror=finish; });
  else { im.onload=finish; im.onerror=finish; }
}

/* Sea-surface temperature, from the thermistor on the same drifters. Without it
   every filament was the same colour whether it carried 24 C north or 3 C back,
   which is the thermo half of thermohaline missing from a thermohaline map. */
function ocLoadSST(){
  const S = OCEAN.sst;
  if(!S || !S.png) return;
  const im = new Image();
  im.src = S.png;
  const finish = () => {
    try{
      const cv = document.createElement("canvas");
      cv.width = S.w; cv.height = S.h;
      const cx = cv.getContext("2d",{willReadFrequently:true});
      cx.drawImage(im,0,0);
      const px = cx.getImageData(0,0,S.w,S.h).data;
      const n = S.w*S.h;
      const t = new Uint8Array(n), ok = new Uint8Array(n);
      for(let k=0;k<n;k++){
        const o=k*4;
        if(px[o+3]<128) continue;
        t[k]=px[o]; ok[k]=1;
      }
      OC.tmp=t; OC.tok=ok; OC.tw=S.w; OC.th=S.h;
      OC.tlon0=S.lon0; OC.tlat0=S.lat0; OC.tdd=S.d; OC.tmin=S.tmin; OC.tmax=S.tmax;
      cv.width=cv.height=0;
      OCEAN.sst.png=null;
      sync();
    }catch(e){ OC.terr=String(e); }
  };
  if(im.decode) im.decode().then(finish).catch(()=>{ im.onload=finish; im.onerror=finish; });
  else { im.onload=finish; im.onerror=finish; }
}
/* nearest-cell temperature in degrees C, or null where no drifter measured one */
function ocTemp(lon,lat){
  if(!OC.tok) return null;
  const w=OC.tw, h=OC.th;
  let x=Math.round((lon-OC.tlon0)/OC.tdd);
  const y=Math.round((OC.tlat0+(h-1)*OC.tdd-lat)/OC.tdd);
  if(y<0||y>h-1) return null;
  x=((x%w)+w)%w;
  const k=y*w+x;
  if(!OC.tok[k]) return null;
  return OC.tmp[k]/255*(OC.tmax-OC.tmin)+OC.tmin;
}

/* The climatological month the deck is showing, and how far between it and the
   next one. Driven by the scrubber, so the ocean moves with the ice — but it is
   a CLIMATOLOGY: the average of every September in the record, not September of
   the year on the dial. The readout says so. */
function ocSetMonth(){
  if(!OC.sok) { OC.monA=OC.monB=0; OC.monF=0; return; }
  const k=monIdx(), ym=ymFor(k);
  let f=st.t-k;                          // sub-month position while playing
  if(!(f>-0.5&&f<0.5)) f=0;
  let x=ym[1]+f;                         // 0-based climatological month, fractional
  x=((x%12)+12)%12;
  OC.mon=x;
  OC.monA=Math.floor(x)%12;
  OC.monB=(OC.monA+1)%12;
  OC.monF=x-Math.floor(x);
}

/* row 0 of the image is the northernmost row; the array is stored north-up */
function ocIdx(lon,lat){
  const F=OC;
  let x=(lon - F.lon0)/F.dd, y=(F.lat0 + (F.h-1)*F.dd - lat)/F.dd;
  if(y<0||y>F.h-1) return -1;
  x=((x % F.w)+F.w)%F.w;
  return (Math.round(y)*F.w + Math.round(x));
}

/* bilinear sample; returns false where the climatology has no observation */
const OC_S={u:0,v:0,n:0};
function ocSample(lon,lat){
  if(!OC.ready) return false;
  const F=OC;
  let fx=(lon - F.lon0)/F.dd;
  const fy=(F.lat0 + (F.h-1)*F.dd - lat)/F.dd;
  if(fy<0||fy>F.h-1) return false;
  fx=((fx % F.w)+F.w)%F.w;
  const x0=Math.floor(fx), y0=Math.floor(fy);
  const tx=fx-x0, ty=fy-y0;
  const x1=(x0+1)%F.w, y1=Math.min(F.h-1,y0+1);
  let su=0,sv=0,sn=0,sw=0;
  for(let c=0;c<4;c++){
    const xi=c&1?x1:x0, yi=c&2?y1:y0;
    const w=(c&1?tx:1-tx)*(c&2?ty:1-ty);
    const k=yi*F.w+xi;
    if(!F.ok[k]||w<=0) continue;
    su+=F.u[k]*w; sv+=F.v[k]*w; sn+=F.nobs[k]*w; sw+=w;
  }
  if(sw<0.35) return false;          // mostly no data: treat as no observation
  OC_S.u=su/sw; OC_S.v=sv/sw; OC_S.n=sn/sw;
  OC_S.seasonal=false;
  if(OC.sok && st.flowSeason!==false) ocSeasonAdd(lon,lat);
  return true;
}

/* the anomaly for the displayed month, added on top of the annual mean.
   Where the month has no observation of its own the anomaly is zero and the
   value falls back to the annual mean — flagged, not silently substituted. */
const OC_A={u:0,v:0,ok:false};
function ocSeasonOne(lon,lat,m){
  const w=OC.sw, h=OC.sh;
  let fx=(lon-OC.slon0)/OC.sdd;
  const fy=(OC.slat0+(h-1)*OC.sdd-lat)/OC.sdd;
  OC_A.ok=false; OC_A.u=0; OC_A.v=0;
  if(fy<0||fy>h-1) return;
  fx=((fx%w)+w)%w;
  const x0=Math.floor(fx), y0=Math.floor(fy), tx=fx-x0, ty=fy-y0;
  const x1=(x0+1)%w, y1=Math.min(h-1,y0+1), base=m*w*h;
  const k=OC.samax/(127*127);
  let su=0,sv=0,sw2=0;
  for(let c=0;c<4;c++){
    const xi=c&1?x1:x0, yi=c&2?y1:y0;
    const ww=(c&1?tx:1-tx)*(c&2?ty:1-ty);
    const idx=base+yi*w+xi;
    if(!OC.sok[idx]||ww<=0) continue;
    const a=OC.sdu[idx], b=OC.sdv[idx];
    su+=(a<0?-a*a:a*a)*k*ww; sv+=(b<0?-b*b:b*b)*k*ww; sw2+=ww;
  }
  if(sw2<0.35) return;
  OC_A.u=su/sw2; OC_A.v=sv/sw2; OC_A.ok=true;
}
function ocSeasonAdd(lon,lat){
  ocSeasonOne(lon,lat,OC.monA);
  const ua=OC_A.u, va=OC_A.v, oka=OC_A.ok;
  if(OC.monF>0.001){
    ocSeasonOne(lon,lat,OC.monB);
    if(oka&&OC_A.ok){
      OC_S.u+=ua+(OC_A.u-ua)*OC.monF; OC_S.v+=va+(OC_A.v-va)*OC.monF;
      OC_S.seasonal=true; return;
    }
  }
  if(oka){ OC_S.u+=ua; OC_S.v+=va; OC_S.seasonal=true; }
}

/* ---------------- particles ---------------- */
function ocCount(){
  const w=st.mapW||900;
  const base = w<620 ? 2200 : w<1000 ? 4200 : 6000;
  return ocReduced() ? Math.round(base*0.5) : base;
}

/* Half a sphere is always facing away. Seeding uniformly over the whole globe
   therefore throws away half the particles, so most respawns land inside a cap
   around whatever the view is centred on. The rest stay uniform, so the far
   side is populated by the time you turn the globe to it. */
function ocViewCentre(){
  if(st.mode==="GLOBE") return [st.glat, st.glon];
  if(st.mode==="PAIR")  return [Math.random()<0.5?-90:90, 0];
  return [st.S?-90:90, 0];
}
function ocCapPoint(lat0,lon0,capDeg){
  const u=1-Math.random()*(1-Math.cos(capDeg*D)), r=Math.sqrt(Math.max(0,1-u*u));
  const ph=Math.random()*Math.PI*2;
  const a=lat0*D, b=lon0*D, ca=Math.cos(a), sa=Math.sin(a), cb=Math.cos(b), sb=Math.sin(b);
  const f=[ca*cb, ca*sb, sa], rr=[-sb, cb, 0], uu=[-sa*cb, -sa*sb, ca];
  const x=r*Math.cos(ph), y=r*Math.sin(ph);
  const X=x*rr[0]+y*uu[0]+u*f[0], Y=x*rr[1]+y*uu[1]+u*f[1], Z=x*rr[2]+y*uu[2]+u*f[2];
  return [Math.asin(Z<-1?-1:Z>1?1:Z)/D, Math.atan2(Y,X)/D];
}
function ocSeed(){
  const P=ocCount();
  OC.P=P; OC.nPart=Math.round(P*0.45);
  OC.plon=new Float32Array(P); OC.plat=new Float32Array(P);
  OC.page=new Float32Array(P); OC.pspd=new Float32Array(P); OC.pdns=new Float32Array(P); OC.ptmp=new Float32Array(P);
  OC.trail=new Float32Array(P*OC.TR*3);
  OC.thead=0; OC.seeded=true;
  for(let i=0;i<P;i++) ocRespawn(i,true);
  OC.warm=0;
}
function ocRespawn(i,initial){
  const vc=ocViewCentre();
  for(let t=0;t<40;t++){
    let lon, lat;
    if(!initial && t<30 && Math.random()<0.82){
      const q=ocCapPoint(vc[0], vc[1], 96); lat=q[0]; lon=q[1];
    } else {
      lon=Math.random()*360-180;
      lat=Math.asin(Math.random()*2-1)/D;             // area-uniform on the sphere
    }
    if(lat<OC.lat0 || lat>OC.lat0+(OC.h-1)*OC.dd) continue;
    const k=ocIdx(lon,lat);
    if(k<0||!OC.ok[k]) continue;
    OC.plon[i]=lon; OC.plat[i]=lat;
    OC.page[i]= initial ? Math.random()*OC_LIFE : 0;
    OC.pspd[i]=Math.hypot(OC.u[k],OC.v[k]); OC.pdns[i]=OC.nobs[k];
    { const t=ocTemp(lon,lat); OC.ptmp[i]= t===null ? -99 : t; }
    for(let t2=0;t2<OC.TR;t2++) ocStore(i,t2,lon,lat);
    return;
  }
  OC.plon[i]=0; OC.plat[i]=0; OC.page[i]=OC_LIFE;     // retire it for a frame
}
const OC_LIFE=4.2;                                     // seconds before a particle is recycled
function ocStore(i,slot,lon,lat){
  const a=lat*D, b=lon*D, ca=Math.cos(a);
  const o=(i*OC.TR+slot)*3;
  OC.trail[o]=ca*Math.cos(b); OC.trail[o+1]=ca*Math.sin(b); OC.trail[o+2]=Math.sin(a);
}

function ocStep(dt){
  if(!OC.ready||!OC.seeded) return;
  if(dt>0.05) dt=0.05;
  const P=OC.nPart;
  OC.tick=(OC.tick|0)+1;   // temperature is resampled for an eighth of the field each frame
  OC.pacc+=dt;
  const push = OC.pacc>=OC_PUSH;
  const head = push ? (OC.thead+1)%OC.TR : OC.thead;
  if(push) OC.pacc=0;
  for(let i=0;i<P;i++){
    OC.page[i]+=dt;
    let lon=OC.plon[i], lat=OC.plat[i];
    if(OC.page[i]>OC_LIFE){ ocRespawn(i,false); lon=OC.plon[i]; lat=OC.plat[i]; }
    else if(ocSample(lon,lat)){
      const cs=Math.cos(lat*D);
      lat += OC_S.v*OC_GAIN*dt;
      lon += (cs>0.02 ? OC_S.u*OC_GAIN*dt/cs : 0);
      if(lat>89.5||lat<-89.5){ ocRespawn(i,false); lon=OC.plon[i]; lat=OC.plat[i]; }
      else {
        lon=((lon+180)%360+360)%360-180;
        OC.plon[i]=lon; OC.plat[i]=lat;
        OC.pspd[i]=Math.hypot(OC_S.u,OC_S.v); OC.pdns[i]=OC_S.n;
        if((i&7)===(OC.tick&7)){ const t=ocTemp(lon,lat); OC.ptmp[i]= t===null ? -99 : t; }
      }
    } else { ocRespawn(i,false); lon=OC.plon[i]; lat=OC.plat[i]; }
    if(push) ocStore(i,head,lon,lat);
  }
  if(push){ OC.thead=head; if(OC.warm<OC.TR) OC.warm++; }
}

/* speed -> colour. Three buckets, so the whole field batches into six strokes.

   The cost of this layer is not the arithmetic — advecting and projecting three
   thousand particles is under two milliseconds. It is rasterisation: every
   segment drawn separately, with a round cap at each end, is a few thousand
   antialiased circles per frame. So each particle's whole trail goes into one
   polyline, the polylines batch by speed, and the caps are butt. Six strokes a
   frame instead of fourteen thousand capped segments. */
const OC_RAMP={
  /* by speed — the default. Fast water is bright and leaves a long streak;
     slow water is a dim grain. Trail length is the real speed encoding. */
  speed:[{max:0.10, col:"110,176,214", w:0.9,  a:0.42},
         {max:0.35, col:"158,219,240", w:1.15, a:0.62},
         {max:99,   col:"242,251,255", w:1.5,  a:0.92}],
  /* by how much the ocean has actually been sampled there, in drifter-days per
     square degree. Red is not danger, it is thin evidence. The two thresholds
     are the terciles of the field itself — 158 and 337 drifter-days — so the
     three colours split the sampled ocean into equal thirds instead of dumping
     80% of it into one bucket, which is what round numbers did. */
  dens: [{max:173, col:"216,82,74",   w:0.9,  a:0.50},
         {max:199, col:"200,128,47",  w:1.15, a:0.62},
         {max:999, col:"234,244,250", w:1.5,  a:0.92}],
  /* by measured sea-surface temperature. This is the thermo in thermohaline:
     the Gulf Stream leaves the tropics at 24 C and the Labrador Current brings
     3 C back past it, and until this ramp existed both were the same white.
     Breaks at 10 and 22 C — subpolar, temperate, subtropical. */
  temp: [{max:10,  col:"92,164,224",   w:1.0,  a:0.70},
         {max:22,  col:"206,220,232",  w:1.05, a:0.55},
         {max:999, col:"236,132,72",   w:1.35, a:0.88}]
};
function ocRamp(){ return OC_RAMP[OC_RAMP[st.flowCol] ? st.flowCol : "speed"]; }
function ocBucket(i){
  const R=ocRamp();
  const v = st.flowCol==="dens" ? OC.pdns[i]
          : st.flowCol==="temp" ? OC.ptmp[i]
          : OC.pspd[i];
  return v<R[0].max?0 : v<R[1].max?1 : 2;
}

/* Draw the advected field. `put` maps a unit-sphere point to a screen point and
   returns false when the point is not visible in this view — that is the only
   thing that differs between the globe and a polar disc.

   Cost here is rasterisation, not arithmetic: drawing every segment separately
   with a round cap at each end is a few thousand antialiased circles a frame.
   So each particle's whole trail is one polyline, the polylines batch by speed,
   and the caps are butt. Nine strokes a frame rather than fourteen thousand
   capped segments. */
function ocDrawField(g,put){
  if(!OC.ready||!OC.seeded||OC.warm<2) return;
  const P=OC.nPart, TR=OC.TR, T=OC.trail, thead=OC.thead;
  const still=ocReduced();
  const segs=Math.min(TR-1, OC.warm-1);

  const path=[new Path2D(),new Path2D(),new Path2D()];
  const dot =[new Path2D(),new Path2D(),new Path2D()];
  let drawn=0;

  for(let i=0;i<P;i++){
    const b=ocBucket(i);
    const pb=path[b];
    // the live head, so the motion is smooth between history pushes
    const a=OC.plat[i]*D, l=OC.plon[i]*D, ca=Math.cos(a);
    let run=false, lx=0, ly=0, k=0;
    if(put(ca*Math.cos(l), ca*Math.sin(l), Math.sin(a))){
      pb.moveTo(OC_PX,OC_PY); run=true; lx=OC_PX; ly=OC_PY; k=1;
      // slow water leaves no streak worth seeing, so it is a grain instead —
      // trail length is the speed encoding, and this keeps the field legible
      dot[b].moveTo(OC_PX-0.55,OC_PY); dot[b].lineTo(OC_PX+0.55,OC_PY);
    }
    for(let s=0;s<=segs;s++){
      const o=(i*TR+((thead-s+TR*2)%TR))*3;
      if(!put(T[o],T[o+1],T[o+2])){ run=false; continue; }
      if(run && (Math.abs(OC_PX-lx)>140||Math.abs(OC_PY-ly)>140)) run=false;
      if(!run){ pb.moveTo(OC_PX,OC_PY); run=true; } else pb.lineTo(OC_PX,OC_PY);
      lx=OC_PX; ly=OC_PY; k++;
    }
    if(k>1) drawn++;
  }
  OC.drawn=drawn;

  const R=ocRamp();
  g.lineCap="butt"; g.lineJoin="round";
  const dim = still ? 0.8 : 1;
  for(let b=0;b<3;b++){
    const B=R[b];
    g.strokeStyle="rgba("+B.col+","+(B.a*dim).toFixed(3)+")";
    g.lineWidth=B.w; g.stroke(path[b]);
  }
  g.lineCap="round";
  for(let b=0;b<3;b++){
    const B=R[b];
    g.strokeStyle="rgba("+B.col+","+Math.min(1,B.a*1.35*dim).toFixed(3)+")";
    g.lineWidth=B.w*1.15; g.stroke(dot[b]);
  }
  g.lineCap="butt";
}

/* An automatic frame budget. The deck runs on everything from a phone to a
   workstation and the right particle count is not the same number on both, so
   it is measured rather than guessed: shed particles when the frame runs long,
   put them back when it does not, inside the bounds ocCount sets. */
function ocBudget(dt){
  if(!OC.ready||!OC.seeded||OC.budgetOff) return;
  const cap=ocCount(), floor=Math.max(300, Math.round(cap*0.22));
  // keep the count inside its bounds unconditionally, so a count that has been
  // pushed below the floor can still climb back out
  if(OC.nPart<floor) OC.nPart=floor;
  if(OC.nPart>cap)   OC.nPart=cap;
  OC.bAcc=(OC.bAcc||0)+dt; OC.bN=(OC.bN||0)+1;
  if(OC.bN<50) return;
  const ms=OC.bAcc/OC.bN*1000; OC.bAcc=0; OC.bN=0;
  OC.frameMs=+ms.toFixed(1);
  // the test is the one a viewer applies: is this still above 30 frames a second
  if(ms>31 && OC.nPart>floor)      OC.nPart=Math.max(floor, Math.round(OC.nPart*0.82));
  else if(ms<20 && OC.nPart<cap)   OC.nPart=Math.min(cap, Math.round(OC.nPart*1.12)+32);
}

/* put() writes its result here rather than allocating a point per call */
let OC_PX=0, OC_PY=0;

function ocPutGlobe(B,cx,cy,s){
  const r0=B.r, u0=B.u, f0=B.f;
  return (x,y,z)=>{
    if(x*f0[0]+y*f0[1]+z*f0[2] < 0) return false;
    OC_PX = cx + (x*r0[0]+y*r0[1]+z*r0[2])*s;
    OC_PY = cy - (x*u0[0]+y*u0[1]+z*u0[2])*s;
    return true;
  };
}
/* the polar disc: unit sphere point -> lat/lon -> the deck's own projection */
function ocPutDisc(cx,cy,s,S){
  return (x,y,z)=>{
    const lat=Math.asin(z<-1?-1:z>1?1:z)/D;
    if(S ? lat>-45 : lat<45) return false;
    const p=proj(Math.atan2(y,x)/D, lat, S);
    if(p[0]*p[0]+p[1]*p[1]>1) return false;
    OC_PX=cx+p[0]*s; OC_PY=cy-p[1]*s;
    return true;
  };
}

/* ---------------- ACC fronts, measured ---------------- */
function ocDrawFronts(g,project){
  for(const fr of OCEAN.fronts){
    g.beginPath();
    let started=false, lx=0, ly=0;
    const p=fr.pts;
    for(let i=0;i<p.length;i+=2){
      if(!project(p[i],p[i+1])){ started=false; continue; }
      if(!started){ g.moveTo(OC_PX,OC_PY); started=true; }
      else if(Math.abs(OC_PX-lx)>160||Math.abs(OC_PY-ly)>160){ g.moveTo(OC_PX,OC_PY); }
      else g.lineTo(OC_PX,OC_PY);
      lx=OC_PX; ly=OC_PY;
    }
    g.strokeStyle=fr.col; g.lineWidth=1.15; g.globalAlpha=0.62; g.stroke();
    g.globalAlpha=1;
  }
}

/* ---------------- the deep limbs, schematic, at depth ---------------- */
const OC_LIMBCOL={
  warm:{c:"236,132,72",  nm:"warm upper limb"},
  nadw:{c:"74,134,216",  nm:"North Atlantic Deep Water"},
  aabw:{c:"127,227,245", nm:"Antarctic Bottom Water"},
  up:  {c:"79,158,106",  nm:"upwelling"},
  sink:{c:"203,94,62",   nm:"sinking"}
};
function ocRadius(depth){
  return 1 - OCEAN.depth.radius * Math.min(1, depth/OCEAN.depth.scale_m);
}

/* One pass over every limb. `side` is +1 for the hemisphere facing the viewer,
   -1 for the one behind the planet. Phase drives a travelling pulse rather than
   a dash offset, so it stays smooth whatever the frame rate does. */
function ocDrawLimbs(g,B,cx,cy,s,side,phase,speed){
  const r0=B.r, u0=B.u, f0=B.f;
  const z=Math.max(1, (CAM&&CAM.zoom)||1);
  const k=Math.min(1.9, 0.75+0.55*z);        // chevrons and ribbons hold up when zoomed
  // the chevrons march. A static arrowhead says which way; a moving one says
  // that something is moving, which is the whole point of the layer.
  const march=(performance.now()/1000)*0.85*speed;
  for(const L of OCEAN.limbs){
    const col=OC_LIMBCOL[L.cls].c, p=L.pts, n=L.n;
    const xs=OC_XS, ys=OC_YS, vis=OC_VIS;
    for(let i=0;i<n;i++){
      const lon=p[i*3]*D, lat=p[i*3+1]*D, rr=ocRadius(p[i*3+2]);
      const ca=Math.cos(lat)*rr;
      const X=ca*Math.cos(lon), Y=ca*Math.sin(lon), Z=Math.sin(lat)*rr;
      const zz=X*f0[0]+Y*f0[1]+Z*f0[2];
      vis[i]= (side>0 ? zz>=0 : zz<0) ? 1 : 0;
      xs[i]=cx+(X*r0[0]+Y*r0[1]+Z*r0[2])*s;
      ys[i]=cy-(X*u0[0]+Y*u0[1]+Z*u0[2])*s;
    }
    const near=side>0;
    // the ribbon
    g.beginPath();
    let run=false;
    for(let i=0;i<n;i++){
      if(!vis[i]){ run=false; continue; }
      if(!run){ g.moveTo(xs[i],ys[i]); run=true; } else g.lineTo(xs[i],ys[i]);
    }
    g.lineCap="round"; g.lineJoin="round";
    g.strokeStyle="rgba("+col+","+(near?0.26:0.09)+")";
    g.lineWidth=(near?3.4:2.2)*k; g.stroke();
    g.strokeStyle="rgba("+col+","+(near?0.55:0.16)+")";
    g.lineWidth=(near?1.5:1.0)*k; g.stroke();

    // the travelling pulse: a short bright run whose head advances with phase
    const span=Math.max(6, Math.round(n*0.16));
    const head=Math.floor(((phase*0.5 + (L.id.charCodeAt(5)%7)/7) % 1) * n);
    g.beginPath(); run=false;
    for(let c=0;c<span;c++){
      const i=(head-c+n*2)%n;
      if(!vis[i] || (c>0 && Math.abs(i-((head-c+1+n*2)%n))>1)){ run=false; continue; }
      if(!run){ g.moveTo(xs[i],ys[i]); run=true; } else g.lineTo(xs[i],ys[i]);
    }
    g.strokeStyle="rgba("+col+","+(near?0.95:0.22)+")";
    g.lineWidth=(near?2.4:1.3)*k; g.stroke();

    // marching chevrons
    if(near){
      const step=Math.max(7, Math.round(n/11));
      const off=Math.floor(((march + (L.id.charCodeAt(5)%5)/5) % 1) * step);
      const a=4.6*k;
      g.beginPath();
      for(let i=step+off;i<n-1;i+=step){
        if(!vis[i]||!vis[i-1]) continue;
        const dx=xs[i]-xs[i-1], dy=ys[i]-ys[i-1], m=Math.hypot(dx,dy);
        if(m<0.6) continue;
        const ux=dx/m, uy=dy/m;
        g.moveTo(xs[i]+ux*a, ys[i]+uy*a);
        g.lineTo(xs[i]-ux*a*0.5+uy*a*0.62, ys[i]-uy*a*0.5-ux*a*0.62);
        g.lineTo(xs[i]-ux*a*0.5-uy*a*0.62, ys[i]-uy*a*0.5+ux*a*0.62);
        g.closePath();
      }
      g.fillStyle="rgba("+col+",0.92)"; g.fill();
    }
  }
}
const OC_XS=new Float32Array(4096), OC_YS=new Float32Array(4096), OC_VIS=new Uint8Array(4096);

/* the gateways: real positions, real sill depths, drawn where they actually sit */
function ocDrawNodes(g,B,cx,cy,s,labels){
  const r0=B.r, u0=B.u, f0=B.f;
  for(const nd of OCEAN.nodes){
    const lon=nd.at[0]*D, lat=nd.at[1]*D, rr=ocRadius(nd.depth);
    const ca=Math.cos(lat)*rr;
    const X=ca*Math.cos(lon), Y=ca*Math.sin(lon), Z=Math.sin(lat)*rr;
    if(X*f0[0]+Y*f0[1]+Z*f0[2] < 0.06) continue;
    const px=cx+(X*r0[0]+Y*r0[1]+Z*r0[2])*s, py=cy-(X*u0[0]+Y*u0[1]+Z*u0[2])*s;
    g.strokeStyle="rgba(200,128,47,.95)"; g.lineWidth=1.1;
    g.beginPath(); g.moveTo(px-4,py); g.lineTo(px+4,py); g.moveTo(px,py-4); g.lineTo(px,py+4); g.stroke();
    g.beginPath(); g.arc(px,py,3.4,0,7); g.stroke();
    labels.push({px,py,t:nd.label.toUpperCase(),col:"rgba(226,190,140,.95)",dy:-8});
    HOT.push({x:px,y:py,r:12,ex:"node_"+nd.id});
  }
}
