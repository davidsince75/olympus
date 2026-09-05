const fs = require("fs"), path = require("path"), os = require("os");
const { chromium } = require("playwright-core");
const SKEL = '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:light}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#faf9f5;color:#141413}img{max-width:100%}[hidden]:not([hidden=until-found]){display:none!important}</style></head><body>\n';

(async () => {
  const src = process.argv[2], shot = process.argv[3];
  const tmp = path.join(os.tmpdir(), "r-atlas.html");
  fs.writeFileSync(tmp, SKEL + fs.readFileSync(src, "utf8") + "\n</body></html>");
  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args:["--no-sandbox","--disable-dev-shm-usage"] });
  const page = await browser.newPage({ viewport:{width:1600,height:1000} });
  const errs = []; page.on("console", m=>{ if(m.type()==="error") errs.push(m.text()); });
  page.on("pageerror", e=>errs.push("PAGEERROR "+e.message));
  await page.goto("file://"+tmp, { waitUntil:"load", timeout:90000 });
  await page.waitForTimeout(3000);

  const before = await page.evaluate(()=>({
    indexHidden: document.querySelector("#exIndexHead")?.hidden,
    learn: document.querySelector("#learnBtn")?.getAttribute("aria-pressed"),
    hotWithEx: (typeof HOT!=="undefined" ? HOT.filter(h=>h.ex).length : "n/a")
  }));
  await page.click("#learnBtn");
  await page.waitForTimeout(700);
  const after = await page.evaluate(()=>({
    learn: document.querySelector("#learnBtn")?.getAttribute("aria-pressed"),
    indexButtons: document.querySelectorAll("#exIndex button").length,
    indexHidden: document.querySelector("#exIndexHead")?.hidden,
    targets: document.querySelectorAll("[data-ex]").length,
    calloutHots: (()=>{ try { return HOT.filter(h=>h.ex).map(h=>h.ex); } catch(e){ return "HOT not in scope"; } })()
  }));

  // hover every entry through the index — that is the guaranteed route
  const keys = await page.evaluate(()=>[...document.querySelectorAll("#exIndex button")].map(b=>b.dataset.ex));
  const broken = [];
  for(const k of keys){
    const el = await page.$(`#exIndex button[data-ex="${k}"]`);
    await el.hover().catch(()=>{});
    await page.waitForTimeout(25);
    const r = await page.evaluate(()=>{
      const b=document.querySelector(".exbox");
      if(!b||b.hidden) return null;
      return {t:b.querySelector(".exh b")?.textContent, k:b.querySelector(".exk")?.textContent,
              blen:(b.querySelector(".exb")?.textContent||"").length, p:(b.querySelector(".exp")?.textContent||"").length};
    });
    if(!r || !r.t || r.blen<60 || r.p<10) broken.push([k,r]);
  }

  // a callout on the map must open its explainer on hover
  const calloutTest = await page.evaluate(async ()=>{
    if(typeof HOT==="undefined") return "HOT not reachable";
    const h = HOT.find(x=>x.ex); if(!h) return "no callout in HOT";
    const c = document.querySelector("#map"), r = c.getBoundingClientRect();
    c.dispatchEvent(new PointerEvent("pointermove",{clientX:r.left+h.x, clientY:r.top+h.y, bubbles:true, pointerType:"mouse"}));
    await new Promise(z=>setTimeout(z,80));
    const b=document.querySelector(".exbox");
    return {ex:h.ex, shown: b && !b.hidden, title: b?.querySelector(".exh b")?.textContent};
  });

  // and turning LEARN off must take the callouts back off the map
  await page.click("#learnBtn"); await page.waitForTimeout(500);
  const off = await page.evaluate(()=>({ hots:(typeof HOT!=="undefined"?HOT.filter(h=>h.ex).length:"n/a"),
                                         indexHidden: document.querySelector("#exIndexHead")?.hidden }));
  await page.click("#learnBtn"); await page.waitForTimeout(600);
  if(shot) await page.screenshot({path:shot});
  console.log(JSON.stringify({errs, before, after, brokenPopups:broken, calloutTest, learnOff:off}, null, 1));
  await browser.close();
})();
