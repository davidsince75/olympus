# -*- coding: utf-8 -*-
"""
Retire the deck's SIM anomaly stream.

The panel was six hardcoded objects with hardcoded ages ("14 min", forever).
It is replaced by a stream derived from the record the page already carries:
OSI SAF measured monthly extent against the 1991-2020 mean for the same calendar
month, from the same record. Nothing is fetched and nothing is invented.

Run from the repo root:  python build/deck_anomaly.py
"""
import io, os, sys, re

SRC = "src/deck.html"
DIST = "dist/deck.html"

s = io.open(SRC, encoding="utf-8").read()
n0 = len(s)

def cut(text, a, b, label):
    """replace exactly one occurrence of a with b, or fail loudly"""
    if text.count(a) != 1:
        sys.exit("PATCH FAILED (%s): expected 1 occurrence, found %d" % (label, text.count(a)))
    return text.replace(a, b)

# ---------------------------------------------------------------- 1. the fake data
OLD_EVENTS_HEAD = 'const EVENTS=[\n {s:"crit",t:"Rift propagation"'
i = s.find(OLD_EVENTS_HEAD)
if i < 0:
    sys.exit("PATCH FAILED (EVENTS): array not found")
j = s.find("\n];", i) + 3
s = s[:i] + s[j:]

# ---------------------------------------------------------------- 2. the renderer
OLD_FN = '''function events(){
  $("#stream").innerHTML=EVENTS.map(e=>
    `<div class="evt ${e.s}"><div class="bar"></div><div>
       <div class="hd"><span class="ttl">${e.t}</span><span class="ago">${e.a}</span></div>
       <div class="ds">${e.d}</div><div class="mt">${e.m}</div></div></div>`).join("");
  $("#evtn").textContent=EVENTS.length+" open";
}'''

