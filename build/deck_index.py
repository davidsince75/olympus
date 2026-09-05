# -*- coding: utf-8 -*-
"""Thirteen explainers had been written and had no hover target anywhere on the
page — invisible content. Rather than invent thirteen places to hover, give the
layer an index: with LEARN on, every entry is listed by name in the left rail,
grouped the way the popups are already coded. Also make the popup reachable by
keyboard, and hang the obvious chrome targets where they belong."""
import io, sys
SRC = "/home/claude/olympus/src/deck.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# ---------------------------------------------------------------- chrome targets
once(u'<span><i style="background:#2E4152"></i>Grounded ice</span>',
     u'<span data-ex="grounding"><i style="background:#2E4152"></i>Grounded ice</span>', "key grounded -> grounding")
once(u'<span><i style="background:#0FA5BE"></i>Ice shelf</span>',
     u'<span data-ex="shelf"><i style="background:#0FA5BE"></i>Ice shelf</span>', "key shelf -> shelf")
once(u'<span><i style="background:#C8802F;border-radius:50%"></i>Station</span>',
     u'<span data-ex="stn_deck"><i style="background:#C8802F;border-radius:50%"></i>Station</span>', "key station -> stn_deck")
once(u'<div style="color:var(--ink4)">drag the trace to travel · 570 monthly composites</div>',
     u'<div style="color:var(--ink4)">drag the trace to travel · <span data-ex="monthly">570 monthly composites</span></div>', "570 composites -> monthly")
once(u'<div class="readout" id="proj">—</div>',
     u'<div class="readout" id="proj" data-ex="reprojection">—</div>', "proj readout -> reprojection")

# ---------------------------------------------------------------- the index
once(u'''      <div class="ph"><h2>Station network</h2><span class="n" id="stncount"></span></div>''',
     u'''      <div class="ph" id="exIndexHead"><h2>Explainers</h2><span class="n" id="exCount"></span></div>
      <div class="exidx" id="exIndex"></div>
      <div class="ph"><h2>Station network</h2><span class="n" id="stncount"></span></div>''',
     "index markup")

once(u'''.learn{display:flex;align-items:center;gap:6px;''',
     u'''.exidx{padding:2px 10px 10px}
.exidx .grp{font-family:var(--disp);font-size:9px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink4);margin:9px 4px 4px}
.exidx button{display:block;width:100%;text-align:left;font-size:11.5px;line-height:1.35;color:var(--ink3);
  padding:3px 5px;border-radius:2px;border-left:2px solid transparent}
.exidx button:hover,.exidx button:focus-visible{color:var(--ice);background:var(--panel2);border-left-color:var(--s1)}
.learn{display:flex;align-items:center;gap:6px;''',
     "index css")

once(u'''/* ---------------- view modes ---------------- */
const MODES=''',
     u'''/* the index: with LEARN on, every explainer is reachable by name, not by luck */
function exIndex(){
  const head=$("#exIndexHead"), box=$("#exIndex");
  if(!head||!box) return;
  const on = !!st.learn;
  head.hidden = !on; box.hidden = !on;
  if(!on){ box.innerHTML=""; return; }
  const order=["obj","ins","num","mech"];
  const by={}; order.forEach(k=>by[k]=[]);
  for(const [id,e] of Object.entries(EXPL)) (by[e.k]||(by[e.k]=[])).push([id,e.t]);
  box.innerHTML = order.map(k=>{
    const rows=by[k]||[];
    if(!rows.length) return "";
    return `<div class="grp">${KIND[k]}</div>` + rows.map(([id,t])=>
      `<button type="button" data-ex="${id}">${t}</button>`).join("");
  }).join("");
  $("#exCount").textContent = Object.keys(EXPL).length;
}

/* ---------------- view modes ---------------- */
const MODES=''',
     "index render fn")

# keep the index in step with the LEARN switch
once(u'''$("#learnBtn").addEventListener("click",()=>{
  st.learn=!st.learn;''',
     u'''$("#learnBtn").addEventListener("click",()=>{
  st.learn=!st.learn;
  exIndex();''',
     "index follows LEARN")

# the popup should be reachable without a pointer
once(u'''document.addEventListener("pointerout",e=>{''',
     u'''document.addEventListener("focusin",e=>{
  const t=e.target.closest?.("[data-ex]");
  if(t){ const r=t.getBoundingClientRect(); showEx(t.dataset.ex, r.right, r.top); }
});
document.addEventListener("focusout",e=>{
  if(e.target.closest?.("[data-ex]")) hideEx();
});
document.addEventListener("keydown",e=>{ if(e.key==="Escape") hideEx(); });
document.addEventListener("pointerout",e=>{''',
     "keyboard route into the explainer")

io.open(SRC, "w", encoding="utf8").write(s)
print("written")
