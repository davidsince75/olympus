/* The living layer was being rebuilt from scratch on every frame: 8,100 separate
   aurora quad fills and up to 3,329 ice-drift vectors, each with its own path, its
   own colour string and its own stroke. None of it moves — the aurora is one
   observation, the drift is one 48-hour field, the SAR footprints are a fixed
   catalogue. So it is rendered once into two offscreen sheets and composited,
   and rebuilt only when the hemisphere, the size, the layer switches or the
   drift multiplier actually change.

   Two sheets rather than one because the aurora composites with `lighter` onto
   whatever is underneath it, and the footprints and drift do not. */
const LIVEC={};
function liveSheet(S,which,s,dpr){
  const key=(S?"S":"N")+which;
  let c=LIVEC[key];
  const w=Math.max(2,Math.round(s*2*dpr));
  if(!c){ c={cv:document.createElement("canvas")}; LIVEC[key]=c; }
  if(c.cv.width!==w){ c.cv.width=c.cv.height=w; c.key=null; }
  return c;
}
function drawDeckLive(g,cx,cy,s,S){
  if(typeof LIVE === "undefined" || !LIVE) return;
  const dpr=Math.min(2,window.devicePixelRatio||1);
  const key=[Math.round(s*dpr), st.lay.aur?1:0, st.lay.sar1?1:0, st.lay.drift?1:0,
             (st.driftX||1)].join("|");
  const A=liveSheet(S,"a",s,dpr), B=liveSheet(S,"b",s,dpr);
  if(A.key!==key){
    for(const [sheet,part] of [[A,"aur"],[B,"rest"]]){
      const x=sheet.cv.getContext("2d");
      x.setTransform(1,0,0,1,0,0);
      x.clearRect(0,0,sheet.cv.width,sheet.cv.height);
      x.setTransform(dpr,0,0,dpr,0,0);
      drawDeckLiveRaw(x,s,s,s,S,part);
    }
    A.key=B.key=key;
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
}

/* the original work, now run once per change instead of once per frame, and
   batched: the aurora into ten colour buckets and the drift into eight, so the
   cost is a few dozen fills rather than twelve thousand. */
function drawDeckLiveRaw(g,cx,cy,s,S,part){
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
        const a0 = xy(g,cx,cy,s,S,sgn*lat,lo),      a1 = xy(g,cx,cy,s,S,sgn*lat,lo+2);
        const a2 = xy(g,cx,cy,s,S,sgn*(lat+1),lo+2), a3 = xy(g,cx,cy,s,S,sgn*(lat+1),lo);
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
  }

  // --- SAR footprints ---
  const SR = LIVE.sar;
  if(st.lay.sar1 && SR && SR.items){
    const want = S ? "sh" : "nh", now = Date.now(), NB=6;
    const fp=[], sp=[];
    for(let b=0;b<NB;b++){ fp.push(new Path2D()); sp.push(new Path2D()); }
    for(const it of SR.items){
      if(it.hemi !== want) continue;
      const pts = it.poly.map(([lon,lat]) => xy(g,cx,cy,s,S,lat,lon));
      if(pts.length < 3) continue;
      const fresh = Math.max(0, 1 - (now - Date.parse(it.start))/3600000/18);
      const b = Math.min(NB-1, Math.floor(fresh*NB));
      const q=new Path2D();
      q.moveTo(pts[0][0],pts[0][1]);
      for(let i=1;i<pts.length;i++) q.lineTo(pts[i][0],pts[i][1]);
      q.closePath();
      fp[b].addPath(q); sp[b].addPath(q);
    }
    for(let b=0;b<NB;b++){
      const fresh=(b+0.5)/NB;
      g.fillStyle   = `rgba(155,118,220,${(0.05+0.13*fresh).toFixed(3)})`;
      g.strokeStyle = `rgba(200,155,232,${(0.20+0.55*fresh).toFixed(2)})`;
      g.lineWidth = 0.7 + fresh*0.9;
      g.fill(fp[b]); g.stroke(sp[b]);
    }
  }

  // --- ice drift ---
  const DR = LIVE.drift && LIVE.drift[S ? "sh" : "nh"];
  if(st.lay.drift && DR && DR.v){
    g.lineCap = "round";
    const X = st.driftX || 1, NB=8;
    const paths=[]; for(let b=0;b<NB;b++) paths.push(new Path2D());
    for(const [la0,lo0,la1,lo1] of DR.v){
      const p = xy(g,cx,cy,s,S,la0,lo0), q0 = xy(g,cx,cy,s,S,la1,lo1);
      const qx = p[0] + (q0[0]-p[0])*X, qy = p[1] + (q0[1]-p[1])*X;
      const dx = qx-p[0], dy = qy-p[1], len = Math.hypot(dx,dy);
      if(len < 0.6) continue;
      const k = Math.min(1, len/(s*0.045*X));
      const P = paths[Math.min(NB-1, Math.floor(k*NB))];
      P.moveTo(p[0],p[1]); P.lineTo(qx,qy);
      const ux = dx/len, uy = dy/len, hl = Math.min(4.5, len*0.42);
      P.moveTo(qx,qy); P.lineTo(qx-ux*hl-uy*hl*0.5, qy-uy*hl+ux*hl*0.5);
      P.moveTo(qx,qy); P.lineTo(qx-ux*hl+uy*hl*0.5, qy-uy*hl-ux*hl*0.5);
    }
    for(let b=0;b<NB;b++){
      const k=(b+0.5)/NB;
      g.strokeStyle = `rgba(${Math.round(127+90*k)},${Math.round(227-40*k)},245,${(0.32+0.5*k).toFixed(2)})`;
      g.lineWidth = 0.8 + 0.9*k;
      g.stroke(paths[b]);
    }
  }
}
