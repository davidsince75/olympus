/* screenshots in the states a reader will actually meet */
const fs=require("fs"),path=require("path"),os=require("os");
const {chromium}=require("playwright-core");
const SKEL='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>:root{color-scheme:light}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#faf9f5;color:#141413}img{max-width:100%}[hidden]:not([hidden=until-found]){display:none!important}</style></head><body>\n';
(async()=>{
  const src=process.argv[2], out=process.argv[3], mode=process.argv[4]||"";
  const tmp=path.join(os.tmpdir(),"v-"+path.basename(src));
  fs.writeFileSync(tmp,SKEL+fs.readFileSync(src,"utf8")+"\n</body></html>");
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium-1194/chrome-linux/chrome",args:["--no-sandbox","--disable-dev-shm-usage"]});
  const p=await b.newPage({viewport:{width:1600,height:1000}});
  await p.goto("file://"+tmp,{waitUntil:"load",timeout:90000});
  await p.waitForTimeout(3000);
  if(mode.includes("learn")) { await p.click("#learnBtn").catch(()=>{}); await p.waitForTimeout(800); }
  if(mode.includes("arctic")) { await p.click('#modeBar button[data-mode="N"]').catch(()=>{}); await p.waitForTimeout(1200); }
  if(mode.includes("hover")) {
    const k=mode.split("hover:")[1].split(",")[0];
    const el=await p.$(`[data-ex="${k}"]`); if(el){ await el.hover().catch(()=>{}); await p.waitForTimeout(300); }
  }
  await p.screenshot({path:out});
  await b.close();
})();
