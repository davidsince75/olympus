# -*- coding: utf-8 -*-
"""Popup, index, LEARN switch and the anchored map callouts."""
import io, sys
SRC = "/home/claude/olympus/src/atlas.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# state
once(u'st.driftX = 1;          // vector length multiplier, always stated on screen',
     u'st.learn = false;       // the learning layer is off until asked for\nst.driftX = 1;          // vector length multiplier, always stated on screen',
     "st.learn")

MACH = u'''
/* ---- the callouts: anchored on the map, drawn only when LEARN is on ---- */
const ANNOT = [
  {ex:"finding_dml",        S:true,  at:[11.63,-70.83], t:"Two runways"},
  {ex:"finding_fildes",     S:true,  at:[-58.96,-62.20], t:"Fildes"},
  {ex:"finding_union",      S:true,  at:[-82.87,-79.77], t:"Union Glacier"},
  {ex:"finding_terranova",  S:true,  at:[163.72,-74.93], t:"Terra Nova Bay"},
  {ex:"finding_russia",     S:true,  at:[76.38,-68.58],  t:"Russia"},
  {ex:"finding_nyalesund",  S:false, at:[11.93,78.92],   t:"Ny-\\u00c5lesund"}
];

function drawAnnot(d){
  if(!st.learn) return;
  for(let i=0;i<ANNOT.length;i++){
    const a = ANNOT[i];
    if(a.S !== d.S) continue;
    const p = place(a.at[1], a.at[0]);
    if(!p || p.d !== d) continue;
    const x = p.x, y = p.y;
    g.save();
    g.strokeStyle = "rgba(127,227,245,.85)"; g.lineWidth = 1.1;
    g.setLineDash([3,3]);
    g.beginPath(); g.arc(x, y, 13, 0, 7); g.stroke();
    g.setLineDash([]);
    g.fillStyle = "rgba(6,9,14,.88)";
    g.beginPath(); g.arc(x, y, 8, 0, 7); g.fill();
    g.strokeStyle = "rgba(127,227,245,.95)"; g.lineWidth = 1;
    g.beginPath(); g.arc(x, y, 8, 0, 7); g.stroke();
    g.fillStyle = "#7FE3F5";
    g.font = "600 10px 'Saira Condensed', sans-serif";
    g.textAlign = "center"; g.textBaseline = "middle";
    g.fillText(String(i+1), x, y+0.5);
    // label, offset so it does not sit on the station it is about
    g.font = "600 9.5px 'Saira Condensed', sans-serif";
    g.textAlign = "left"; g.textBaseline = "alphabetic";
    const tw = g.measureText(a.t.toUpperCase()).width;
    g.fillStyle = "rgba(6,9,14,.80)";
    g.fillRect(x+15, y-13, tw+8, 14);
    g.fillStyle = "#7FE3F5";
    g.fillText(a.t.toUpperCase(), x+19, y-3);
    g.restore();
    HOT.push({x, y, r:15, ex:a.ex});
  }
}

/* ---- the popup ---- */
const exBox = document.createElement("div");
exBox.className = "exbox"; exBox.setAttribute("role","tooltip"); exBox.hidden = true;
document.body.appendChild(exBox);
let exId = null;
function showEx(id, px, py){
  if(!st.learn){ hideEx(); return; }
  const e = EXPL[id]; if(!e){ hideEx(); return; }
  if(exId !== id){
    exId = id;
    exBox.innerHTML = `<div class="exh"><span class="exk k-${e.k}">${EXKIND[e.k]}</span><b>${e.t}</b></div>` +
                      `<div class="exb">${e.b}</div><div class="exp">${e.p}</div>`;
  }
  exBox.hidden = false;
  const w = exBox.offsetWidth, h = exBox.offsetHeight;
  let x = px + 16, y = py + 16;
  if(x + w > innerWidth - 8)  x = px - w - 16;
  if(y + h > innerHeight - 8) y = Math.max(8, py - h - 16);
  exBox.style.left = Math.max(8, x) + "px";
  exBox.style.top  = Math.max(8, y) + "px";
}
function hideEx(){ if(!exBox.hidden){ exBox.hidden = true; exId = null; } }

document.addEventListener("pointerover", e=>{
  const t = e.target.closest?.("[data-ex]");
  if(t) showEx(t.dataset.ex, e.clientX, e.clientY);
});
document.addEventListener("pointermove", e=>{
  const t = e.target.closest?.("[data-ex]");
  if(t && exId === t.dataset.ex) showEx(t.dataset.ex, e.clientX, e.clientY);
});
document.addEventListener("pointerout", e=>{
  const t = e.target.closest?.("[data-ex]");
  if(t && !t.contains(e.relatedTarget)) hideEx();
});
document.addEventListener("focusin", e=>{
  const t = e.target.closest?.("[data-ex]");
  if(t){ const r = t.getBoundingClientRect(); showEx(t.dataset.ex, r.right, r.top); }
});
document.addEventListener("focusout", e=>{ if(e.target.closest?.("[data-ex]")) hideEx(); });
document.addEventListener("keydown", e=>{ if(e.key === "Escape") hideEx(); });

/* ---- the index: every entry reachable by name, not by luck ---- */
function exIndex(){
  const head = $("#exIndexHead"), box = $("#exIndex");
  if(!head || !box) return;
  head.hidden = !st.learn; box.hidden = !st.learn;
  if(!st.learn){ box.innerHTML = ""; return; }
  const order = ["mech","obj","ins","num"];
  const by = {}; order.forEach(k => by[k] = []);
  for(const [id, e] of Object.entries(EXPL)) (by[e.k] || (by[e.k] = [])).push([id, e.t]);
  box.innerHTML = order.map(k => {
    const rows = by[k] || [];
    if(!rows.length) return "";
    return `<div class="grp">${EXKIND[k]}</div>` + rows.map(([id, t]) =>
      `<button type="button" data-ex="${id}">${t}</button>`).join("");
  }).join("");
  $("#exCount").textContent = Object.keys(EXPL).length;
}

$("#learnBtn").addEventListener("click", ()=>{
  st.learn = !st.learn;
  $("#learnBtn").setAttribute("aria-pressed", String(st.learn));
  document.body.classList.toggle("learning", st.learn);
  if(!st.learn) hideEx();
  exIndex(); draw();
});
'''
once(u'$("#q").addEventListener("input", e=>{ st.q = e.target.value.trim();',
     MACH + u'\n$("#q").addEventListener("input", e=>{ st.q = e.target.value.trim();',
     "machinery")

# draw the callouts last, over the network
once(u'''function hit(mx,my){''',
     u'''function hit(mx,my){''', "anchor check")
io.open(SRC, "w", encoding="utf8").write(s)
print("machinery written")
