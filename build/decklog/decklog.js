/* ============================ the deck log ============================
   The record behind the picture, as tables a reader can check and take away.

   Three views, all reading the arrays this page already draws from:
     This month  every quantity at the month on the dial, with its status, and
                 every layer on the map with what it is actually showing then
     Series      the scalar records in full, one row per month or season, with
                 CSV export; gaps are rows with an empty value and a status
     Sources     product, version, DOI, licence, coverage, and every step
                 between the published value and the pixel; plus dated checks
                 that re-derived what is carried from the publisher's own files

   Nothing is fetched and nothing here changes a value. The one record carried
   only for this view is OSI SAF's published Sea Ice Index, kept as a reference
   beside the deck's own extent and never used to compute anything on the deck.
   Gridded fields are not re-exported: the log names the exact product instead,
   because a copy taken from a visualisation is a worse source than the original. */

const DL = { open:false, tab:"frame", ser:"extent", key:"", saver:undefined };
const DLK = (typeof DECKLOG !== "undefined" && DECKLOG) ? DECKLOG : {};

function lgEsc(t){ return String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function lgYM(t){ return Math.floor(t/12)+String(t%12+1).padStart(2,"0"); }
function lgAbs(ym){ return (+String(ym).slice(0,4))*12 + (+String(ym).slice(4,6))-1; }
function lgNow(){ return YM0 + OSI.hemi[hemiKey()].ymo[monIdx()]; }
function lgMonYr(t){ return MON[t%12]+" "+Math.floor(t/12); }
function lgF(v,dp){ return (v==null||!isFinite(v)) ? "" : (+v).toFixed(dp); }
function lgS(v,dp){ return (v==null||!isFinite(v)) ? "" : (v>0?"+":v<0?"−":"±")+Math.abs(v).toFixed(dp); }
function lgFrame(h,t){
  const A=OSI.hemi[h].ymo, off=t-YM0; let lo=0, hi=A.length-1;
  while(lo<=hi){ const m=(lo+hi)>>1; if(A[m]===off) return m; if(A[m]<off) lo=m+1; else hi=m-1; }
  return -1;
}
function lgFirst(){ return YM0+OSI.hemi.sh.ymo[0]; }
function lgLast(){ return YM0+OSI.hemi.sh.ymo[OSI.hemi.sh.n-1]; }

/* ---- status vocabulary: one word per kind of claim, used everywhere in the log ---- */
const LG_TAG = { "MEAS":"arch", "FT":"ft", "DERIVED":"arch", "CLIM":"arch", "MEAN":"arch", "REF":"ref",
  "AS OF":"live", "MODEL":"sim", "SCHEMATIC":"sim", "SIM":"sim", "NO OBS":"wait", "NOT CARRIED":"nil",
  "STATIC":"nil", "GENERATED":"nil", "SELECTION":"nil" };
const LG_KEYS = [
  ["MEAS","measured, from the product named beside it"],
  ["FT","fast-track: provisional, can still be revised"],
  ["DERIVED","computed in this page from values it carries"],
  ["REF","another agency's published value, shown for comparison, never used in a computation"],
  ["CLIM","a climatology: the average of every such month, not this month"],
  ["AS OF","a snapshot with its own date; it does not move with the dial"],
  ["MODEL","model output"], ["SCHEMATIC","drawn through measured points"], ["SIM","illustration"],
  ["NO OBS","the source has no observation here; the value is left empty"],
  ["NOT CARRIED","the source has it; this page does not carry it"]
];
function lgTag(s){ return '<span class="tag '+(LG_TAG[s]||"nil")+'">'+s+'</span>'; }

/* ---- OSI SAF records, by the key in the file name ---- */
const LG_OSI = {
  "cdr-v3p0":         {id:"OSI-450-a", nm:"Global sea-ice concentration CDR v3.0 (SMMR, SSM/I, SSMIS)", doi:"10.15770/EUM_SAF_OSI_0013", url:"https://osi-saf.eumetsat.int/products/osi-450-a", lic:"EUMETSAT OSI SAF licence: free of charge, credit “Copyright EUMETSAT”"},
  "icdr-v3p0":        {id:"OSI-430-a", nm:"Interim CDR v3.0 (SSMIS)", doi:"10.15770/EUM_SAF_OSI_0014", url:"https://osi-saf.eumetsat.int/products/osi-430-a", lic:"EUMETSAT OSI SAF licence: free of charge, credit “Copyright EUMETSAT”"},
  "icdr-v3p0-amsr":   {id:"OSI-438", nm:"Interim CDR v3.0 (AMSR2, AMSR3)", doi:null, url:"https://osi-saf.eumetsat.int/products/osi-438", lic:"CC BY 4.0 (file attribute)"},
  "icdrft-v3p0-amsr": {id:"OSI-438", nm:"Interim CDR v3.0 (AMSR2, AMSR3), fast track", doi:null, url:"https://osi-saf.eumetsat.int/products/osi-438", lic:"CC BY 4.0 (file attribute)"}
};
function lgFile(h,r,t){ return "ice_conc_"+h+"_ease2-250_"+r[2]+"_"+lgYM(t)+".nc"; }
/* which record each stretch of the dial comes from, read from the payload */
function lgRuns(){
  const H=OSI.hemi.sh, R=H.runs;
  return R.map((r,i)=>{ const a=r[0], b=(i+1<R.length?R[i+1][0]:H.n)-1;
    return {r, a, b, t0:YM0+H.ymo[a], t1:YM0+H.ymo[b], P:LG_OSI[r[2]]||{id:r[1]}}; });
}
function lgSII(h,t){
  const R=DLK.sii && DLK.sii.hemi && DLK.sii.hemi[h]; if(!R) return undefined;
  const i=t-lgAbs(R.m0);
  return (i>=0 && i<R.v.length) ? R.v[i] : undefined;   // null = published as "no data"
}
const LG_HEMI = {sh:"Antarctic", nh:"Arctic"};
const LG_SEAS = ["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"];   // by centre month
const LG_RONI0 = 1950*12;   // DJF 1950 is centred on January 1950
function lgDiscKm(){ return (2*PS.N.rn/NG/1000).toFixed(1); }

/* ============================ this month ============================ */
function lgRank(h,k,m){
  const S=anomStats(), ser=S.byMonth[h][m].slice().sort((a,b)=>a[1]-b[1]);
  const n=ser.length, pos=ser.findIndex(q=>q[2]===k)+1;
  if(pos<1) return "";
  const lowR=pos, hiR=n-pos+1, low=lowR<=hiR, rk=low?lowR:hiR;
  return ordinal(rk)+" "+(low?"lowest":"highest")+" "+MON[m]+" of "+n;
}
function lgIceRows(h,t){
  const H=OSI.hemi[h], k=lgFrame(h,t), m=t%12, hemi=LG_HEMI[h], out=[];
  out.push({grp:hemi+" sea ice · EUMETSAT OSI SAF", ex:"log_extent"});
  if(k<0){
    out.push({q:hemi+" sea-ice extent", sub:"this deck", v:"", u:"10⁶ km²", s:"NO OBS",
      src:"no monthly file for "+lgMonYr(t)+" in either hemisphere", note:"a passive-microwave outage; shown as a gap, never bridged"});
    return out;
  }
  const r=recFor(h,k), P=LG_OSI[r[2]]||{id:r[1]}, v=H.ext[k];
  out.push({q:hemi+" sea-ice extent", sub:"this deck: the monthly-mean concentration field, cells ≥ 15 % × 625 km²",
    v:lgF(v,3), u:"10⁶ km²", s:r[3]?"FT":"MEAS", ex:"log_extent",
    src:lgEsc(r[1])+(r[3]?" fast track":"")+" · <code>"+lgEsc(lgFile(h,r,t))+"</code>",
    note:r[3]?"provisional month: the consolidated file replaces it":""});
  const pub=lgSII(h,t), R=DLK.sii && DLK.sii.hemi && DLK.sii.hemi[h];
  out.push({q:hemi+" sea-ice extent", sub:"OSI SAF’s published index: the mean of the daily extents, cells > 15 %",
    v:pub==null?"":lgF(pub/1e6,3), u:"10⁶ km²", s:pub==null?(pub===null?"NO OBS":"NOT CARRIED"):"REF", ex:"sie_index",
    src:"OSI-420-a Sea Ice Index v3.0"+(R&&R.created?" · file created "+lgEsc(String(R.created).slice(0,10)):""),
    note:pub==null?"":"this deck − index = "+lgS(v-pub/1e6,3)+" ×10⁶ km²"});
  const c=H.clim[m], sd=anomStats().SD[h][m], dv=v-c;
  out.push({q:hemi+" · 1991–2020 "+MON[m]+" mean", sub:"the 30 "+MON[m]+" values of 1991–2020 in this record",
    v:lgF(c,4), u:"10⁶ km²", s:"DERIVED", src:"this deck’s record, at ingest", note:"σ "+lgF(sd,4)+" (sample SD, same 30 years, computed here)", ex:"anomaly"});
  out.push({q:hemi+" anomaly", sub:"extent − "+MON[m]+" mean",
    v:lgS(dv,3), u:"10⁶ km²", s:"DERIVED", src:"computed here",
    note:lgS(dv/c*100,1)+" % · "+(sd>0?lgS(dv/sd,2)+" σ · ":"")+lgRank(h,k,m), ex:"anomaly"});
  return out;
}
function lgRapidRows(t){
  const ym=lgYM(t), a=amocAt(ym), out=[{grp:"Atlantic overturning · RAPID-MOCHA-WBTS 26.5°N", ex:"rapid"}];
  const V=[["moc","Overturning (AMOC)","moc_mar_hc10"],["gs","Florida Current","t_gs10"],
           ["ek","Ekman transport","t_ek10"],["umo","Upper mid-ocean transport","t_umo10"]];
  for(const [k,nm,src] of V){
    out.push({q:nm, sub:"", v:a?lgF(a[k],3):"", u:"Sv", s:a?"MEAS":"NO OBS", ex:k==="moc"?"amoc_num":"rapid",
      src:"RAPID v"+String(AM.version||"").replace(/^v/,"")+" · <code>"+src+"</code>",
      note:a?"calendar-month mean of the 12-hourly, 10-day low-passed series":"RAPID covers "+lgMonYr(lgAbs(AM.m0))+" – "+lgMonYr(lgAbs(AM.mN))+" in the version carried"});
  }
  return out;
}
function lgEnsoRows(t){
  const E=ensoData(), out=[{grp:"Tropical Pacific · NOAA Climate Prediction Center", ex:"el_nino"}];
  const code=LG_SEAS[t%12]+" "+Math.floor(t/12);
  if(!E){ out.push({q:"RONI", v:"", u:"°C", s:"NOT CARRIED", src:"", note:""}); return out; }
  const i=t-LG_RONI0, R=E.roni;
  const have = i>=0 && i<R.v.length;
  out.push({q:"Relative Oceanic Niño Index (RONI)", sub:"3-month mean centred on "+MON[t%12]+": "+code,
    v:have?lgS(R.v[i],2):"", u:"°C", s:have?"MEAS":"NO OBS", ex:"roni_history",
    src:"NOAA CPC · <code>RONI.ascii.txt</code>",
    note:have?"":"not yet published; latest is "+lgEsc(R.last)});
  const W=E.weekly, t0=Date.parse(W.series_t0+"T12:00:00Z"), wk=[];
  W.series34.forEach((v,j)=>{ const d=new Date(t0+j*7*864e5); if(d.getUTCFullYear()*12+d.getUTCMonth()===t) wk.push([d,v]); });
  const firstT=new Date(t0); const carriedFrom=firstT.getUTCFullYear()*12+firstT.getUTCMonth();
  out.push({q:"Niño-3.4, relative, weekly", sub:"weeks centred in "+lgMonYr(t),
    v:wk.map(([d,v])=>d.getUTCDate()+" "+MON[d.getUTCMonth()]+" "+lgS(v,1)).join(" · "), u:"°C",
    s:wk.length?"MEAS":(t<carriedFrom?"NOT CARRIED":"NO OBS"), ex:"nino_relative",
    src:"NOAA CPC · <code>rel_wksst9120.txt</code> (OISST v2.1)",
    note:wk.length?"":(t<carriedFrom?"the page carries weeks from "+fmtDay(W.series_t0)+"; CPC’s file starts in 1981":"")});
  return out;
}

/* what each layer on the map is actually showing for the month on the dial */
function lgField(L,t){
  const id=L.id, m=t%12, A=(typeof LIVE!=="undefined"&&LIVE)?LIVE:{}, E=ensoData();
  const obsMonth = iso => { const d=new Date(iso); return isFinite(d) ? d.getUTCFullYear()*12+d.getUTCMonth() : -1; };
  const same = iso => obsMonth(iso)===t ? " This is the month on the dial." : " It does not change with the dial.";
  switch(id){
  case "ice": {
    const out=[];
    for(const h of ["sh","nh"]){
      const k=lgFrame(h,t);
      if(k<0){ out.push(LG_HEMI[h]+": no file"); continue; }
      out.push(LG_HEMI[h]+": <code>"+lgEsc(lgFile(h,recFor(h,k),t))+"</code>");
    }
    const k=lgFrame("sh",t), r=k<0?null:recFor("sh",k);
    return {s:k<0?"NO OBS":(r[3]?"FT":"MEAS"),
      w:"Monthly-mean concentration. "+out.join(" · ")+". Each of the 220 × 220 disc cells ("+lgDiscKm()+" km on the projection plane) holds the mean of the 25 km cells that fall in it, in 1 % steps. Below 5 % is not drawn; 13–20 % is drawn as the 15 % edge."};
  }
  case "flow": {
    const col = st.flowCol==="temp" ? "Coloured by the drifters’ annual-mean temperature (breaks at "+OC_RAMP.temp[0].max+" and "+OC_RAMP.temp[1].max+" °C)."
              : st.flowCol==="dens" ? "Coloured by sampling density, drifter-days per square degree." : "Coloured by speed.";
    const seas = st.flowSeason && OC.sok;
    return {s:"CLIM", w:(seas ? MON[m]+" climatology: the average of every "+MON[m]+" the drifters sampled, not "+lgMonYr(t)+". Where a cell has no "+MON[m]+" observation it falls back to the annual mean."
                              : "Annual-mean climatology, the same for every month.")+" "+col};
  }
  case "fronts": return {s:"MEAN", w:"Mean frontal positions over the altimetry era, the same for every month."};
  case "enso": {
    if(!E) return {s:"NOT CARRIED", w:""};
    const F=E.field, d0=F.days[0].slice(0,8), d1=F.days[F.days.length-1].slice(0,8);
    const iso=s=>s.slice(0,4)+"-"+s.slice(4,6)+"-"+s.slice(6,8);
    return {s:"AS OF", w:"OISST anomaly, 7-day mean "+fmtDay(iso(d0))+" – "+fmtDay(iso(d1))+", contoured at "+F.levels.map(v=>lgS(v,0)).join(", ")+" °C."+same(iso(d1)+"T12:00:00Z")};
  }
  case "deep": {
    const a=amocAt(lgYM(t));
    return {s:"SCHEMATIC", w:"Hand-drawn paths through gateways at their published positions and sill depths, at ×"+OCEAN.depth.exag+" vertical exaggeration. Animation speed: "
      +(a ? "×"+Math.max(0.25,a.moc/AM.mean).toFixed(2)+" = RAPID "+a.moc.toFixed(1)+" Sv ÷ record mean "+AM.mean.toFixed(2)+" Sv." : "the record mean, because RAPID has no observation for "+lgMonYr(t)+".")};
  }
  case "shelf": return {s:"STATIC", w:"Natural Earth 10 m ice-shelf and coastline polygons, projected on the data’s own grid. No date."};
  case "sat": {
    const B=deckBaseLayer();
    if(!B) return {s:"NOT CARRIED", w:""};
    if(!B.time) return {s:"STATIC", w:B.nm+": a composite with no date. Dimmed by 40 % under the data."};
    const days=(B.gdays&&B.gdays.length)?B.gdays:[B.time];
    return {s:"AS OF", w:B.nm+", "+days.map(fmtDay).join(" + ")+" (the globe composites "+days.length+" day"+(days.length>1?"s":"")+"; the discs use "+fmtDay(B.time)+"). Dimmed by 40 % under the data."+same(B.time+"T12:00:00Z")};
  }
  case "sar1": { const S=A.sar; if(!S) return {s:"NOT CARRIED",w:""};
    return {s:"AS OF", w:S.n+" Sentinel-1 acquisitions in the "+S.hours+" h before "+String((S.items[0]||{}).start||"").replace("T"," ").slice(0,16)+" UTC, one outline each; poleward of 60°."+same((S.items[0]||{}).start)}; }
  case "aur": { const R=A.aurora; if(!R) return {s:"NOT CARRIED",w:""};
    return {s:"MODEL", w:"OVATION-Prime, one frame observed "+String(R.observed).replace("T"," ").slice(0,16)+" UTC. Brightness normalised on this frame’s own maximum; turned at ×"+AUR_SPIN+" to show the Earth rotating under it."+same(R.observed)}; }
  case "drift": { const R=A.drift; if(!R) return {s:"NOT CARRIED",w:""}; const D0=R.sh||R.nh;
    return {s:"AS OF", w:"48-hour displacement "+String(D0.t0).slice(0,10)+" → "+String(D0.t1).slice(0,10)+": "+(R.nh?R.nh.n:0)+" Arctic and "+(R.sh?R.sh.n:0)+" Antarctic vectors, nominal quality only, drawn at ×"+(st.driftX||1)+" length."+same(D0.t1)}; }
  case "vel": case "argo": case "track": return {s:"SIM", w:"Placeholder geometry. No value on the deck is derived from it."};
  case "grat": return {s:"GENERATED", w:"Meridians every 30°, parallels every 15°; the outer circle is 45°."};
  case "stn": return {s:"SELECTION", w:(STATIONS.S.length+STATIONS.N.length)+" sites typed into the page, not the Atlas register of 166."};
  }
  return {s:"NOT CARRIED", w:""};
}

function lgFrameHTML(){
  const t=lgNow(), rows=[].concat(lgIceRows("sh",t), lgIceRows("nh",t), lgRapidRows(t), lgEnsoRows(t));
  const tr = r => r.grp
    ? '<tr class="grp"><td colspan="6"'+(r.ex?' data-ex="'+r.ex+'"':'')+'>'+lgEsc(r.grp)+'</td></tr>'
    : '<tr'+(r.ex?' data-ex="'+r.ex+'"':'')+'><td class="q">'+lgEsc(r.q)+(r.sub?'<br><span class="off">'+lgEsc(r.sub)+'</span>':'')+'</td>'
      +'<td class="v">'+lgEsc(r.v)+'</td><td class="u">'+r.u+'</td><td class="s">'+lgTag(r.s)+'</td>'
      +'<td class="src">'+(r.src||"")+'</td><td class="src">'+lgEsc(r.note||"")+'</td></tr>';
  const fields = LAYERS.map(L=>{ const f=lgField(L,t);
    return '<tr data-ex="'+(L.ex||"")+'"><td class="q">'+lgEsc(L.nm)+'</td><td class="s">'+(st.lay[L.id]?'on':'<span class="off">off</span>')+'</td>'
      +'<td class="s">'+lgTag(f.s)+'</td><td>'+f.w+'</td><td class="src">'+lgEsc(L.src)+'</td></tr>'; }).join("");
  return '<section>'
    +'<p class="dlog-note">Every number the deck holds for <b>'+lgMonYr(t)+'</b>, at the precision it is carried, with where it came from and what kind of claim it is. '
    +'An empty value is an empty value: the source has nothing there, and the status says so. Move the dial or use ◀ ▶ and the log follows it.</p>'
    +'<div class="dlog-keys" data-ex="log_status">'+LG_KEYS.map(([k,d])=>'<span>'+lgTag(k)+lgEsc(d)+'</span>').join("")+'</div>'
    +'<div><h3>Values for '+lgMonYr(t)+' <span class="n">'+lgYM(t)+'</span></h3>'
    +'<div class="dlog-tw"><table class="dlt"><thead><tr><th>Quantity</th><th class="v">Value</th><th>Unit</th><th>Status</th><th>Source</th><th>Note</th></tr></thead><tbody>'
    +rows.map(tr).join("")+'</tbody></table></div></div>'
    +'<div><h3>What each layer shows for '+lgMonYr(t)+' <span class="n">'+LAYERS.filter(L=>st.lay[L.id]).length+' of '+LAYERS.length+' on</span></h3>'
    +'<div class="dlog-tw"><table class="dlt"><thead><tr><th>Layer</th><th>On</th><th>Status</th><th>What is drawn</th><th>Source</th></tr></thead><tbody>'
    +fields+'</tbody></table></div></div>'
    +'</section>';
}

/* ============================ series ============================ */
/* One definition per record. `cols` drive both the table and the CSV, so the two
   cannot say different things. kind: num (fixed dp), sgn (signed), int, txt, tag. */
function lgSeries(id){
  const t0=lgFirst(), tN=lgLast();
  if(id==="extent"){
    const cols=[{h:"Month",k:"yyyymm",kind:"txt"}];
    for(const h of ["sh","nh"]){
      const nm=LG_HEMI[h];
      cols.push({h:nm,sub:"deck, 10⁶ km²",k:h+"_extent_deck_1e6km2",kind:"num",dp:3},
                {h:"Status",k:h+"_status",kind:"tag"},
                {h:"OSI SAF index",sub:"10⁶ km²",k:h+"_index_1e6km2",kind:"num",dp:3,nocsv:true},
                {h:"Index",sub:"km², as published",k:h+"_index_km2",kind:"int",notable:true},
                {h:"Δ deck − index",sub:"10⁶ km²",k:h+"_minus_index_1e6km2",kind:"sgn",dp:3},
                {h:"Anomaly",sub:"vs 1991–2020, 10⁶ km²",k:h+"_anomaly_1e6km2",kind:"sgn",dp:3});
    }
    cols.push({h:"Record",k:"record",kind:"txt"},{h:"Deck file key",k:"file_key",kind:"txt",notable:true});
    const rows=[];
    for(let t=t0;t<=tN;t++){
      const r={yyyymm:lgYM(t), _t:t};
      let rec=null;
      for(const h of ["sh","nh"]){
        const k=lgFrame(h,t), pub=lgSII(h,t);
        r[h+"_index_km2"]=pub==null?null:pub; r[h+"_index_1e6km2"]=pub==null?null:pub/1e6;
        if(k<0){ r[h+"_status"]="NO OBS"; continue; }
        const q=recFor(h,k), v=OSI.hemi[h].ext[k]; rec=q;
        r[h+"_extent_deck_1e6km2"]=v; r[h+"_status"]=q[3]?"FT":"MEAS";
        r[h+"_minus_index_1e6km2"]=pub==null?null:+(v-pub/1e6).toFixed(6);
        r[h+"_anomaly_1e6km2"]=+(v-OSI.hemi[h].clim[t%12]).toFixed(6);
      }
      r.record=rec?((LG_OSI[rec[2]]||{}).id||rec[1])+(rec[3]?" FT":""):"";
      r.file_key=rec?rec[2]:"";
      if(!rec) r._gap=true;
      rows.push(r);
    }
    const R=DLK.sii||{};
    return {nm:"Sea-ice extent, monthly", file:"olympus_sea_ice_extent_monthly.csv", cols, rows, cur:lgYM(lgNow()),
      head:[["What","Two different extents for the same month, never merged. <b>Deck</b>: extent of OSI SAF’s monthly-mean concentration field, cells ≥ 15 % counted on the 25 km EASE2 grid × 625 km², rounded to 0.001 ×10⁶ km². <b>Index</b>: OSI SAF’s own published figure, the mean of the daily extents (cells > 15 %), kept in km² exactly as published."],
            ["Deck source","EUMETSAT OSI SAF "+lgRuns().map(x=>lgEsc(x.r[1])+(x.r[3]?" fast track":"")+" ("+lgMonYr(x.t0)+(x.t1>x.t0?" – "+lgMonYr(x.t1):"")+")").join(", ")+". Copyright EUMETSAT."],
            ["Index source",lgEsc(R.product||"")+(R.hemi?" · created "+lgEsc(String(R.hemi.nh.created).slice(0,10))+" · retrieved "+lgEsc(String(R.retrieved_utc).slice(0,10)):"")],
            ["Anomaly","Deck extent minus the deck’s own 1991–2020 mean for that calendar month (Climatology series)."],
            ["Gaps","April–June 1986 and December 1987 have no data in either record. They are rows with empty values and NO OBS."]],
      comment:["Deck: extent of the OSI SAF monthly-mean sea-ice concentration field; cells >= 15% on the EASE2 25 km grid x 625 km2; 1e6 km2, 3 decimals.",
               "Index: EUMETSAT OSI SAF Sea Ice Index v3.0 (OSI-420-a), mean of daily extents (cells > 15%), km2 as published.",
               "Index files created "+(R.hemi?R.hemi.nh.created+" (nh), "+R.hemi.sh.created+" (sh)":"?")+"; retrieved "+(R.retrieved_utc||"?")+".",
               "Anomaly: deck extent minus the deck's 1991-2020 mean of the same calendar month.",
               "Status: MEAS consolidated, FT fast-track (provisional), NO OBS no data (empty values).",
               "Sea-ice data: Copyright EUMETSAT. OSI-450-a doi:10.15770/EUM_SAF_OSI_0013; OSI-430-a doi:10.15770/EUM_SAF_OSI_0014; OSI-438 CC BY 4.0."]};
  }
  if(id==="clim"){
    const S=anomStats(), cols=[{h:"Month",k:"month",kind:"txt"}], rows=[];
    for(const h of ["sh","nh"]) cols.push({h:LG_HEMI[h]+" mean",sub:"10⁶ km², as carried",k:h+"_mean_1e6km2",kind:"num",dp:4},
                                          {h:"σ",sub:"sample SD, computed here",k:h+"_sd_1e6km2",kind:"num",dp:4},
                                          {h:"n",k:h+"_n",kind:"int"});
    for(let m=0;m<12;m++){
      const r={month:MON[m], _m:m};
      for(const h of ["sh","nh"]){
        const v=S.byMonth[h][m].filter(q=>q[0]>=1991&&q[0]<=2020);
        r[h+"_mean_1e6km2"]=OSI.hemi[h].clim[m]; r[h+"_sd_1e6km2"]=S.SD[h][m]; r[h+"_n"]=v.length;
      }
      rows.push(r);
    }
    return {nm:"1991–2020 climatology", file:"olympus_sea_ice_climatology_1991_2020.csv", cols, rows, cur:MON[lgNow()%12], curKey:"month",
      head:[["What","The baseline every anomaly on the deck is measured against: the mean of the 30 values of each calendar month, 1991–2020, from the deck’s own extent record. Means as carried (4 decimals); σ computed in this page."]],
      comment:["Mean of the 30 values of each calendar month 1991-2020 from this deck's extent record (monthly-mean-field method), as carried.",
               "sd: sample standard deviation of the same 30 values, computed in the page."]};
  }
  if(id==="rapid"){
    const cols=[{h:"Month",k:"yyyymm",kind:"txt"},{h:"AMOC",sub:"moc_mar_hc10, Sv",k:"moc_sv",kind:"num",dp:3},
      {h:"Florida Current",sub:"t_gs10, Sv",k:"florida_sv",kind:"num",dp:3},{h:"Ekman",sub:"t_ek10, Sv",k:"ekman_sv",kind:"num",dp:3},
      {h:"Upper mid-ocean",sub:"t_umo10, Sv",k:"upper_mid_ocean_sv",kind:"num",dp:3},{h:"Status",k:"status",kind:"tag"}];
    const rows=AM.months.map((ym,i)=>({yyyymm:ym, moc_sv:AM.moc[i], florida_sv:AM.gs[i], ekman_sv:AM.ek[i], upper_mid_ocean_sv:AM.umo[i], status:"MEAS"}));
    return {nm:"RAPID 26.5°N, monthly", file:"olympus_rapid_26n_monthly.csv", cols, rows, cur:lgYM(lgNow()),
      head:[["What","Atlantic overturning and its components at 26.5°N, as monthly means of RAPID’s 12-hourly, 10-day low-passed transports (fill values excluded), 3 decimals."],
            ["Source","RAPID-MOCHA-WBTS "+lgEsc(AM.version)+", doi:"+lgEsc(AM.doi)+". Record mean "+AM.mean.toFixed(2)+" Sv, monthly SD "+AM.sd.toFixed(1)+" Sv."]],
      comment:["RAPID-MOCHA-WBTS 26.5N "+AM.version+", doi:"+AM.doi+" (moc_transports.nc).",
               "Calendar-month means of the 12-hourly, 10-day low-passed transports; fill values (-99999) excluded; 3 decimals.",
               "Positive northward. Months outside "+AM.m0+"-"+AM.mN+" have no observation and are not listed."]};
  }
  if(id==="roni"){
    const E=ensoData(); if(!E) return null;
    const cols=[{h:"Season",k:"season",kind:"txt"},{h:"Centre month",k:"centre_yyyymm",kind:"txt"},{h:"RONI",sub:"°C",k:"roni_c",kind:"sgn",dp:2}];
    const rows=E.roni.v.map((v,i)=>{ const t=LG_RONI0+i; return {season:LG_SEAS[t%12]+" "+Math.floor(t/12), centre_yyyymm:lgYM(t), roni_c:v}; });
    return {nm:"RONI, 3-month seasons", file:"olympus_roni_seasons.csv", cols, rows, cur:lgYM(lgNow()), curKey:"centre_yyyymm",
      head:[["What","NOAA CPC’s Relative Oceanic Niño Index for every overlapping 3-month season since DJF 1950, as published. Each season is listed under its centre month."],
            ["Source","NOAA CPC <code>RONI.ascii.txt</code>, rebuilt with the living layer ("+lgEsc(String(LIVE.meta.built).slice(0,10))+")."]],
      comment:["NOAA CPC Relative Oceanic Nino Index (RONI), "+E.roni.t0+" to "+E.roni.last+", as published in RONI.ascii.txt.",
               "Each overlapping 3-month season is listed with its centre month. Living layer built "+LIVE.meta.built+"."]};
  }
  if(id==="nino"){
    const E=ensoData(); if(!E) return null; const W=E.weekly, t0=Date.parse(W.series_t0+"T12:00:00Z");
    const cols=[{h:"Week centred",k:"week_centre",kind:"txt"},{h:"Niño-3.4 relative",sub:"°C",k:"nino34_relative_c",kind:"sgn",dp:1}];
    const rows=W.series34.map((v,j)=>({week_centre:new Date(t0+j*7*864e5).toISOString().slice(0,10), nino34_relative_c:v}));
    return {nm:"Niño-3.4 relative, weekly", file:"olympus_nino34_relative_weekly.csv", cols, rows, cur:null,
      head:[["What","NOAA CPC’s weekly relative Niño-3.4 SST anomaly (OISST v2.1), the "+rows.length+" most recent weeks, as published. The page carries this window only; CPC’s file starts in 1981."],
            ["Latest","Week of "+fmtDay(W.week)+": relative "+lgS(W.rel.nino34,1)+" °C, traditional "+lgS(W.trad34,1)+" °C."]],
      comment:["NOAA CPC weekly relative Nino-3.4 SST anomaly, rel_wksst9120.txt, weeks centred "+rows[0].week_centre+" to "+rows[rows.length-1].week_centre+".",
               "Latest traditional (non-relative) weekly value: "+W.trad34+" C. Living layer built "+LIVE.meta.built+"."]};
  }
  if(id==="nsidc"){
    const cols=[{h:"Hemisphere",k:"hemisphere",kind:"txt"},{h:"Month",k:"yyyymm",kind:"txt"},{h:"Value",sub:"10⁶ km²",k:"extent_1e6km2",kind:"num",dp:2},
                {h:"What",k:"note",kind:"txt"},{h:"Status",k:"status",kind:"tag"}];
    const rows=[]; for(const h of ["sh","nh"]) for(const a of (ANCHORS[h]||[])) rows.push({hemisphere:LG_HEMI[h], yyyymm:a.ym, extent_1e6km2:a.v, note:a.note, status:"REF"});
    return {nm:"NSIDC daily records", file:"olympus_nsidc_reference_points.csv", cols, rows, cur:null,
      head:[["What","Published NSIDC daily extents, drawn as orange rings on the timeline. A different algorithm and a daily, not monthly, value: never averaged into the deck’s record."]],
      comment:["NSIDC Sea Ice Index daily extents as quoted on the deck; a different algorithm and a daily value, shown for comparison only."]};
  }
  if(id==="kp"){
    const K=LIVE.kp; if(!K) return null;
    const cols=[{h:"Time",sub:"UTC",k:"time_utc",kind:"txt"},{h:"Kp",sub:"estimated",k:"kp",kind:"num",dp:2}];
    const rows=K.series.map(([t,v])=>({time_utc:t, kp:v}));
    return {nm:"Kp, latest 6 hours", file:"olympus_kp_estimated.csv", cols, rows, cur:null,
      head:[["What","NOAA SWPC’s estimated planetary K index, every third one-minute value, the newest "+rows.length+". A snapshot from the build: it does not move with the dial."]],
      comment:["NOAA SWPC estimated planetary K index (planetary_k_index_1m.json), every third 1-minute value, 2 decimals.",
               "Definitive Kp is published by GFZ Potsdam. Living layer built "+LIVE.meta.built+"."]};
  }
  return null;
}
const LG_SER = [["extent","Sea-ice extent · monthly"],["clim","Climatology 1991–2020"],["rapid","RAPID 26.5°N · monthly"],
                ["roni","RONI · seasons"],["nino","Niño-3.4 · weekly"],["nsidc","NSIDC reference points"],["kp","Kp · 6 h"]];

function lgCell(c,v,html){
  if(c.kind==="tag") return v ? (html?lgTag(v):v) : "";
  if(v==null || v==="" ) return "";
  if(c.kind==="num") return (+v).toFixed(c.dp);
  if(c.kind==="sgn") return html ? lgS(+v,c.dp) : (+v).toFixed(c.dp);
  if(c.kind==="int") return String(Math.round(+v));
  return html ? lgEsc(v) : String(v);
}
function lgCSVText(S){
  const q = s => /[",\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s;
  const cols=S.cols.filter(c=>!c.nocsv);
  const lines=["# Olympus Deck log: "+S.nm,
    "# Deck log built "+(DLK.build?DLK.build.built:"?")+"; living layer built "+((typeof LIVE!=="undefined"&&LIVE.meta)?LIVE.meta.built:"?")+"; exported "+new Date().toISOString().slice(0,19)+"Z"];
  for(const c of S.comment||[]) lines.push("# "+c);
  lines.push("# Empty field = no value; a status column, where present, says why.");
  lines.push(cols.map(c=>c.k).join(","));
  for(const r of S.rows) lines.push(cols.map(c=>q(lgCell(c,r[c.k],false))).join(","));
  return lines.join("\n")+"\n";
}
function lgSeriesHTML(){
  const S=lgSeries(DL.ser);
  const pick='<div class="dlog-sers" role="group" aria-label="Series">'+LG_SER.map(([id,nm])=>
    '<button type="button" data-ser="'+id+'" aria-pressed="'+(id===DL.ser)+'">'+lgEsc(nm)+'</button>').join("")+'</div>';
  if(!S) return '<section>'+pick+'<p class="dlog-note">This record is not carried in this build.</p></section>';
  const cols=S.cols.filter(c=>!c.notable), ck=S.curKey||"yyyymm";
  const th=cols.map(c=>'<th'+((c.kind==="num"||c.kind==="sgn"||c.kind==="int")?' class="v"':'')+'>'+lgEsc(c.h)+(c.sub?'<small>'+lgEsc(c.sub)+'</small>':'')+'</th>').join("");
  const body=S.rows.map(r=>'<tr data-k="'+lgEsc(r[ck]||"")+'"'+(r._gap?' class="gap"':'')+'>'+cols.map(c=>
    '<td'+((c.kind==="num"||c.kind==="sgn"||c.kind==="int")?' class="v"':'')+'>'+lgCell(c,r[c.k],true)+'</td>').join("")+'</tr>').join("");
  return '<section>'+pick
    +'<dl class="dlog-meta">'+S.head.map(([a,b])=>'<dt>'+lgEsc(a)+'</dt><dd>'+b+'</dd>').join("")
    +'<dt>Rows</dt><dd>'+S.rows.length+(S.cur?' · the month on the dial is highlighted':'')+'</dd></dl>'
    +'<div class="dlog-acts"><button type="button" class="pri" id="dlogSave">Download CSV</button><button type="button" id="dlogCopy">Copy CSV</button>'
    +'<button type="button" id="dlogRaw">Show as text</button><span class="msg" id="dlogMsg" aria-live="polite"></span></div>'
    +'<textarea class="dlog-raw" id="dlogText" readonly hidden aria-label="CSV text"></textarea>'
    +'<div class="dlog-tw tall" id="dlogTW"><table class="dlt"><thead><tr>'+th+'</tr></thead><tbody>'+body+'</tbody></table></div>'
    +'</section>';
}
function lgMarkRow(scroll){
  const tw=$("#dlogTW"); if(!tw) return;
  const S={extent:lgYM(lgNow()), rapid:lgYM(lgNow()), roni:lgYM(lgNow()), clim:MON[lgNow()%12]}[DL.ser];
  let hit=null;
  tw.querySelectorAll("tr.cur").forEach(r=>r.classList.remove("cur"));
  if(S) tw.querySelectorAll('tr[data-k="'+S+'"]').forEach(r=>{ r.classList.add("cur"); hit=r; });
  if(scroll && hit){ const top=hit.offsetTop-tw.clientHeight/2; tw.scrollTop=Math.max(0,top); }
}

/* Saving a file. Inside the claude.ai viewer a page cannot start a download
   itself, so the viewer's own save is used, and the viewer confirms it. On an
   ordinary web host the browser saves it directly. Where neither is possible
   the text is shown so it can be selected and copied. */
function lgSaver(){
  if(DL.saver!==undefined) return DL.saver;
  const C = (typeof window!=="undefined") ? window.claude : null;
  DL.saver = (C && typeof C.use==="function") ? C.use("downloads").then(d=>d||null).catch(()=>null) : null;
  return DL.saver;
}
async function lgSave(S){
  const msg=$("#dlogMsg"), text=lgCSVText(S);
  const say=t=>{ if(msg) msg.textContent=t; };
  const P=lgSaver();
  if(P){
    const d=await P;
    if(!d){ say("Saving files is not available here. Use Copy CSV or Show as text."); return; }
    try{ await d.save({filename:S.file, data:text}); say("Saved "+S.file); }
    catch(e){ const c=e&&e.code;
      say(c==="declined"?"Not saved.":c==="rate_limited"?"A save is already waiting for an answer.":"Saving is not available here. Use Copy CSV or Show as text."); }
    return;
  }
  try{
    const url=URL.createObjectURL(new Blob([text],{type:"text/csv;charset=utf-8"}));
    const a=document.createElement("a"); a.href=url; a.download=S.file; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(()=>URL.revokeObjectURL(url),5000);
    say("Saved "+S.file);
  }catch(e){ say("Saving is not available here. Use Copy CSV or Show as text."); }
}
function lgShowText(S){
  const ta=$("#dlogText"); if(!ta) return;
  ta.value=lgCSVText(S); ta.hidden=false; ta.focus(); ta.select();
}
async function lgCopy(S){
  const msg=$("#dlogMsg"), text=lgCSVText(S);
  try{ await navigator.clipboard.writeText(text); msg.textContent="Copied "+S.rows.length+" rows."; }
  catch(e){ lgShowText(S); msg.textContent="Copy is blocked here; the text is selected below."; }
}

/* ============================ sources ============================ */
function lgA(u,t){ return '<a href="'+lgEsc(u)+'" target="_blank" rel="noopener">'+lgEsc(t||u)+'</a>'; }
function lgGrid(o){ return o.d+"° · "+o.w+" × "+o.h; }
function lgCards(){
  const A=(typeof LIVE!=="undefined"&&LIVE)?LIVE:{}, E=ensoData(), R=DLK.sii||{}, C=DLK.checks||{};
  const src=OCEAN.src, sat=SATIMG.layers||[];
  const cards=[];
  cards.push({t:"Sea-ice concentration and extent", tag:"MEAS", lay:"ice · hero · timeline · anomaly stream", ex:"passive_mw", rows:[
    ["Products", lgRuns().map(x=>(x.P.url?lgA(x.P.url,x.r[1]):lgEsc(x.r[1]))+(x.r[3]?" fast track":"")+": "+lgMonYr(x.t0)+(x.t1>x.t0?" – "+lgMonYr(x.t1):"")+" ("+(x.b-x.a+1)+" frame"+(x.b>x.a?"s":"")+")"+(x.P.doi?" · doi:"+lgEsc(x.P.doi):"")).join("<br>")],
    ["Licence", "OSI-450-a and OSI-430-a: free of charge, with the credit <b>Copyright EUMETSAT</b> shown under the product. OSI-438: CC BY 4.0."],
    ["Access", "met.no THREDDS over OPeNDAP, variable <code>ice_conc</code> of the monthly files, read by <code>ingest/ingest_osisaf.py</code>. Read in place: no file-level checksum is kept."],
    ["Grid", "EASE2 25 km, 432 × 432 per hemisphere, equal-area: every cell is 625 km²."],
    ["Coverage", lgMonYr(lgFirst())+" – "+lgMonYr(lgLast())+": "+OSI.hemi.sh.n+" frames over "+(lgLast()-lgFirst()+1)+" months. April–June 1986 and December 1987 are missing at source."],
    ["Extent, step by step", "<ol><li><code>ice_conc</code> of the monthly-mean file (%)</li><li>cells ≥ 15 % counted on the source grid</li><li>× 625 km², ÷ 10⁶, rounded to 3 decimals (1,000 km²)</li><li>climatology: mean of the 30 values of each calendar month 1991–2020, 4 decimals</li><li>anomaly = extent − climatology; σ and rank computed in the page</li></ol>"],
    ["Map, step by step", "<ol><li>each source cell forward-binned onto a 220 × 220 grid on the deck’s disc (EPSG:3413 north, EPSG:3976 south, radius 1 at 45°); a disc cell is "+lgDiscKm()+" km on the projection plane and holds the mean of the source cells in it</li><li>rounded to 1 % steps, packed losslessly in PNG, decoded byte-exact</li><li>below 5 % transparent; 13–20 % drawn as the 15 % edge; colour and opacity ramp above</li></ol>"],
    ["Uncertainty", "<b>Not carried.</b> The monthly files carry none. OSI SAF’s daily files carry per-cell <code>total_standard_uncertainty</code>; the deck does not propagate it into the extent."],
    ["Differs from", "OSI SAF’s own published extent (see the Sea Ice Index card and the checks below) and NSIDC’s, which uses a different algorithm."]]});
  cards.push({t:"OSI SAF Sea Ice Index (reference)", tag:"REF", lay:"log only", ex:"sie_index", rows:[
    ["Product", lgEsc(R.product||"not carried")+(R.page?" · "+lgA(R.page,"product page"):"")],
    ["Quantity", lgEsc(R.quantity||"")],
    ["Files", R.hemi?["nh","sh"].map(h=>lgA(R.hemi[h].url,h.toUpperCase())+" · created "+lgEsc(R.hemi[h].created)+" · sha256 <code>"+lgEsc(R.hemi[h].sha256.slice(0,16))+"…</code>").join("<br>"):""],
    ["Retrieved", lgEsc(R.retrieved_utc||"")+" by <code>ingest/fetch_sie_index.py</code>. Kept in km² as published; −999 kept as empty."],
    ["Inputs", "OSI-450-a1 v3.1 (to Dec 2020), OSI-430-a (2021–2024), OSI-438 (2025 →) and a near-real-time AMSR2 product, per OSI SAF. Not the same versions as the deck’s record in every month."],
    ["Use on the deck", "None. It is shown in the log beside the deck’s own number and never enters a computation."]]});
  cards.push({t:"RAPID-MOCHA-WBTS 26.5°N", tag:"MEAS", lay:"AMOC gauge · timeline tooltip · deep-limb speed", ex:"rapid", rows:[
    ["Product", "Atlantic meridional overturning and components, "+lgEsc(AM.version)+", doi:"+lgEsc(AM.doi)+" · "+lgA("https://rapid.ac.uk/","rapid.ac.uk")],
    ["Coverage", lgMonYr(lgAbs(AM.m0))+" – "+lgMonYr(lgAbs(AM.mN))+", "+AM.months.length+" months. Outside it the gauge reads NO OBS."],
    ["Step by step", "<ol><li><code>moc_mar_hc10</code>, <code>t_gs10</code>, <code>t_ek10</code>, <code>t_umo10</code>: 12-hourly, 10-day low-passed, Sv</li><li>fill value −99999 excluded</li><li>calendar-month mean, 3 decimals</li><li>deep-limb animation speed = monthly AMOC ÷ record mean "+AM.mean.toFixed(2)+" Sv, not below 0.25; the record mean when there is no observation</li></ol>"],
    ["Uncertainty", "<b>Not carried.</b> RAPID’s error budget is in McCarthy et al. (2015), <i>Progress in Oceanography</i> 130. The gauge’s ±3.2 Sv is the monthly variability of the record, not a measurement error."],
    ["Licence", "Free with acknowledgement, per the file: “Data from the RAPID AMOC observing project … are freely available from rapid.ac.uk”. Cite the DOI."]]});
  cards.push({t:"NOAA Global Drifter Program, near-surface climatology", tag:"CLIM", lay:"near-surface currents · Speed / Temp / Coverage · cursor readout", ex:"ocean_flow", rows:[
    ["Product", lgEsc(src.drifter.name)+" v"+lgEsc(src.drifter.version)+" · doi:"+lgEsc(src.drifter.doi)+" · "+lgEsc(src.drifter.cite)],
    ["Licence", lgEsc(src.drifter.licence)],
    ["Files", lgA(src.drifter.url,"annual means")+" · "+lgA(src.seasonal.url,"monthly means")],
    ["Coverage", lgEsc(src.drifter.coverage)+". Seasonal: "+lgEsc(src.seasonal.coverage)+". SST: "+lgEsc(src.sst.coverage)+"."],
    ["Grids, as carried", "velocity "+lgGrid(OCEAN.flow)+" · monthly anomaly "+lgGrid(OCEAN.seasonal)+" × 12 · SST "+lgGrid(OCEAN.sst)],
    ["Step by step", "<ol><li>u, v per component as sign × √(|u| ÷ "+OCEAN.flow.vmax+" m/s) in 8 bits; decoded as sign × e² × "+OCEAN.flow.vmax+" (max error "+(OCEAN.flow_stats.encode_max_err_ms*100).toFixed(2)+" cm/s)</li><li>twelve monthly anomalies at 1° added to the annual mean; RMS against the true monthly field "+(OCEAN.seasonal_stats.rms_with_season_ms*100).toFixed(2)+" cm/s (annual mean alone "+(OCEAN.seasonal_stats.rms_annual_only_ms*100).toFixed(2)+")</li><li>sampled bilinearly; while the timeline plays, blended between adjacent climatological months</li><li>particles advected at a fixed display rate, about "+OC_DAYS_PER_SEC+" days of ocean per second</li><li>SST in 8 bits over "+OCEAN.sst.tmin+" to "+OCEAN.sst.tmax+" °C (max error "+OCEAN.sst_stats.encode_max_err_c+" °C); "+OCEAN.sst_stats.dropped_below_freezing+" cells below freezing dropped</li><li>coverage: drifter-days per square degree, log-encoded, 0 to "+OCEAN.flow.nmax+"</li></ol>"],
    ["Uncertainty", "<b>Not carried.</b> Where no drifter sampled a cell, nothing is drawn and the readout says NO OBS."]]});
  cards.push({t:"Antarctic Circumpolar Current fronts", tag:"MEAN", lay:"ACC fronts", ex:"ocean_fronts", rows:[
    ["Product", lgEsc(src.fronts.name)+", "+lgEsc(src.fronts.version)+" · doi:"+lgEsc(src.fronts.doi)+" · "+lgEsc(src.fronts.cite)],
    ["Licence", lgEsc(src.fronts.licence)+" · "+lgA(src.fronts.url,"SEANOE")],
    ["Step by step", "<ol>"+OCEAN.fronts.map(f=>"<li>"+lgEsc(f.label)+": "+f.n0+" vertices simplified to "+(f.pts.length/2)+"</li>").join("")+"</ol>"],
    ["Coverage", lgEsc(src.fronts.coverage)+". The same line for every month."]]});
  cards.push({t:"Deep and bottom-water limbs", tag:"SCHEMATIC", lay:"deep & bottom-water limbs", ex:"deep_schematic", rows:[
    ["What", lgEsc(src.deep.detail)],
    ["Measured points", OCEAN.nodes.map(n=>lgEsc(n.label)+" ("+n.depth+" m)").join(" · ")],
    ["Scale", "Drawn inside the globe at true depth ×"+OCEAN.depth.exag+" vertically ("+OCEAN.depth.scale_m+" m = "+OCEAN.depth.radius+" of the radius); horizontal ×1."],
    ["Cited", lgEsc(src.deep.cite)]]});
  if(E) cards.push({t:"El Niño: status, indices, SST anomaly", tag:"AS OF", lay:"featured event · El Niño contours", ex:"featured_event", rows:[
    ["Status", lgEsc(E.status.alert)+", issued "+fmtDay(E.status.issued)+(E.status.next?", next "+fmtDay(E.status.next):"")+" · "+lgA(E.status.url,"CPC discussion")],
    ["Weekly", "Niño-3.4 week of "+fmtDay(E.weekly.week)+": relative "+lgS(E.weekly.rel.nino34,1)+", traditional "+lgS(E.weekly.trad34,1)+" °C · "+lgA(E.weekly.url,"rel_wksst9120.txt")],
    ["RONI", E.roni.v.length+" seasons, "+lgEsc(E.roni.t0)+" – "+lgEsc(E.roni.last)+" · "+lgA(E.roni.url,"RONI.ascii.txt")],
    ["SST field", lgEsc(E.field.source)+", days "+E.field.days.map(d=>d.slice(6,8)).join(" ")+" "+MON[+E.field.days[0].slice(4,6)-1]+", "+E.field.res_deg+"° block mean, 3 × 3 smoothing, contoured at "+E.field.levels.map(v=>lgS(v,0)).join(" / ")+" °C, "+E.field.window[2]+"° to "+E.field.window[3]+"° latitude · base "+lgEsc(E.field.base)],
    ["Build check", "Box mean "+lgS(E.field.n34_check,2)+" °C against CPC’s traditional "+lgS(E.weekly.trad34,1)+" °C for the same week; the build stops if they differ by more than 0.25."],
    ["Refresh", "Rebuilt with the living layer, "+lgEsc(String(LIVE.meta.built).replace("T"," ").slice(0,16))+" UTC."]]});
  const liveRows=[];
  if(A.aurora) liveRows.push(["Aurora", lgEsc(A.aurora.source)+", MODEL, observed "+lgEsc(A.aurora.observed)+" · 360 × 46 grid from 45°; values below "+AUR_CUT+" not drawn; brightness normalised on this frame’s maximum ("+aurTop()+"), ten colour steps, softened, turned ×"+AUR_SPIN+" · "+lgA(A.aurora.url,"source")]);
  if(A.kp) liveRows.push(["Kp", lgEsc(A.kp.source)+", "+A.kp.latest+" at "+lgEsc(A.kp.time)+" · every third one-minute estimate kept · "+lgA(A.kp.url,"source")]);
  if(A.drift){ const D0=A.drift.sh||A.drift.nh; liveRows.push(["Ice drift", lgEsc(A.drift.source)+", "+lgEsc(D0.t0)+" → "+lgEsc(D0.t1)+" · <code>"+lgEsc((A.drift.nh||D0).file)+"</code>, <code>"+lgEsc((A.drift.sh||D0).file)+"</code> · nominal-quality vectors only · true length unless ×5 or ×15 is shown on screen · vectors shorter than 0.6 px not drawn · Copyright EUMETSAT"]); }
  if(A.sar) liveRows.push(["Sentinel-1", lgEsc(A.sar.source)+", "+A.sar.n+" acquisitions since "+lgEsc(A.sar.since)+" · one outline per acquisition, poleward of 60°, fading over "+A.sar.hours+" h · "+lgA(A.sar.url,"catalogue")]);
  liveRows.push(["Build", "<code>ingest/build_events.py</code>, injected by <code>ingest/inject_live.py</code>; living layer built "+lgEsc(String(LIVE.meta.built))+". Each layer keeps its own observation time."]);
  cards.push({t:"The living layer", tag:"AS OF", lay:"aurora · drift · SAR · Kp", ex:"live_transport", rows:liveRows});
  cards.push({t:"Base imagery", tag:"AS OF", lay:"satellite imagery", ex:"reprojection", rows:sat.map(L=>[L.nm,
    (L.gibs?"NASA GIBS <code>"+lgEsc(L.gibs)+"</code>":"")+(L.time?", "+(L.gdays&&L.gdays.length?L.gdays.join(" + "):L.time):", no date")
    +((L.gsrc&&L.gsrc.sources)?" · globe sheet from "+L.gsrc.sources.length+" request"+(L.gsrc.sources.length>1?"s":"")+", sha256 "+L.gsrc.sources.map(s=>"<code>"+lgEsc(String(s.sha256).slice(0,12))+"…</code>").join(" "):"")]).concat([
    ["Step by step", "<ol><li>north: GIBS EPSG:3413 placed by scale and offset; south: GIBS EPSG:3031 resampled into EPSG:3976</li><li>beyond latitude 52.6°, where the polar tiles stop, filled from plate carrée</li><li>globe: one global plate carrée sheet resampled per screen cell</li><li>drawn at 95 % opacity, then dimmed by 40 % so the measurements stay brightest</li></ol>"],
    ["Built", lgEsc(SATIMG.built)+" by <code>ingest/build_imagery.py</code>"]])});
  cards.push({t:"Geometry, stations and reference marks", tag:"STATIC", lay:"ice shelves · graticule · stations · timeline rings", ex:"shelf", rows:[
    ["Coastlines and shelves", "Natural Earth 10 m, simplified and projected on the data’s grid by <code>ingest/build_geo.py</code>. The globe’s coastline ("+EX.coast.length+" rings) is carried without a recorded source."],
    ["Stations", (STATIONS.S.length+STATIONS.N.length)+" sites typed into the page, labelled “COMNAP · SCAR master list”. The Atlas register of 166 is not wired to the deck."],
    ["NSIDC records", "Five published NSIDC daily extents, drawn as rings on the timeline. REF only."],
    ["SIM layers", LAYERS.filter(L=>L.sim).map(L=>lgEsc(L.nm)).join(" · ")+": illustration, no values."]]});
  return cards;
}
function lgChecks(){
  const out=[], R=DLK.sii, C=DLK.checks||{};
  // --- run in the page, on the values it carries ---
  { let worst=0; const S=anomStats();
    for(const h of ["sh","nh"]) for(let m=0;m<12;m++){
      const v=S.byMonth[h][m].filter(q=>q[0]>=1991&&q[0]<=2020).map(q=>q[1]);
      worst=Math.max(worst, Math.abs(v.reduce((a,b)=>a+b,0)/v.length-OSI.hemi[h].clim[m]));
    }
    // the extents are carried to 0.001, so a mean of thirty of them is only good to 0.0005
    out.push({r:worst<=0.0005?"ok":"diff", b:"Climatology recomputed from the carried extents: largest difference "+worst.toFixed(5)+" ×10⁶ km², inside the 0.0005 that extents carried to three decimals allow.", w:"run in this page"}); }
  if(R && R.hemi){
    const parts=[];
    for(const h of ["nh","sh"]){
      const d=[]; for(let t=lgFirst();t<=lgLast();t++){ const k=lgFrame(h,t), p=lgSII(h,t); if(k>=0 && p!=null) d.push(OSI.hemi[h].ext[k]-p/1e6); }
      const mu=d.reduce((a,b)=>a+b,0)/d.length, up=d.filter(x=>x>0).length;
      parts.push("<b>"+LG_HEMI[h]+"</b>: deck higher in "+up+" of "+d.length+" months, mean "+lgS(mu,3)+", from "+lgS(Math.min(...d),3)+" to "+lgS(Math.max(...d),3)+" ×10⁶ km²");
    }
    out.push({r:"diff", b:"The deck’s extent against OSI SAF’s published index, in every month both carry. "+parts.join("; ")+". The two are different quantities: the deck thresholds the month’s mean concentration field, so a cell the ice edge crosses during the month counts in full; the index averages the daily extents.", w:"run in this page"});
  }
  // --- run at build time against the publishers' files (ingest/check_sources.py) ---
  const when="checked "+String(C.checked_utc||"").slice(0,10)+" by ingest/check_sources.py";
  if(C.extent_method && C.extent_method.length){
    out.push({r:"note", b:"<b>Why the two extents differ</b>, recomputed from OSI SAF’s own files: "+C.extent_method.map(x=>
      LG_HEMI[x.hemi]+" "+lgMonYr(lgAbs(x.ym))+": monthly-mean field "+x.monthly_field.toFixed(3)+" · mean of "+x.days+" daily extents "+x.daily_mean_gt15.toFixed(3)+" · published "+(x.published_index==null?"—":x.published_index.toFixed(3))).join("; ")
      +". In the climate-record months the mean of the daily extents reproduces the published index, so the whole gap is the order of averaging. In the AMSR months it does not: OSI SAF builds recent index months from inputs that include a near-real-time AMSR2 product, not only the OSI-438 files the deck reads. The cause of that second gap is not established here.", w:when});
  }
  for(const x of (C.fast_track||[])) if(x.consolidated_file) out.push({r:"diff", b:LG_HEMI[x.hemi]+" "+lgMonYr(lgAbs(x.ym))+" is on the deck from the fast-track file ("+x.fast_track.toFixed(3)+"). The consolidated file, created "+x.consolidated_created+", gives "+x.consolidated.toFixed(3)+" ("+lgS(x.consolidated-x.fast_track,3)+"). The record has not been refreshed since.", w:when});
  if(C.rapid) out.push({r:Object.values(C.rapid.vars).every(v=>v.equal===v.months)?"ok":"diff", b:"RAPID: "+Object.entries(C.rapid.vars).map(([k,v])=>"<code>"+v.source+"</code> "+v.equal+"/"+v.months).join(" · ")+" monthly values reproduced from <code>moc_transports.nc</code> "+lgEsc(C.rapid.version)+" (created "+lgEsc(C.rapid.created)+", sha256 <code>"+lgEsc(C.rapid.sha256.slice(0,16))+"…</code>).", w:when});
  if(C.enso) out.push({r:(C.enso.roni.equal===C.enso.roni.values && C.enso.weekly.equal===C.enso.weekly.values)?"ok":"diff", b:"ENSO: RONI "+C.enso.roni.equal+"/"+C.enso.roni.values+" and weekly relative Niño-3.4 "+C.enso.weekly.equal+"/"+C.enso.weekly.values+" values identical to NOAA CPC’s files, for the living layer built "+lgEsc(C.enso.live_built)+". The layer is rebuilt daily; later builds are checked by <code>ingest/enso.py</code>.", w:when});
  return out;
}
function lgManifestHTML(){
  const cards=lgCards(), checks=lgChecks();
  return '<section>'
    +'<p class="dlog-note">Where every layer comes from and what happens between the published value and the pixel. Anything this page cannot trace back is said to be untraceable, not left out. '
    +'Gridded fields are not re-exported here: use the product named.</p>'
    +'<div><h3 data-ex="log_checks">Checks <span class="n">'+checks.length+'</span></h3><div class="dlog-checks">'
    +checks.map(c=>'<div class="dlog-check"><span class="r '+c.r+'">'+({ok:"agrees",diff:"differs",note:"method"}[c.r])+'</span><div>'+c.b+'</div><span class="when">'+lgEsc(c.w)+'</span></div>').join("")
    +'</div></div>'
    +'<div><h3>Sources <span class="n">'+cards.length+'</span></h3><div class="dlog-cards">'
    +cards.map(c=>'<article class="dlog-card"'+(c.ex?' data-ex="'+c.ex+'"':'')+'><h4>'+lgEsc(c.t)+lgTag(c.tag)+'</h4><div class="lyr">'+lgEsc(c.lay)+'</div>'
      +'<dl class="dlog-meta">'+c.rows.map(([a,b])=>'<dt>'+lgEsc(a)+'</dt><dd>'+b+'</dd>').join("")+'</dl></article>').join("")
    +'</div></div></section>';
}

/* ============================ shell ============================ */
function lgStamp(){
  const el=$("#dlogStamp"); if(!el) return;
  el.innerHTML="log built "+lgEsc(String((DLK.build||{}).built||"?").slice(0,16).replace("T"," "))
    +"<br>living layer "+lgEsc(String((typeof LIVE!=="undefined"&&LIVE.meta)?LIVE.meta.built:"?").slice(0,16).replace("T"," "))+" UTC";
}
function lgRender(){
  if(!DL.open) return;
  const t=lgNow(), body=$("#dlogBody");
  $("#dlogYm").innerHTML=lgYM(t)+"<small>"+lgMonYr(t)+"</small>";
  $$(".dlog-tabs button").forEach(b=>b.setAttribute("aria-selected",String(b.dataset.tab===DL.tab)));
  const keep=body.scrollTop;
  if(DL.tab==="frame") body.innerHTML=lgFrameHTML();
  else if(DL.tab==="series"){ body.innerHTML=lgSeriesHTML(); lgMarkRow(true); }
  else body.innerHTML=lgManifestHTML();
  body.scrollTop=keep;
  DL.key=DL.tab+"|"+DL.ser+"|"+t;
}
/* called from sync(): cheap unless the month on the dial changed */
function logSync(){
  if(!DL.open) return;
  const t=lgNow();
  if(DL.tab==="series"){ const k="series|"+DL.ser+"|"+t; if(k!==DL.key){ DL.key=k; $("#dlogYm").innerHTML=lgYM(t)+"<small>"+lgMonYr(t)+"</small>"; lgMarkRow(!st.playing); } return; }
  if(DL.tab==="manifest"){ $("#dlogYm").innerHTML=lgYM(t)+"<small>"+lgMonYr(t)+"</small>"; return; }
  if(DL.key!==DL.tab+"|"+DL.ser+"|"+t) lgRender();
}
function logOpen(on, tab){
  DL.open = on===undefined ? !DL.open : !!on;
  if(tab) DL.tab=tab;
  const p=$("#dlog"), b=$("#logBtn");
  p.hidden=!DL.open; b.setAttribute("aria-pressed",String(DL.open));
  if(DL.open){ lgStamp(); lgRender(); hideEx(); }
  else { try{ b.focus({preventScroll:true}); }catch(e){} }
}
function logStep(d){
  const k=Math.max(0,Math.min(NMON-1,monIdx()+d));
  st.t=k; st.playing=false; $("#playIcon").setAttribute("d","M2.5 1.5 10 6l-7.5 4.5z");
  sync(); drawTL();
}
function decklog(){
  const btn=$("#logBtn"), p=$("#dlog"); if(!btn||!p) return;
  btn.addEventListener("click",()=>logOpen());
  $("#dlogClose").addEventListener("click",()=>logOpen(false));
  $("#dlogPrev").addEventListener("click",()=>logStep(-1));
  $("#dlogNext").addEventListener("click",()=>logStep(1));
  $("#dlogLatest").addEventListener("click",()=>logStep(NMON));
  $$(".dlog-tabs button").forEach(b=>b.addEventListener("click",()=>{ DL.tab=b.dataset.tab; $("#dlogBody").scrollTop=0; lgRender(); }));
  $("#dlogBody").addEventListener("click",e=>{
    const s=e.target.closest("[data-ser]");
    if(s){ DL.ser=s.dataset.ser; lgRender(); return; }
    const S=()=>lgSeries(DL.ser);
    if(e.target.closest("#dlogSave")) lgSave(S());
    else if(e.target.closest("#dlogCopy")) lgCopy(S());
    else if(e.target.closest("#dlogRaw")) lgShowText(S());
  });
  p.addEventListener("keydown",e=>{
    if(e.target && /^(TEXTAREA|INPUT|SELECT)$/.test(e.target.tagName)) return;
    if(e.key==="ArrowLeft"){ e.preventDefault(); logStep(-1); }
    else if(e.key==="ArrowRight"){ e.preventDefault(); logStep(1); }
    else if(e.key==="Escape"){ logOpen(false); }
  });
  document.addEventListener("keydown",e=>{
    if(e.defaultPrevented || e.ctrlKey || e.metaKey || e.altKey) return;
    const tg=e.target && e.target.tagName;
    if(tg && /^(TEXTAREA|INPUT|SELECT)$/.test(tg)) return;
    if(e.key==="l" || e.key==="L"){ logOpen(); }
  });
  lgSaver();
  // a bare #log, #log-series or #log-sources opens it where the link points
  const h=(location.hash||"").slice(1);
  if(/^log(-series|-sources)?$/.test(h)) logOpen(true, h==="log-series"?"series":h==="log-sources"?"manifest":"frame");
}
