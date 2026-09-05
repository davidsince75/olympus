# -*- coding: utf-8 -*-
import io, sys
SRC = "/home/claude/olympus/src/atlas.html"
s = io.open(SRC, encoding="utf8").read()
def once(old, new, label):
    global s
    n = s.count(old)
    if n != 1: sys.exit("FAIL %s: %d matches" % (label, n))
    s = s.replace(old, new, 1); print("  ok  %s" % label)

# callouts are drawn last so nothing on the network covers them
once(u'''  g.restore();
  $("#zoomR").textContent = "ZOOM " + st.discs.map(d=>d.z.toFixed(1)+"×").join(" / ");
}''',
     u'''  g.restore();
  st.discs.forEach(d=>{ try{ drawAnnot(d); }catch(e){} });
  $("#zoomR").textContent = "ZOOM " + st.discs.map(d=>d.z.toFixed(1)+"×").join(" / ");
}''',
     "call drawAnnot")

# a callout hotspot explains itself; a station hotspot still shows its tooltip
once(u'''  const h = hit(mx,my), tip = $("#tip");
  if(h){
    const o = BY.get(h.id);''',
     u'''  const h = hit(mx,my), tip = $("#tip");
  if(h && h.ex){
    tip.style.opacity = 0;
    map.style.cursor = "help";
    showEx(h.ex, ev.clientX, ev.clientY);
    return;
  }
  hideEx();
  if(h){
    const o = BY.get(h.id);''',
     "callout hover")

# and a click on a callout must not try to select a station that is not there
once(u'''function hit(mx,my){''',
     u'''function hit(mx,my){''', "noop")
io.open(SRC, "w", encoding="utf8").write(s)
print("wired")
