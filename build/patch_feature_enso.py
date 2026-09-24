#!/usr/bin/env python3
"""
Olympus — the deck opens on a featured event: El Niño, 2026.

David, 24 Sep 2026: the opening view should be the globe, coloured by Temp, with
the season on, looking at the Pacific, with El Niño as a featured event — its own
learn card and a data widget with links.

What that takes, and one correction to it:

  - The opening state becomes GLOBE · Temp · Season, camera over the equatorial
    Pacific, tilted south so the Amundsen and Ross seas sit on the lower limb —
    El Niño and the place it reaches in Antarctica in one view.

  - The Temp colouring cannot show El Niño on its own. It is the drifters'
    forty-year annual mean, and its ramp puts everything above 22 °C in one
    orange, so the equatorial Pacific looks the same in 1998, 2011 and 2026.
    The event therefore brings its own measured mark: this week's NOAA OISST
    anomaly over the tropical Pacific as contours (+1, +2, +3 °C; dashed at
    -1), drawn in white so they do not add a second colour scale to a map that
    already has one, and the Niño-3.4 box the official index is taken from.
    The box mean of that field is checked against CPC's published weekly value
    at build time (ingest/enso.py) — this week +3.00 against +3.0.

  - The card is built from LIVE.enso, so it says what NOAA says and ages like
    everything else: alert status and synopsis quoted verbatim with their date,
    the weekly relative Niño-3.4 beside the traditional one, the official RONI
    since 1950 with its record, NOAA's stated probabilities verbatim, two camera
    moves, and six links, each checked to resolve on the day it was built.

  - The opening composition holds: the globe does not start its idle drift
    until the reader touches it, so it does not wander away from the event.

  - Phones: the right rail (the event, the extents, the stream) now comes
    straight after the map, before the layer stack.

Exact-string anchors, applied in order; each must match once or nothing is
written.

  python build/patch_feature_enso.py [--dry]     # patches dist/deck.html
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

CAM_LAT, CAM_LON = -18, -140          # opening camera: Niño-3.4 upper middle, Amundsen/Ross on the lower limb

CSS = r'''
/* ---------- the featured event ---------- */
.feat{padding:14px 16px 13px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,rgba(236,132,72,.085),rgba(236,132,72,0) 70%)}
.feat .fk{display:flex;align-items:center;gap:8px;font-family:var(--disp);font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--ink3)}
.feat .fk .tag{margin-left:auto;font-family:var(--disp);font-size:9px;letter-spacing:.14em;padding:1px 5px;border-radius:1px;background:rgba(236,132,72,.2);color:#F2C6A4}
.feat h3{font-family:var(--disp);font-size:25px;font-weight:600;letter-spacing:.07em;text-transform:uppercase;margin:3px 0 0;color:#F2C6A4;line-height:1.05}
.feat .syn{font-size:12px;line-height:1.5;color:var(--ink2);margin:7px 0 0}
.feat .cite{display:block;font-family:var(--mono);font-size:9px;letter-spacing:.02em;color:var(--ink4);margin-top:4px}
.feat .nums{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--line);border:1px solid var(--line);margin-top:11px}
.feat .nums>div{background:var(--panel);padding:8px 10px 9px;min-width:0}
.feat .nums .lab{font-family:var(--disp);font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink3)}
.feat .nums .v{font-family:var(--mono);font-size:23px;line-height:1.15;color:var(--ink);font-variant-numeric:tabular-nums}
.feat .nums .v small{font-size:11px;color:var(--ink3);margin-left:3px}
.feat .nums .sub{font-family:var(--mono);font-size:9px;line-height:1.45;color:var(--ink4);margin-top:2px}
.feat .chart{margin-top:10px}
.feat .chart canvas{display:block;width:100%;height:84px}
.feat .chart .cap{font-family:var(--mono);font-size:9px;color:var(--ink4);margin-top:3px;display:flex;justify-content:space-between;gap:8px}
.feat .out{font-size:11.5px;line-height:1.5;color:var(--ink2);margin-top:9px;border-left:2px solid rgba(236,132,72,.55);padding-left:8px}
.feat .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}
.feat .acts button{font-family:var(--disp);font-size:10px;letter-spacing:.13em;text-transform:uppercase;padding:5px 9px;border:1px solid var(--line2);border-radius:2px;color:var(--ink2)}
.feat .acts button:hover,.feat .acts button:focus-visible{border-color:var(--s1);color:var(--ice)}
.feat .lnk{display:grid;gap:4px;margin-top:11px;padding-top:9px;border-top:1px solid var(--line)}
.feat .lnk a{font-family:var(--mono);font-size:10px;line-height:1.35;color:var(--ink3);text-decoration:none}
.feat .lnk a:hover,.feat .lnk a:focus-visible{color:var(--ice)}
.feat .lnk a::after{content:" \2197";color:var(--ink4)}
.feat .pv{margin-top:9px}
.feat .pv .prov{white-space:normal;line-height:1.5}
'''

PANEL = '''<section class="col rrail">
      <div class="feat" id="feat" hidden></div>
      <div class="hero" id="heroMain">'''

LAYER = '''{id:"fronts",nm:"ACC fronts",               src:"Park & Durand · CNES-CLS18 mean dynamic topography", on:true, ex:"ocean_fronts"},
 {id:"enso", nm:"El Niño · SST anomaly this week", src:"NOAA OISST v2.1 · 7-day mean · tropical Pacific · contours", live:"enso", on:true, ex:"enso_contours"},'''

DRAW_CALL = '''  // ---- the featured event: this week's El Niño, as contours and the index box
  if(st.lay.enso) drawEnso(g,B,cx,cy,s);

  // ---- the living layer: aurora, SAR footprints, ice drift
  drawDeckLiveGlobe(g,B,cx,cy,s);'''

JS = r'''
/* ---------------- the featured event: El Niño ----------------
   Built from LIVE.enso (ingest/enso.py): NOAA CPC's status and words, the weekly
   relative Niño-3.4, the official RONI since 1950, and this week's OISST anomaly
   over the tropical Pacific. The field is drawn as contours, not colour: the
   currents are already coloured by temperature, and two colour scales for two
   different quantities on one map get read as one. */
const FEAT = {hold:true, fly:null};
function ensoData(){ return (typeof LIVE !== "undefined" && LIVE && LIVE.enso) ? LIVE.enso : null; }
const SEAS = {DJF:[12,2],JFM:[1,3],FMA:[2,4],MAM:[3,5],AMJ:[4,6],MJJ:[5,7],JJA:[6,8],JAS:[7,9],ASO:[8,10],SON:[9,11],OND:[10,12],NDJ:[11,1]};
const MSHORT = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function seasonName(code){
  const [s,y] = code.split(" "), Y=+y, m=SEAS[s]; if(!m) return code;
  if(s==="DJF") return "Dec "+(Y-1)+"–Feb "+Y;
  if(s==="NDJ") return "Nov "+Y+"–Jan "+(Y+1);
  return MSHORT[m[0]-1]+"–"+MSHORT[m[1]-1]+" "+Y;
}
function eventYears(code){
  // an ENSO event straddles the northern winter: name it by the two years it spans
  const [s,y]=code.split(" "), Y=+y, m=SEAS[s]; if(!m) return code;
  const mid=(m[0]%12)+1;                 // middle month of the three
  const a = s==="DJF" ? Y-1 : s==="NDJ" ? Y : (mid>=7 ? Y : Y-1);
  return a+"–"+String(a+1).slice(2);
}
function fmtDay(iso){ const d=new Date(iso+"T12:00:00Z"); return d.getUTCDate()+" "+MSHORT[d.getUTCMonth()]+" "+d.getUTCFullYear(); }
function esgn(v,dp){ return (v>0?"+":v<0?"−":"")+Math.abs(v).toFixed(dp); }

function featFly(lat,lon,ms){
  CAM.vlat=0; CAM.vlon=0; CAM.auto=false; CAM.zTarget=1;
  FEAT.hold=true;
  if(ocReduced()){ setCam(lat,lon); FEAT.fly=null; return; }
  FEAT.fly={la0:st.glat, lo0:st.glon, la1:lat, lo1:lon, t0:performance.now(), ms:ms||1500};
}

function feature(){
  const el=$("#feat"), E=ensoData();
  if(!el) return;
  if(!E || /Not Active/.test(E.status.alert)){ el.hidden=true; return; }
  const S=E.status, W=E.weekly, R=E.roni, F=E.field;
  const kind = S.alert.replace(/^Final /,"").replace(/ (Advisory|Watch)$/,"");
  const stage = (S.alert.match(/(Advisory|Watch)$/)||[""])[0];
  const title = stage==="Watch" ? kind+" — forming" : kind;
  const esc = t => String(t).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
  el.innerHTML =
    '<div class="fk" data-ex="featured_event">Featured event<span class="tag" data-ex="el_nino">NOAA · '+esc(S.alert)+'</span></div>'+
    '<h3 data-ex="el_nino">'+esc(title)+'</h3>'+
    '<p class="syn" data-ex="el_nino">“'+esc(S.synopsis)+'”'+
      '<span class="cite">NOAA Climate Prediction Center · '+fmtDay(S.issued)+(S.next?' · next '+fmtDay(S.next):'')+'</span></p>'+
    '<div class="nums">'+
      '<div data-ex="nino_relative"><div class="lab">Niño-3.4 · this week</div>'+
        '<div class="v">'+esgn(W.rel.nino34,1)+'<small>°C</small></div>'+
        '<div class="sub">relative · wk '+fmtDay(W.week).replace(/ \d{4}$/,"")+'<br>traditional '+esgn(W.trad34,1)+'</div></div>'+
      '<div data-ex="roni_history"><div class="lab">Official index · RONI</div>'+
        '<div class="v">'+esgn(R.latest,2)+'<small>°C</small></div>'+
        '<div class="sub">'+seasonName(R.last)+'<br>record '+esgn(R.peak.value,2)+', '+eventYears(R.peak.season)+'</div></div>'+
    '</div>'+
    '<div class="chart" data-ex="roni_history"><canvas id="featChart"></canvas>'+
      '<div class="cap"><span>'+seasonName(R.t0).split("–")[0].replace(/^Dec /,"")+'</span><span>every 3-month season, relative index</span><span>'+R.last.split(" ")[1]+'</span></div></div>'+
    (S.outlook && S.outlook.length ? '<div class="out" data-ex="el_nino">'+S.outlook.map(o=>'“'+esc(o)+'”').join(' ')+'</div>' : '')+
    '<div class="acts">'+
      '<button id="featGo" data-ex="enso_contours">Centre on the event</button>'+
      '<button id="featPole" data-ex="enso_antarctica">Follow it to Antarctica</button>'+
    '</div>'+
    '<div class="lnk">'+E.links.map(([n,u])=>'<a href="'+esc(u)+'" target="_blank" rel="noopener">'+esc(n)+'</a>').join('')+'</div>'+
    '<div class="pv"><span class="prov" data-ex="enso_contours"><b>OISST '+F.days[0].slice(6,8)+'–'+F.days[F.days.length-1].slice(6,8)+' '+MSHORT[+F.days[0].slice(4,6)-1]+
      ' · Niño-3.4 box '+esgn(F.n34_check,2)+' °C = CPC '+esgn(W.trad34,1)+'</b><span class="tag arch">MEAS</span></span></div>';
  el.hidden=false;
  $("#featGo").addEventListener("click",()=>{ if(st.mode!=="GLOBE") setMode("GLOBE"); featFly(CAM_HOME[0],CAM_HOME[1]); });
  $("#featPole").addEventListener("click",()=>{
    if(st.mode!=="GLOBE") setMode("GLOBE");
    if(!st.lay.ice){ st.lay.ice=true; layers(); }
    featFly(-58,-125);
  });
  featChart();
}

/* The official index since 1950. Warm above the line, cold below; the record
   and the latest value are marked; +2.5 °C is the value NOAA names as beyond any
   event on this record. The chart is drawn from the same array the card quotes. */
function featChart(){
  const E=ensoData(), cv=$("#featChart"); if(!E||!cv) return;
  const v=E.roni.v, n=v.length, dpr=Math.min(2,window.devicePixelRatio||1);
  const w=cv.clientWidth||300, h=cv.clientHeight||84;
  cv.width=Math.round(w*dpr); cv.height=Math.round(h*dpr);
  const g=cv.getContext("2d"); g.setTransform(dpr,0,0,dpr,0,0); g.clearRect(0,0,w,h);
  const lo=Math.min(-2.2,...v), hi=Math.max(2.8,...v), pt=6, pb=4;
  const X=i=>2+i/(n-1)*(w-4), Y=t=>pt+(hi-t)/(hi-lo)*(h-pt-pb), y0=Y(0);
  g.fillStyle="rgba(95,114,134,.10)"; g.fillRect(0,Y(0.5),w,Y(-0.5)-Y(0.5));
  const path=()=>{ g.beginPath(); g.moveTo(X(0),y0); for(let i=0;i<n;i++) g.lineTo(X(i),Y(v[i])); g.lineTo(X(n-1),y0); g.closePath(); };
  g.save(); g.beginPath(); g.rect(0,0,w,y0); g.clip(); path(); g.fillStyle="rgba(236,132,72,.62)"; g.fill(); g.restore();
  g.save(); g.beginPath(); g.rect(0,y0,w,h-y0); g.clip(); path(); g.fillStyle="rgba(92,164,224,.52)"; g.fill(); g.restore();
  g.strokeStyle="rgba(147,167,186,.45)"; g.lineWidth=1; g.beginPath(); g.moveTo(0,y0); g.lineTo(w,y0); g.stroke();
  g.setLineDash([3,3]); g.strokeStyle="rgba(242,198,164,.65)"; g.beginPath(); g.moveTo(0,Y(2.5)); g.lineTo(w,Y(2.5)); g.stroke(); g.setLineDash([]);
  g.font="9px 'IBM Plex Mono', monospace"; g.textBaseline="bottom";
  g.fillStyle="rgba(242,198,164,.8)"; g.textAlign="left"; g.fillText("+2.5 °C", 3, Y(2.5)-1);
  const ip=v.indexOf(E.roni.peak.value), il=n-1;
  for(const [i,lab,al] of [[ip, esgn(v[ip],2), "center"], [il, esgn(v[il],2), "right"]]){
    g.fillStyle="#F2C6A4"; g.beginPath(); g.arc(X(i),Y(v[i]),2.4,0,7); g.fill();
    g.fillStyle="rgba(221,232,241,.85)"; g.textAlign=al; g.fillText(lab, al==="right"?X(i)-4:X(i), Y(v[i])-3);
  }
}

/* this week's anomaly contours over the tropical Pacific, the index box, and
   the sea in Antarctica the event reaches — all on the near side only */
function drawEnso(g,B,cx,cy,s){
  const E=ensoData(); if(!E) return;
  const labels=[];
  g.lineJoin="round";
  for(const c of E.field.contours){
    const lv=c.level, warm=lv>0;
    g.strokeStyle = warm ? "rgba(255,248,240,"+(0.42+0.16*lv).toFixed(2)+")" : "rgba(176,210,238,.70)";
    g.lineWidth = warm ? 0.7+0.55*lv : 0.9;
    g.setLineDash(warm ? [] : [3,3]);
    g.beginPath();
    let best=null;
    for(const L of c.lines){
      gpathTo(g,L,B,cx,cy,s,true);
      if(!best || L.length>best.length) best=L;
    }
    g.stroke();
    // each warm level is labelled at the western tip of its tongue, where the
    // nested contours are furthest apart; longitudes run 120..290 east, unwrapped
    if(best && warm){
      let bi=-1, bl=1e9;
      for(let i=0;i<best.length;i+=2){ if(Math.abs(best[i+1])<8 && best[i]<bl){ bl=best[i]; bi=i; } }
      if(bi>=0){ const q=gproj(best[bi],best[bi+1],B);
        if(q[2]>0.15) labels.push({px:cx+q[0]*s-4, py:cy-q[1]*s+3, t:"+"+lv+"°C", col:"rgba(255,248,240,.95)", dy:0, al:"right"}); }
    }
  }
  g.setLineDash([]);
  const bx=E.box, ring=[];
  for(let lon=bx.lon[0];lon<=bx.lon[1];lon+=2) ring.push(lon,bx.lat[1]);
  for(let lon=bx.lon[1];lon>=bx.lon[0];lon-=2) ring.push(lon,bx.lat[0]);
  ring.push(bx.lon[0],bx.lat[1]);
  g.strokeStyle="rgba(127,227,245,.95)"; g.lineWidth=1.3; g.setLineDash([6,4]);
  g.beginPath(); gpathTo(g,ring,B,cx,cy,s,true); g.stroke(); g.setLineDash([]);
  const qb=gproj(bx.lon[0],bx.lat[1]+1.5,B);
  if(qb[2]>0.1){
    const px=cx+qb[0]*s, py=cy-qb[1]*s;
    labels.push({px:px, py, t:"NIÑO-3.4 · "+esgn(E.weekly.rel.nino34,1)+"°C RELATIVE", col:"rgba(127,227,245,.98)", dy:-6, al:"left"});
    HOT.push({x:px+50,y:py-10,r:30,ex:"el_nino"});
  }
  const qa=gproj(-112,-71,B);
  if(qa[2]>0.1){
    const px=cx+qa[0]*s, py=cy-qa[1]*s;
    labels.push({px, py, t:"AMUNDSEN SEA", col:"rgba(242,198,164,.92)", dy:0});
    HOT.push({x:px,y:py-4,r:26,ex:"enso_antarctica"});
  }
  g.font="600 10px 'Saira Condensed', sans-serif";
  for(const L of labels){
    const y=L.py+L.dy; g.textAlign=L.al||"center";
    g.lineWidth=2.6; g.strokeStyle="rgba(4,8,13,.9)"; g.strokeText(L.t,L.px,y);
    g.fillStyle=L.col; g.fillText(L.t,L.px,y);
  }
}
'''

EXPL = r'''featured_event:{k:"ins",t:"The featured event",
 b:"One thing happening in the climate system right now, chosen because it is large, measured and connected to the poles, and shown with the numbers of the agency that monitors it, in their words. The card is rebuilt from source with the rest of the living layer, and it states the date of everything on it. When the event ends, the card says so instead of going quiet.",
 p:"Built by ingest/enso.py from NOAA CPC and NOAA OISST v2.1 at build time."},
el_nino:{k:"mech",t:"El Niño",
 b:"Most years the trade winds push the sun-warmed surface of the Pacific west, piling it up against Indonesia, while cold water wells up off Peru to replace it. Every few years the winds slacken, the warm pool slides back east along the equator and the upwelling is capped: the water off South America stops being cold. The rain follows the warm water from Indonesia into the central Pacific, and the atmosphere carries the change around the world. It is the largest year-to-year swing in the climate system. The dashed box is <b>Niño-3.4</b>, the stretch of equator the official index is measured in.",
 p:"Coupled through the Bjerknes feedback between equatorial winds and the east–west temperature gradient. Niño-3.4: 5°N–5°S, 170°–120°W. Status and outlook: NOAA CPC ENSO diagnostic discussion, monthly."},
nino_relative:{k:"num",t:"Why the index is relative",
 b:"The whole tropical ocean has warmed, so a Pacific anomaly measured against 1991–2020 now reads high even when the Pacific is doing nothing unusual. Since February 2026 NOAA's official index subtracts the average anomaly of the whole tropics, 20°N to 20°S, from the Niño-3.4 anomaly, and rescales the difference so its swings match the old index. What remains is the Pacific departing from the rest of the tropics, which is what El Niño is. The two can now differ by most of a degree, so the card shows both.",
 p:"NOAA CPC Relative Oceanic Niño Index (RONI): 3-month ERSSTv5 Niño-3.4 anomaly minus the 20°N–20°S mean, variance-matched to Niño-3.4, 1991–2020 base; El Niño above +0.5 °C. Weekly relative and traditional indices from OISST v2.1."},
roni_history:{k:"num",t:"Seventy-six years on one line",
 b:"Every three-month season since 1950 on the official index. Warm spikes above the line are El Niño, cold troughs La Niña, and the grey band is the ±0.5 °C inside which neither is declared. The three great El Niños on this record, 1982–83, 1997–98 and 2015–16, peaked between +2.25 and +2.40 °C. The dashed line at +2.5 °C is the value NOAA names as stronger than any event on the record.",
 p:"NOAA CPC RONI.ascii.txt, DJF 1950 onward. Peaks computed from the file at build time."},
enso_contours:{k:"obj",t:"The white lines",
 b:"This week's sea-surface temperature against its 1991–2020 average for the same days, from satellites, ships and buoys, averaged over seven days and drawn across the tropical Pacific as contours a degree apart: thin at +1 °C, heavier at +2, heaviest at +3, dashed where the sea is a degree colder than normal. They are lines, not colour, because the currents are already coloured by temperature — and the Temp colouring is a forty-year average that cannot show El Niño at all: it paints everything above 22 °C the same orange. Before the page is built, the mean inside the Niño-3.4 box is checked against NOAA's published weekly value for the same week.",
 p:"NOAA OISST v2.1 daily anomaly, 0.25°, 7-day mean centred on CPC's latest weekly index, 1° block mean, 3×3 smoothing; 20°S–20°N, 120°E–70°W. Traditional anomaly, not relative."},
enso_antarctica:{k:"mech",t:"How El Niño reaches Antarctica",
 b:"Heat released into the tropical atmosphere sets off a train of high- and low-pressure waves that arcs south-east across the Pacific, the Pacific–South American pattern, and ends over the Amundsen Sea, where it weakens the Amundsen Sea Low. The winds around that low decide where Antarctic sea ice gathers. In El Niño years cold southerlies tend to push more ice into the Bellingshausen Sea while warm northerlies thin it in the Ross Sea: a dipole, not one signal. How hard it lands depends on the Southern Annular Mode, the ring of westerlies round the continent, which can amplify it or cancel it.",
 p:"Wang, Luo, Yu, Li, Holland & Yang (2023), The impacts of combined SAM and ENSO on seasonal Antarctic sea ice changes, Journal of Climate 36."},
enso_heat:{k:"mech",t:"Why El Niño years are hot years",
 b:"El Niño does not add heat to the planet; it moves it. Warm water that normally stays pooled beneath the western Pacific spreads across the surface of the eastern Pacific and gives its heat up to the air. Global surface temperature follows the Niño-3.4 index a few months later, which is why the record years 1998, 2016 and 2024 each came at the end of a strong El Niño, stacked on top of the long-term warming underneath.",
 p:"ENSO's imprint on global temperature, lagging by a few months: Foster & Rahmstorf (2011), Environmental Research Letters 6, 044022."},
channel_empty:{k:"ins",t:"Why this space is empty",'''

EDITS = [
("opening mode: the globe",
 'const st={ S:true, mode:"S",', 'const st={ S:true, mode:"GLOBE",', 1),
("opening camera: the equatorial Pacific, tilted south",
 'learn:true, glat:-60, glon:-30,', f'learn:true, glat:{CAM_LAT}, glon:{CAM_LON},', 1),
("opening colouring: Temp, season on",
 'baseImg:"relief", driftX:1, flowCol:"speed", flowSeason:true };',
 'baseImg:"relief", driftX:1, flowCol:"temp", flowSeason:true };\n'
 f'const CAM_HOME=[{CAM_LAT},{CAM_LON}];   // where the featured event is framed', 1),
("mode buttons agree at first paint",
 '<button data-mode="S" aria-pressed="true">Antarctic</button>',
 '<button data-mode="S" aria-pressed="false">Antarctic</button>', 1),
("globe button pressed",
 '<button data-mode="GLOBE" aria-pressed="false" data-ex="mode_globe">Globe</button>',
 '<button data-mode="GLOBE" aria-pressed="true" data-ex="mode_globe">Globe</button>', 1),
("colour buttons agree at first paint: speed",
 '<button data-fc="speed" aria-pressed="true"  data-ex="ocean_flow">Speed</button>',
 '<button data-fc="speed" aria-pressed="false" data-ex="ocean_flow">Speed</button>', 1),
("colour buttons agree at first paint: temp",
 '<button data-fc="temp"  aria-pressed="false" data-ex="ocean_temp">Temp</button>',
 '<button data-fc="temp"  aria-pressed="true"  data-ex="ocean_temp">Temp</button>', 1),
("the card, at the top of the right rail",
 '<section class="col rrail">\n      <div class="hero" id="heroMain">', PANEL, 1),
("the card's styles",
 '.dispatch{padding:13px 16px 15px;', CSS.strip() + '\n.dispatch{padding:13px 16px 15px;', 1),
("phones: the event and the extents come straight after the map",
 '.body .col:nth-child(1){order:2}.body .col:nth-child(2){order:1}.body .col:nth-child(3){order:3}',
 '.body .col:nth-child(1){order:3}.body .col:nth-child(2){order:1}.body .col:nth-child(3){order:2}', 1),
("the event's layer",
 '{id:"fronts",nm:"ACC fronts",               src:"Park & Durand · CNES-CLS18 mean dynamic topography", on:true, ex:"ocean_fronts"},',
 LAYER, 1),
("drawn on the globe, above the currents, under the living layer",
 '  // ---- the living layer: aurora, SAR footprints, ice drift\n  drawDeckLiveGlobe(g,B,cx,cy,s);', DRAW_CALL, 1),
("the camera flies to the event and back",
 '  if(st.mode!=="GLOBE") return;\n  // zoom eases toward its target so a wheel notch is not a jump',
 '''  if(st.mode!=="GLOBE") return;
  if(FEAT.fly){
    const f=FEAT.fly, t=Math.min(1,(performance.now()-f.t0)/f.ms);
    const e=t<.5 ? 2*t*t : 1-Math.pow(-2*t+2,2)/2;
    const dl=((f.lo1-f.lo0+540)%360)-180;
    setCam(f.la0+(f.la1-f.la0)*e, f.lo0+dl*e);
    if(t>=1) FEAT.fly=null;
    return;
  }
  // zoom eases toward its target so a wheel notch is not a jump''', 1),
("the opening composition holds until the reader touches the globe",
 '  if(!CAM.auto && performance.now()-CAM.idle > CAM_IDLE_MS) CAM.auto=true;',
 '  if(!CAM.auto && !FEAT.hold && performance.now()-CAM.idle > CAM_IDLE_MS) CAM.auto=true;', 1),
("touching the globe releases the hold",
 'function camTouch(){ CAM.idle=performance.now(); CAM.auto=false; }',
 'function camTouch(){ CAM.idle=performance.now(); CAM.auto=false; FEAT.hold=false; FEAT.fly=null; }', 1),
("freshness follows each source's own cadence",
 'function liveFresh(iso){\n  const t = Date.parse(iso||""); if(!isFinite(t)) return "stale";\n  const h = (Date.now()-t)/3.6e6;\n  return h < 48 ? "live" : h < 168 ? "warn" : "stale";\n}',
 '''function liveFresh(iso, cadH){
  // a weekly index a week old is current; an hourly feed a week old is not.
  // Green inside two cadences, amber inside seven, grey after that.
  const c = cadH || 24;
  const t = Date.parse(iso||""); if(!isFinite(t)) return "stale";
  const h = (Date.now()-t)/3.6e6;
  return h < 2*c ? "live" : h < 7*c ? "warn" : "stale";
}''', 1),
("a header chip for the event",
 '  F.push(["RAPID 26.5°N","2004–2024","arch","rapid"]);',
 '''  if(A.enso)   F.push(["Niño-3.4 weekly", liveAge(A.enso.time), liveFresh(A.enso.time, A.enso.cadence_h||168), "nino_relative"]);
  F.push(["RAPID 26.5°N","2004–2024","arch","rapid"]);''', 1),
("the event's code",
 'const CAM_IDLE_MS=14000;', JS.strip() + '\nconst CAM_IDLE_MS=14000;', 1),
("the event's explainers",
 'channel_empty:{k:"ins",t:"Why this space is empty",', EXPL.strip(), 1),
("built at boot, redrawn on resize",
 'feeds(); layers(); stations(); events(); modeUI(); exIndex();',
 'feeds(); layers(); stations(); events(); modeUI(); feature(); exIndex();\n'
 'try{ new ResizeObserver(()=>{ try{ featChart(); }catch(e){} }).observe($("#feat")); }catch(e){}', 1),
]

GUARD_ABSENT = ['mode:"S", t:0', 'glat:-60, glon:-30']
GUARD_PRESENT = ['mode:"GLOBE"', 'flowCol:"temp"', 'function drawEnso(', 'id="feat"', 'el_nino:{k:"mech"']


def main():
    dry = "--dry" in sys.argv
    path = os.path.join(ROOT, "dist", "deck.html")
    src = open(path, encoding="utf-8", newline="").read()
    out = src
    for name, old, new, want in EDITS:
        n = out.count(old)
        if n != want:
            raise SystemExit(f"ABORT — '{name}': anchor matched {n} times, need {want}")
        out = out.replace(old, new, want)
        print(f"  ok  {name}")
    bad = [g for g in GUARD_ABSENT if g in out] + [g for g in GUARD_PRESENT if g not in out]
    if bad:
        raise SystemExit(f"ABORT — guard: {bad}")
    print(f"      {len(src)/1e6:.3f} MB -> {len(out)/1e6:.3f} MB")
    if dry:
        print("dry run — nothing written")
        return
    open(path, "w", encoding="utf-8", newline="").write(out)
    print("written dist/deck.html")


if __name__ == "__main__":
    main()
