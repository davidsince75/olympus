/* Render a surface the way the artifact host does — same skeleton — and check
   the learning layer in a real browser: no console errors, every explainer
   reachable, popups carry their provenance line, controls do something. */
const fs = require("fs"), path = require("path"), os = require("os");
const { chromium } = require("playwright-core");

const SKEL_HEAD = '<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:light}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#faf9f5;color:#141413}img{max-width:100%}[hidden]:not([hidden=until-found]){display:none!important}</style></head><body>\n';

(async () => {
  const src = process.argv[2], shot = process.argv[3];
  const tmp = path.join(os.tmpdir(), "render-" + path.basename(src));
  fs.writeFileSync(tmp, SKEL_HEAD + fs.readFileSync(src, "utf8") + "\n</body></html>");

  const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
                                          args: ["--no-sandbox", "--disable-dev-shm-usage"] });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  const errs = [];
  page.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  page.on("pageerror", e => errs.push("PAGEERROR " + e.message));

  await page.goto("file://" + tmp, { waitUntil: "load", timeout: 90000 });
  await page.waitForTimeout(3500);

  const r = await page.evaluate(() => {
    const out = {};
    const idx = document.querySelectorAll("#exIndex button, .exidx button");
    out.indexButtons = idx.length;
    out.targets = document.querySelectorAll("[data-ex]").length;
    out.canvasPainted = (() => {
      const c = document.querySelector("#map"); if (!c) return null;
      const g = c.getContext("2d"); const d = g.getImageData(0,0,c.width,c.height).data;
      let lit = 0; for (let i = 0; i < d.length; i += 4000) if (d[i]+d[i+1]+d[i+2] > 40) lit++;
      return lit;
    })();
    out.bars = {
      base: !!document.querySelector("#baseBar"),
      drift: !!document.querySelector("#driftBar"),
      baseHidden: document.querySelector("#baseBar")?.hidden,
      imgDay: document.querySelector("#imgDay")?.textContent
    };
    return out;
  });

  // hover a sample of targets and read the popup back out of the DOM
  const sample = ["reprojection","ovation","drift_cmcc","sar_footprints","kp_index",
                  "truecolor","bluemarble","polar_night","terra_drift","live_transport",
                  "age_stamp","drift_pump","surfaces","stn_deck","graticule","drift_true_length",
                  "sim_layer","osnap_e","osnap_w","sea_level","albedo","pole_hole"];
  const popups = {};
  for (const key of sample) {
    const el = await page.$(`[data-ex="${key}"]`);
    if (!el) { popups[key] = "NO TARGET"; continue; }
    try { await el.hover({ timeout: 3000 }); } catch (e) { popups[key] = "UNHOVERABLE"; continue; }
    await page.waitForTimeout(60);
    popups[key] = await page.evaluate(() => {
      const b = document.querySelector(".exbox");
      if (!b || b.hidden) return "HIDDEN";
      return (b.querySelector(".exh b")?.textContent || "?") + " | prov:" +
             ((b.querySelector(".exp")?.textContent || "").slice(0, 40));
    });
  }

  // does the imagery switch actually change the picture
  const before = await page.evaluate(() => { const c=document.querySelector("#map"); return c.toDataURL().length; });
  await page.click('#baseBar button[data-img="today"]').catch(()=>{});
  await page.waitForTimeout(1200);
  const after = await page.evaluate(() => { const c=document.querySelector("#map"); return c.toDataURL().length; });
  const imgDay = await page.evaluate(() => document.querySelector("#imgDay")?.textContent);

  // drift exaggeration must announce itself
  await page.click('#driftBar button[data-x="5"]').catch(()=>{});
  await page.waitForTimeout(300);
  const driftNote = await page.evaluate(() => document.querySelector("#driftNote")?.textContent);

  if (shot) await page.screenshot({ path: shot, fullPage: false });
  console.log(JSON.stringify({ errs, r, popups, imageSwitch: { before, after, changed: before !== after, imgDay }, driftNote }, null, 1));
  await browser.close();
})();