NEW_FN = r'''/* ---------------- anomaly stream · derived, not invented ----------------
   Every card below is computed in the browser from the record this page already
   carries: OSI.hemi[h].ext is the measured monthly extent, integrated on the EASE2
   source grid at the 15% threshold; OSI.hemi[h].clim is the mean of that same
   calendar month over 1991-2020, taken from the same record so the comparison is
   internally consistent. Nothing here is fetched, and nothing here is drawn.
   The stream follows the time slider: it describes the month on screen. */

let ANOM=null;
function anomStats(){
  if(ANOM) return ANOM;
  const SD={}, BY={}, SPAN={};
  for(const h of ["sh","nh"]){
    const H=OSI.hemi[h];
    const by=[], clim=[];
    for(let m=0;m<12;m++){ by.push([]); clim.push([]); }
    let y0=1e9, y1=-1e9;
    for(let k=0;k<H.n;k++){
      const t=YM0+H.ymo[k], y=Math.floor(t/12), m=t%12;
      by[m].push([y, H.ext[k], k]);
      if(y<y0) y0=y; if(y>y1) y1=y;
      if(y>=1991 && y<=2020) clim[m].push(H.ext[k]);   // the stated baseline period
    }
    SD[h]=clim.map(v=>{
      if(v.length<2) return 0;
      const mu=v.reduce((a,b)=>a+b,0)/v.length;
      return Math.sqrt(v.reduce((a,b)=>a+(b-mu)*(b-mu),0)/(v.length-1));
    });
    BY[h]=by; SPAN[h]=[y0,y1];
  }
  ANOM={SD:SD, byMonth:BY, span:SPAN};
  return ANOM;
}

function ordinal(n){
  const t=n%100; if(t>=11&&t<=13) return n+"th";
  return n + (["th","st","nd","rd"][n%10] || "th");
}
function sgn(v,d){ return (v>=0?"+":"−") + Math.abs(v).toFixed(d); }

// the frame this hemisphere is showing, honouring the record's real gaps
function frameFor(h){
  return (h===hemiKey()) ? monIdx() : frameAt(h, OSI.hemi[hemiKey()].ymo[monIdx()]);
}

function anomCards(h){
  const S=anomStats(), H=OSI.hemi[h], k=frameFor(h);
  const t=YM0+H.ymo[k], yy=Math.floor(t/12), mm=t%12;
  const v=H.ext[k], c=H.clim[mm], sd=S.SD[h][mm];
  const dv=v-c, pct=dv/c*100, z=sd>0?dv/sd:0;
  const hemi = (h==="sh") ? "Antarctic" : "Arctic";
  const when = MON[mm].toUpperCase()+" "+yy;
  const r=recFor(h,k), ft=!!r[3];
  const prod = "OSI SAF " + r[1];
  const src = prod + " · EASE2 25 km · ≥15%";
  const tag = ft ? ["ft","FT"] : ["arch","MEAS"];
  const out=[];

  // 1 — the departure itself, graded against the spread of the same calendar month
  out.push({
    s: z<=-2 ? "crit" : (z<=-1 || z>=2) ? "warn" : "info",
    t: hemi+" extent anomaly",
    d: v.toFixed(2)+" against a 1991–2020 "+MON[mm]+" mean of "+c.toFixed(2)+
       " ×10⁶ km² — "+sgn(dv,2)+" ("+sgn(pct,1)+"%)"+
       (sd>0 ? ", which is "+Math.abs(z).toFixed(1)+"σ "+(dv>=0?"above":"below")+
               " that mean measured against the spread of "+MON[mm]+" over the same thirty years." : "."),
    m: src, a: when, tag: tag });

  // 2 — rank, counting only observations of the same calendar month
  const ser=S.byMonth[h][mm].slice().sort((a,b)=>a[1]-b[1]);
  const n=ser.length, pos=ser.findIndex(q=>q[2]===k)+1;
  if(pos>0){
    const lowR=pos, hiR=n-pos+1, low=lowR<=hiR, rk=low?lowR:hiR;
    out.push({
      s: rk<=3 ? (low?"crit":"warn") : rk<=10 ? "warn" : "info",
      t: "Rank on the record",
      d: ordinal(rk)+" "+(low?"lowest":"highest")+" "+MON[mm]+" of the "+n+
         " in the record. Lowest "+ser[0][1].toFixed(2)+" ("+ser[0][0]+
         "), highest "+ser[n-1][1].toFixed(2)+" ("+ser[n-1][0]+").",
      m: n+" "+MON[mm]+" observations · "+S.span[h][0]+"–"+S.span[h][1],
      a: when, tag: ["arch","DERIVED"] });
  }

  // 3 — how long the record has been on the same side of its own mean
  const below = dv<0;
  let run=0;
  for(let q=k;q>=0;q--){
    const mq=(YM0+H.ymo[q])%12;
    if((H.ext[q] < H.clim[mq]) === below) run++; else break;
  }
  if(run>=2){
    const i0=k-run+1, t0=YM0+H.ymo[i0];
    // the record has real gaps; a run of frames is only a run of months if none fall inside it
    const solid = (H.ymo[k]-H.ymo[i0]+1)===run;
    out.push({
      s: run>=24 ? "crit" : run>=12 ? "warn" : "info",
      t: below ? "Consecutive months below the mean" : "Consecutive months above the mean",
      d: run+(solid?" months in a row ":" consecutive observations ")+(below?"below":"above")+
         " the 1991–2020 mean for their own calendar month, beginning "+
         MON[t0%12]+" "+Math.floor(t0/12)+".",
      m: solid ? "unbroken run of monthly observations"
               : "consecutive observations · the record has gaps inside this span, skipped not bridged",
      a: when, tag: ["arch","DERIVED"] });
  }

  // 4 — the same month one year earlier, if the record actually has it
  const pk=frameAt(h, H.ymo[k]-12);
  if(H.ymo[pk]===H.ymo[k]-12){
    const pv=H.ext[pk], d1=v-pv, p1=d1/pv*100;
    const flat = Math.abs(p1) < 0.5;
    out.push({
      s: Math.abs(p1)>=10 ? "warn" : "info",
      t: flat ? "Year on year · level" : "Year on year",
      d: flat
        ? "Level with "+MON[mm]+" "+(yy-1)+" ("+pv.toFixed(2)+" → "+v.toFixed(2)+
          " ×10⁶ km², "+sgn(d1,3)+"). A flat year against a depressed baseline is not a recovery."
        : sgn(d1,2)+" ×10⁶ km² on "+MON[mm]+" "+(yy-1)+
          " ("+pv.toFixed(2)+" → "+v.toFixed(2)+"), "+sgn(p1,1)+"%.",
      m: "same calendar month, consecutive years",
      a: when, tag: ["arch","DERIVED"] });
  }

  // 5 — which product this month comes from, and whether it can still be revised
  out.push({
    s: ft ? "warn" : "info",
    t: ft ? "Provisional product" : "Product in use",
    d: ft ? "This month comes from the interim fast-track stream, not the reprocessed "+
            "climate data record. It is the most recent data available and it can be "+
            "revised when the reprocessed record catches up."
          : "This month comes from "+prod+". Extent is integrated on the source grid "+
            "from the same cells that are drawn, at the 15% concentration threshold.",
    m: prod, a: when, tag: tag });

  return out;
}

let evtKey="";
function events(force){
  const hs = activeHemis();
  const key = hs.join("+")+":"+monIdx();
  if(!force && key===evtKey) return;          // don't rebuild while the slider is dragged
  evtKey = key;
  const cards = hs.reduce((a,h)=>a.concat(anomCards(h)), []);
  $("#stream").innerHTML = cards.map(e=>
    `<div class="evt ${e.s}" data-ex="anom_stream" tabindex="0"><div class="bar"></div><div>
       <div class="hd"><span class="ttl">${e.t}</span><span class="ago">${e.a}</span></div>
       <div class="ds">${e.d}</div>
       <div class="mt">${e.m} <span class="tag ${e.tag[0]}">${e.tag[1]}</span></div>
     </div></div>`).join("");
  $("#evtn").textContent = cards.length + " derived";
}'''

