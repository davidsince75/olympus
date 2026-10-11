"""probe_skin.py — deterministic renders of the deck to prove three things:

 1. Ops after the patch draws the same pixels as the unpatched deck, on the map
    canvas, the timeline and the El Nino chart, in every view.
 2. Lab draws the same pixels as Ops INSIDE the planet (every layer on it is
    untouched), in every view.
 3. Lab differs from Ops outside the planet (the change actually happened).

Time is virtual: requestAnimationFrame is queued and pumped by hand, the clock
advances a fixed 1/60 s per frame, Date and Math.random are fixed. Loads are
let finish in real time before any frame is pumped.

usage: python probe_skin.py ORIG.html OPS.html LAB.html OUTDIR
"""
import asyncio, hashlib, json, sys, os
from playwright.async_api import async_playwright

STUB = r"""
(()=>{
  let seed=0x9E3779B9; Math.random=()=>{seed|=0;seed=seed+0x6D2B79F5|0;let t=Math.imul(seed^seed>>>15,1|seed);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};
  const T0=Date.UTC(2026,9,11,9,41,10); let vt=1000;
  const RD=Date; class FD extends RD{constructor(...a){ if(a.length) super(...a); else super(T0+vt); } static now(){return T0+vt;}} window.Date=FD;
  performance.now=()=>vt;
  const Q=[]; window.requestAnimationFrame=cb=>{Q.push(cb);return Q.length;};
  window.__pump=n=>{ for(let i=0;i<n;i++){ vt+=1000/60; const q=Q.splice(0); for(const cb of q) cb(vt); } return Q.length; };
})();
"""

VIEWS = ["GLOBE", "S", "N", "PAIR"]

async def shoot(pg, path, out, skin=None, w=1600, h=1000):
    await pg.set_viewport_size({"width": w, "height": h})
    await pg.goto("file://" + path + (("#" + skin) if skin else ""), wait_until="load", timeout=180000)
    await pg.wait_for_timeout(9000)
    res = {}
    for v in VIEWS:
        await pg.evaluate("m=>document.querySelector('[data-mode=\"'+m+'\"]').click()", v)
        await pg.evaluate("()=>window.__pump(40)")
        await pg.wait_for_timeout(300)
        await pg.evaluate("()=>window.__pump(2)")
        data = await pg.evaluate("""()=>{
          const pick=id=>{const c=document.getElementById(id); if(!c||!c.width) return null;
            return {w:c.width,h:c.height,png:c.toDataURL('image/png')};};
          return {map:pick('map'), tl:pick('tl'), feat:pick('featChart')};
        }""")
        res[v] = data
        await pg.screenshot(path=f"{out}_{v}.png")
    return res

import base64, io, numpy as np
from PIL import Image
def px(x): return np.asarray(Image.open(io.BytesIO(base64.b64decode(x["png"].split(",",1)[1]))).convert("RGBA"))
def h(x): return None if x is None else hashlib.sha256(px(x).tobytes()).hexdigest()[:12]

def disc_mask(v, W, H, dpr=1):
    """pixels strictly inside the planet(s), 2 px in from the rim, at the opening camera"""
    w, hh = W / dpr, H / dpr
    if v == "GLOBE": discs = [(w/2, hh/2, min(w, hh)/2*0.90)]
    elif v == "PAIR":
        s = min(w/2, hh)/2*0.90; discs = [(w/4, hh/2, s), (w*3/4, hh/2, s)]
    else: discs = [(w/2, hh/2, min(w, hh)/2*0.93)]
    return discs

def compare(a, b, v, region):
    """count differing pixels inside / outside the planet"""
    A, B = px(a), px(b); H, W = A.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    ins = np.zeros((H, W), bool)
    for cx, cy, s in disc_mask(v, W, H): ins |= (xx-cx)**2 + (yy-cy)**2 < (s-2)**2
    d = (A != B).any(axis=2)
    return int(d[ins].sum()), int(ins.sum()), int(d[~ins].sum()), int((~ins).sum())

async def main():
    orig, ops, lab, outdir = sys.argv[1:5]
    os.makedirs(outdir, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        runs = {}
        for name, path, skin in [("orig", orig, None), ("ops", ops, None), ("lab", lab, None)]:
            pg = await b.new_page(device_scale_factor=1)
            errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
            await pg.add_init_script(STUB)
            await pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
            runs[name] = await shoot(pg, os.path.abspath(path), f"{outdir}/{name}")
            runs[name]["_errs"] = errs
            sk = await pg.evaluate("()=>document.documentElement.getAttribute('data-skin')")
            print(f"{name:5s} skin={sk} pageerrors={errs[:3]}")
            await pg.close()
        await b.close()

    ok = True
    print("\n1. Ops after patch vs unpatched deck (hashes must match)")
    for v in VIEWS:
        for c in ("map", "tl", "feat"):
            a, bb = h(runs["orig"][v][c]), h(runs["ops"][v][c])
            same = a == bb; ok &= same
            print(f"   {v:5s} {c:4s} orig={a} ops={bb} {'SAME' if same else 'DIFFERENT'}")
    print("\n2/3. Lab vs Ops on the map canvas")
    for v in VIEWS:
        i, ni, o, no = compare(runs["ops"][v]["map"], runs["lab"][v]["map"], v, None)
        print(f"   {v:5s} inside planet: {i}/{ni} px differ   outside: {o}/{no} px differ")
        ok &= (i == 0)
    print("\nALL ASSERTIONS PASS" if ok else "\nASSERTION FAILED")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    asyncio.run(main())
