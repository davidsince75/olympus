const { chromium } = require("playwright");
const path=require("path"), fs=require("fs");
const HARNESS='window.__oly=()=>({st,setMode,setCam,drawMap});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
async function run(file,label){
  const raw=fs.readFileSync(file,"utf8");
  const p=path.join("build/shots", path.basename(file)+".perf.html");
  fs.writeFileSync(p, raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>"));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage({viewport:{width:1440,height:900},deviceScaleFactor:2});
  await pg.goto("file://"+path.resolve(p),{waitUntil:"load",timeout:120000});
  await pg.waitForFunction("window.__oly",null,{timeout:60000});
  await pg.waitForTimeout(4000);
  const res=await pg.evaluate(async()=>{
    const {setMode,setCam}=window.__oly();
    const run=async(l,fn)=>{ fn(); await new Promise(r=>setTimeout(r,600));
      const t=[]; let last=performance.now();
      await new Promise(res=>{let n=0;const tk=()=>{const now=performance.now();t.push(now-last);last=now;
        if(++n<110) requestAnimationFrame(tk); else res();}; requestAnimationFrame(tk);});
      const s=t.slice(10).sort((a,b)=>a-b);
      return {l, med:+s[s.length>>1].toFixed(1), p95:+s[Math.floor(s.length*.95)].toFixed(1)};
    };
    const o=[];
    o.push(await run("globe still",()=>{setMode("GLOBE"); setCam(20,-40);}));
    o.push(await run("antarctic disc",()=>{setMode("S");}));
    o.push(await run("twin discs",()=>{setMode("PAIR");}));
    return o;
  });
  const mob=await (async()=>{ await pg.setViewportSize({width:420,height:820}); await pg.waitForTimeout(600);
    return pg.evaluate(()=>({sw:document.documentElement.scrollWidth, iw:window.innerWidth})); })();
  await b.close();
  console.log(label.padEnd(12), res.map(r=>`${r.l}: ${r.med}/${r.p95} ms`).join("   "), " | 420px scrollWidth", mob.sw, "vs", mob.iw);
}
(async()=>{ await run(process.argv[2],"BEFORE"); await run(process.argv[3],"AFTER"); })();
