/* Olympus — does the aurora read, and does it move?
 *
 * Two questions, both asked of pixels rather than of objects.
 *
 *   PRESENCE  mean |frame(aurora on) - frame(aurora off)| over the disc.
 *             This is exactly the thing David reported: the layer could only be
 *             found by switching it off. The number is how much switching it off
 *             changes the picture.
 *   MOTION    mean |frame(t) - frame(t+dt)| with the aurora on, minus the same
 *             with it off. The particle layer is turned off first so the only
 *             thing left that can move is the oval.
 *
 * Absolute figures from a software rasteriser mean nothing. The assertions are
 * differentials between the old file and the new one.
 *
 *   node probe_aurora.cjs deck.old.html deck.html
 */
const { chromium } = require("playwright");
const path = require("path");

const DT = 1400;

/* The globe auto-rotates once it has been left alone, and two frames taken at
   two different camera angles compare nothing. A tap on a corner of the panel is
   off-globe — it selects nothing — and resets the idle timer, so the camera is
   held still while the measurement is taken. */
async function hold(page, mode){
  if(mode !== "GLOBE") return;
  const box = await page.$eval("#map", el => { const r = el.getBoundingClientRect();
    return {x:r.x, y:r.y}; });
  await page.mouse.click(box.x+8, box.y+8);
}

async function shot(page){
  return await page.evaluate(() => {
    const c = document.querySelector("#map");
    const g = c.getContext("2d");
    const d = g.getImageData(0,0,c.width,c.height).data;
    // downsample to keep the payload small and the comparison stable
    const out = [];
    for(let i=0;i<d.length;i+=4*7) out.push(d[i],d[i+1],d[i+2]);
    return out;
  });
}
const diff = (a,b) => {
  let s=0; for(let i=0;i<a.length;i++) s += Math.abs(a[i]-b[i]);
  return s/a.length;
};
const sleep = ms => new Promise(r=>setTimeout(r,ms));

/* The globe animates on its own — the deep limbs travel — so a single pair of
   frames measures that and not the aurora. Presence is therefore read off the
   mean of eight frames spread over two seconds: whatever moves on its own
   averages to the same thing in both states, and what is left is the layer. */
async function mean(page, mode){
  let acc = null;
  for(let i=0;i<8;i++){
    await hold(page, mode);
    const f = await shot(page);
    if(!acc) acc = f.map(v=>v);
    else for(let j=0;j<acc.length;j++) acc[j] += f[j];
    await sleep(250);
  }
  return acc.map(v=>v/8);
}

async function setMode(page,m){
  await page.click(`#modeBar button[data-mode="${m}"]`);
  await sleep(1200);
}
async function toggle(page,id){
  await page.click(`.lay[data-id="${id}"]`);
  await sleep(350);
}
async function isOn(page,id){
  return await page.$eval(`.lay[data-id="${id}"]`, el => el.classList.contains("on"));
}

async function measure(file, label, outdir){
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport:{width:1600,height:1000}, deviceScaleFactor:1 });
  const errs = [];
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto("file://"+path.resolve(file));
  await page.waitForSelector("#map");
  await sleep(3000);
  // the drifting particle field would swamp the motion measurement
  if(await isOn(page,"flow")) await toggle(page,"flow");
  const res = {};
  for(const mode of ["S","N","GLOBE"]){
    await setMode(page, mode);
    await sleep(900);
    if(!(await isOn(page,"aur"))) await toggle(page,"aur");
    await hold(page, mode);
    const on1 = await shot(page);
    await sleep(DT);
    await hold(page, mode);
    const on2 = await shot(page);
    const onAvg = await mean(page, mode);
    await page.screenshot({ path: `${outdir}/${label}-${mode}-on.png` });
    await toggle(page,"aur");
    await sleep(500);
    await hold(page, mode);
    const off1 = await shot(page);
    await sleep(DT);
    await hold(page, mode);
    const off2 = await shot(page);
    const offAvg = await mean(page, mode);
    await page.screenshot({ path: `${outdir}/${label}-${mode}-off.png` });
    await toggle(page,"aur");
    res[mode] = { presence: diff(onAvg,offAvg), motionOn: diff(on1,on2), motionOff: diff(off1,off2) };
  }
  await browser.close();
  return { res, errs };
}

(async () => {
  const [oldF, newF] = process.argv.slice(2);
  const A = await measure(oldF, "old", "shots");
  const B = await measure(newF, "new", "shots");
  let fail = 0;
  const ok = (c,msg) => { console.log((c?"  ok  ":"FAIL  ")+msg); if(!c) fail++; };

  console.log("\npage errors — old:", A.errs.length, " new:", B.errs.length);
  B.errs.slice(0,5).forEach(e=>console.log("   ", e));
  ok(B.errs.length === 0, "the patched deck throws nothing");

  for(const m of ["S","N","GLOBE"]){
    const a = A.res[m], b = B.res[m];
    console.log(`\n${m}`);
    console.log(`  presence   old ${a.presence.toFixed(3)}   new ${b.presence.toFixed(3)}   ×${(b.presence/Math.max(1e-6,a.presence)).toFixed(2)}`);
    console.log(`  motion on  old ${a.motionOn.toFixed(3)}   new ${b.motionOn.toFixed(3)}`);
    console.log(`  motion off old ${a.motionOff.toFixed(3)}   new ${b.motionOff.toFixed(3)}`);
    ok(b.presence > a.presence*2.0, `${m}: switching the aurora off changes the picture at least twice as much as before`);
    ok(a.motionOn - a.motionOff < 0.15, `${m}: the old aurora did not move`);
    ok(b.motionOn - b.motionOff > 0.30, `${m}: the new aurora does move, and it is the aurora that moves`);
  }
  console.log(fail ? `\n${fail} FAILED` : "\nall assertions passed");
  process.exit(fail ? 1 : 0);
})();
