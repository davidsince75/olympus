"""probe_skin_atlas.py — the skins on the Station Network, checked like the deck's.

 1. Ops after the patch draws the same map pixels as the unpatched surface, in
    the Antarctic, Arctic and Both views, plain and with a station selected and
    the learning layer's annotations on.
 2. Lab draws the same pixels as Ops inside every imagery disc.
 3. Lab differs from Ops outside the discs (the change actually happened).

Time is virtual (requestAnimationFrame queued and pumped by hand, a fixed clock,
seeded Math.random), as in scripts/probe_skin.py. The disc geometry is read
from the page's own state, not assumed.

usage: python scripts/probe_skin_atlas.py ORIG.html OPS.html LAB.html OUTDIR
"""
import asyncio, base64, hashlib, io, os, sys
import numpy as np
from PIL import Image
from playwright.async_api import async_playwright

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe_skin import STUB  # noqa: E402

# (label, mode, select a station?, learning layer on?)
CASES = [("S", "S", False, False), ("N", "N", False, False), ("BOTH", "BOTH", False, False),
         ("S-sel", "S", True, False), ("S-learn", "S", False, True)]

async def run(b, path, out):
    pg = await b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1)
    errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.add_init_script(STUB)
    await pg.route("**/fonts.googleapis.com/**", lambda r: r.abort())
    await pg.goto("file://" + os.path.abspath(path), wait_until="load", timeout=120000)
    await pg.wait_for_timeout(5000)
    await pg.evaluate("()=>window.__pump(5)")
    res = {}
    for label, mode, sel, learn in CASES:
        await pg.evaluate("m=>document.querySelector('[data-mode=\"'+m+'\"]').click()", mode)
        await pg.evaluate("s=>{ select(s ? ([...BY.values()].find(o=>/Concordia/.test(o.name||''))||{}).id||null : null, false); }", sel)
        if learn != (await pg.evaluate("()=>st.learn")):
            await pg.click("#learnBtn")
        await pg.evaluate("()=>window.__pump(30)")
        await pg.wait_for_timeout(250)
        await pg.evaluate("()=>window.__pump(2)")
        data = await pg.evaluate("""()=>{const c=document.getElementById('map');
          const k=s=>((IMG&&IMG.rmax&&IMG.rmax[s?'S':'N'])||GMAX[s?'S':'N']);
          const dpr=c.width/c.clientWidth;
          return {png:c.toDataURL('image/png'), discs:st.discs.map(d=>[d.cx*dpr,d.cy*dpr,d.k*k(d.S)*dpr,d.x0*dpr,d.x1*dpr])}}""")
        res[label] = data
        await pg.screenshot(path=f"{out}_{label}.png")
    skin = await pg.evaluate("()=>document.documentElement.getAttribute('data-skin')")
    await pg.close()
    return res, errs, skin

def px(x): return np.asarray(Image.open(io.BytesIO(base64.b64decode(x["png"].split(",", 1)[1]))).convert("RGBA"))

def main_sync(runs):
    ok = True
    print("\n1. Ops after the patch vs the unpatched surface (map canvas)")
    for label, *_ in CASES:
        a, b = px(runs["orig"][label]), px(runs["ops"][label])
        same = a.shape == b.shape and (a == b).all(); ok &= same
        print(f"   {label:8s} {'SAME' if same else 'DIFFERENT  %d px' % int((a != b).any(axis=2).sum()) if a.shape == b.shape else 'SIZE'}")
    print("\n2/3. Lab vs Ops on the map canvas")
    for label, *_ in CASES:
        A, B = px(runs["ops"][label]), px(runs["lab"][label]); H, W = A.shape[:2]
        yy, xx = np.mgrid[0:H, 0:W]; ins = np.zeros((H, W), bool)
        for cx, cy, r, x0, x1 in runs["ops"][label]["discs"]:
            ins |= ((xx - cx) ** 2 + (yy - cy) ** 2 < (r - 2) ** 2) & (xx > x0 + 1) & (xx < x1 - 1)
        d = (A != B).any(axis=2)
        i, o = int(d[ins].sum()), int(d[~ins].sum())
        print(f"   {label:8s} inside discs: {i}/{int(ins.sum())} px differ   outside: {o}/{int((~ins).sum())} px differ")
        ok &= (i == 0)
    print("\nALL ASSERTIONS PASS" if ok else "\nASSERTION FAILED")
    return ok

async def main():
    orig, ops, lab, outdir = sys.argv[1:5]
    os.makedirs(outdir, exist_ok=True)
    runs = {}
    async with async_playwright() as p:
        b = await p.chromium.launch(args=["--use-gl=swiftshader", "--enable-unsafe-swiftshader"])
        for name, path in [("orig", orig), ("ops", ops), ("lab", lab)]:
            runs[name], errs, skin = await run(b, path, f"{outdir}/{name}")
            print(f"{name:5s} skin={skin} pageerrors={errs[:3]}")
        await b.close()
    sys.exit(0 if main_sync(runs) else 1)

asyncio.run(main())
