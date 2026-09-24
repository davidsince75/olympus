const { chromium } = require("playwright");
const fs=require("fs"), path=require("path");
const SRC=path.resolve(process.argv[2] || path.join(__dirname,"..","dist","deck.html"));
const HARNESS='\nwindow.__oly=()=>({st,setMode,setCam,OC,CAM,DISC,hideEx,drawMap,map,mctx,discZoom,discReset,zoomOf,modeUI});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
const SK=b=>`<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0}[hidden]{display:none!important}</style></head><body>${b}</body></html>`;
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{
  const raw=fs.readFileSync(SRC,"utf8");
  const p=path.join(__dirname,"..","build","_probe_zoom.html");
  fs.writeFileSync(p,SK(raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>")));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium-1194/chrome-linux/chrome",args:["--no-sandbox"]});
  const pg=await b.newPage({viewport:{width:1500,height:1000}});
  const errs=[]; pg.on("pageerror",e=>errs.push(String(e)));
  pg.on("console",m=>{if(m.type()==="error")errs.push(m.text());});
  await pg.goto("file://"+p,{waitUntil:"load",timeout:180000});
  await pg.waitForFunction(()=>window.__oly&&window.__oly().OC&&window.__oly().OC.ready,null,{timeout:180000}).catch(()=>{});
  await sleep(7000);
  const out={};

  // --- the bar is present, and hidden only in Both
  await pg.evaluate(()=>window.__oly().setMode("S")); await sleep(900);
  out.barVisible_S = await pg.locator("#zoomBar").isVisible();
  out.pct_S_start = (await pg.locator("#zoomPct").textContent()).trim();

  // --- the + button actually magnifies the canvas
  const shot=async()=>{ return await pg.evaluate(()=>{
     const A=window.__oly(); A.drawMap();
     const d=A.mctx.getImageData(0,0,A.map.width,A.map.height).data;
     let n=0; for(let i=0;i<d.length;i+=4*53) if(d[i]+d[i+1]+d[i+2]>90) n++;
     return {lit:n, s:A.st.s, z:A.DISC.z, x:A.DISC.x, y:A.DISC.y};
  });};
  out.before = await shot();
  for(let i=0;i<4;i++){ await pg.locator('#zoomBar button[data-zoom="in"]').click(); await sleep(450); }
  await sleep(900);
  out.afterPlus = await shot();
  out.pct_S_zoomed = (await pg.locator("#zoomPct").textContent()).trim();

  // --- drag pans, and the pan is clamped inside (z-1) radii
  const box=await pg.locator("#map").boundingBox();
  await pg.mouse.move(box.x+box.width/2, box.y+box.height/2);
  await pg.mouse.down();
  for(let i=1;i<=12;i++) await pg.mouse.move(box.x+box.width/2+i*60, box.y+box.height/2+i*30);
  await pg.mouse.up(); await sleep(700);
  const panned = await shot();
  out.panned = panned;
  out.panWithinClamp = Math.hypot(panned.x,panned.y) <= (panned.z-1)*(Math.min(box.width,box.height)/2*0.93)+1.5;

  // --- wheel zooms, anchored
  await pg.mouse.move(box.x+box.width*0.35, box.y+box.height*0.62);
  await pg.mouse.wheel(0,-600); await sleep(800);
  out.afterWheel = await shot();

  // --- reset
  await pg.locator('#zoomBar button[data-zoom="reset"]').click(); await sleep(900);
  out.afterReset = await shot();
  out.pct_S_reset = (await pg.locator("#zoomPct").textContent()).trim();

  // --- at z=1 a drag must not move the disc
  await pg.mouse.move(box.x+box.width/2, box.y+box.height/2);
  await pg.mouse.down();
  for(let i=1;i<=8;i++) await pg.mouse.move(box.x+box.width/2+i*40, box.y+box.height/2);
  await pg.mouse.up(); await sleep(600);
  out.unzoomedDragMoves = await shot();

  // --- Arctic keeps its own working camera; Both hides the bar; Globe uses CAM
  await pg.evaluate(()=>window.__oly().setMode("N")); await sleep(2500);
  await pg.locator('#zoomBar button[data-zoom="in"]').click(); await sleep(700);
  out.pct_N = (await pg.locator("#zoomPct").textContent()).trim();
  out.N = await shot();

  await pg.evaluate(()=>window.__oly().setMode("PAIR")); await sleep(1200);
  out.barVisible_PAIR = await pg.locator("#zoomBar").isVisible();

  await pg.evaluate(()=>{const A=window.__oly(); A.setMode("GLOBE"); A.setCam(-25,-35); A.CAM.auto=false;}); await sleep(2500);
  out.pct_G_start = (await pg.locator("#zoomPct").textContent()).trim();
  await pg.locator('#zoomBar button[data-zoom="in"]').click(); await sleep(900);
  out.pct_G_zoomed = (await pg.locator("#zoomPct").textContent()).trim();
  out.G_zoom = await pg.evaluate(()=>window.__oly().CAM.zoom);
  await pg.locator('#zoomBar button[data-zoom="reset"]').click(); await sleep(900);
  out.pct_G_reset = (await pg.locator("#zoomPct").textContent()).trim();

  out.errors=[...new Set(errs)].filter(e=>!/ERR_CONNECTION_RESET|fonts\.googleapis/.test(e));
  console.log(JSON.stringify(out,null,1));
  await b.close();
})();