s = cut(s, OLD_FN, NEW_FN, "events()")

# ---------------------------------------------------------------- 3. the panel header
OLD_PH = ('<div class="ph"><h2>Anomaly stream</h2>'
          '<span class="prov" style="margin-right:8px" data-ex="sim_layer">'
          '<span class="tag sim">SIM</span></span><span class="n" id="evtn"></span></div>')
NEW_PH = ('<div class="ph"><h2>Anomaly stream</h2>'
          '<span class="prov" style="margin-right:8px" data-ex="anom_stream">'
          '<b>Derived</b>'
          '<span class="tag arch">MEAS</span></span><span class="n" id="evtn"></span></div>')
s = cut(s, OLD_PH, NEW_PH, "panel header")

# ---------------------------------------------------------------- 4. follow the slider
OLD_SYNC_TAIL = ('           : "EASE2 25 km → POLAR STEREOGRAPHIC DISC · TRUE AT 45°N";\n}')
NEW_SYNC_TAIL = ('           : "EASE2 25 km → POLAR STEREOGRAPHIC DISC · TRUE AT 45°N";\n\n'
                 '  // the stream describes the month on screen, so it moves with it\n'
                 '  try{ events(); }catch(e){}\n}')
s = cut(s, OLD_SYNC_TAIL, NEW_SYNC_TAIL, "sync tail")

# ---------------------------------------------------------------- 5. the honesty ledger
OLD_SIM = ('b:"ITS_LIVE velocity streaklines, Argo float positions, the satellite ground track '
           'and the anomaly stream are <b>drawn, not measured</b>. They show what the finished '
           'instrument would carry. They are marked SIM everywhere they appear, and no number on '
           'the deck is derived from them. Sentinel-1 used to be on this list and is not any more: '
           'those footprints are now real acquisitions, which is the only kind of progress this '
           'list is meant to record.",')
NEW_SIM = ('b:"ITS_LIVE velocity streaklines, Argo float positions and the satellite ground track '
           'are <b>drawn, not measured</b>. They show what the finished instrument would carry. '
           'They are marked SIM everywhere they appear, and no number on the deck is derived from '
           'them. Sentinel-1 and the anomaly stream used to be on this list and are not any more: '
           'the footprints are real acquisitions, and the stream is now computed from the measured '
           'record. That is the only kind of progress this list is meant to record.",')
s = cut(s, OLD_SIM, NEW_SIM, "sim_layer explainer")

OLD_FOOT = ('ITS_LIVE, Argo, the ground track and the anomaly stream remain illustrative and are marked')
NEW_FOOT = ('ITS_LIVE, Argo and the ground track remain illustrative and are marked')
s = cut(s, OLD_FOOT, NEW_FOOT, "footer note")

# ---------------------------------------------------------------- 6. a new explainer
ANCHOR = 'sim_layer:{k:"ins",t:"This layer is illustrative",'
NEW_EX = r'''anom_stream:{k:"num",t:"How the anomaly stream is computed",
 b:"Every card in the stream is computed in your browser from the record already on this page. The extent is the measured OSI SAF value for the month on screen, integrated on the EASE2 source grid at the 15% threshold. The baseline is the mean of that <b>same calendar month over 1991-2020</b>, taken from this same record so the comparison is internally consistent — a September is only ever compared with other Septembers. σ is the standard deviation of that calendar month over the same thirty years, which is what allows a departure to be graded rather than guessed at. Ranks count only observations of the same calendar month, and the record's real gaps (April–June 1986, December 1987) are skipped rather than bridged. <b>Nothing in this panel is fetched and nothing is invented.</b> It describes the month you are looking at, and it moves when you move the slider.",
 p:"Derived in the browser from the OSI SAF monthly record carried by this page. No network."},

'''
s = cut(s, ANCHOR, NEW_EX + ANCHOR, "anom_stream explainer")

# ---------------------------------------------------------------- write
io.open(SRC, "w", encoding="utf-8", newline="").write(s)
io.open(DIST, "w", encoding="utf-8", newline="").write(s)
print("src/deck.html %d -> %d bytes (%+d)" % (n0, len(s), len(s)-n0))
print("dist/deck.html written")
