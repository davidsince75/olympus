const { chromium } = require("playwright");
const fs=require("fs"), path=require("path");
// src/ was retired on 24 Sep 2026; dist/deck.html is what is published
const SRC = path.resolve(process.argv[2] || path.join(__dirname,"..","dist","deck.html"));
const HARNESS = '\nwindow.__oly=()=>({st,setMode,setCam,OC,CAM,hideEx,layers,drawMap,paintAll,LAYERS,sync,map,mctx,allReady:(typeof allReady!=="undefined"?allReady:null)});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
const SKELETON = (body) => `<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}
[hidden]{display:none!important}</style></head><body>${body}</body></html>`;

(async()=>{
  const raw=fs.readFileSync(SRC,"utf8");
  const wired=raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>");
  const p=path.join(__dirname,"..","build","_probe_layers.html");
  fs.writeFileSync(p, SKELETON(wired));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium-1194/chrome-linux/chrome", args:["--no-sandbox"]});
  const pg=await b.newPage({viewport:{width:1500,height:1000}});
  const errors=[];
  pg.on("pageerror",e=>errors.push("pageerror: "+String(e)));
  pg.on("console",m=>{ if(m.type()==="error") errors.push("console: "+m.text()); });
  await pg.goto("file://"+p,{waitUntil:"load",timeout:180000});
  await pg.waitForFunction(()=>window.__oly && window.__oly().OC && window.__oly().OC.ready, null, {timeout:180000}).catch(e=>console.error("OC not ready:",e.message));
  await pg.waitForTimeout(6000);

  await pg.addScriptTag({content:`
    window.__snapSetup=function(){
      const A=window.__oly(); window.__A=A;
      window.__snap=function(){
        A.drawMap();
        const d=A.mctx.getImageData(0,0,A.map.width,A.map.height).data;
        const out=new Uint8Array(d.length>>2);
        for(let i=0,k=0;i<d.length;i+=4,k++) out[k]=(d[i]+d[i+1]+d[i+2]+d[i+3])&255;
        return out;
      };
      window.__diff=function(a,b){ let n=0; for(let i=0;i<a.length;i++) if(a[i]!==b[i]) n++; return n; };
    };
  `});
  await pg.evaluate(()=>window.__snapSetup());

  const report={};
  for(const mode of ["S","N","PAIR","GLOBE"]){
    await pg.evaluate((m)=>{ const A=window.__A; A.setMode(m);
      if(m==="GLOBE"){ A.setCam(-25,-35); A.CAM.zoom=1; A.CAM.zTarget=1; A.CAM.auto=false; A.CAM.vlon=0; A.CAM.vlat=0; }
      A.hideEx(); }, mode);
    await pg.waitForTimeout(7000);   // let fields decode and the globe settle to still-resolution
    const r = await pg.evaluate(()=>{
      const A=window.__A, snap=window.__snap, diff=window.__diff;
      A.st.gMoved = performance.now()-100000; A.CAM.auto=false;
      snap(); snap();
      const base=snap(), base2=snap();
      const per={};
      for(const L of A.LAYERS){
        const id=L.id, was=A.st.lay[id];
        A.st.lay[id]=!was; A.paintAll(); const off=snap();
        A.st.lay[id]=was;  A.paintAll(); snap();
        per[id]=diff(base,off);
      }
      const wasImg=A.st.baseImg;
      A.st.baseImg="today";  const t1=snap();
      A.st.baseImg="relief"; const t2=snap();
      A.st.baseImg=wasImg;   snap();
      return {noise:diff(base,base2), total:base.length, layers:per, imgSwitch:diff(t1,t2), ready:A.allReady?A.allReady():null};
    });
    report[mode]=r;
  }
  console.log(JSON.stringify(report,null,1));
  console.log("ERRORS:", JSON.stringify([...new Set(errors)].slice(0,20),null,1));
  await b.close();
})();
