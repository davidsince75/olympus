const { chromium } = require("playwright");
const path=require("path"), fs=require("fs");
const HARNESS='window.__oly=()=>({OCEAN,isLand});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
(async()=>{
  const raw=fs.readFileSync(process.argv[2],"utf8");
  const p=path.join(__dirname,"..","build","shots","lc.html");
  fs.mkdirSync(path.dirname(p),{recursive:true});
  fs.writeFileSync(p, raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>"));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage();
  await pg.goto("file://"+path.resolve(p),{waitUntil:"load",timeout:120000});
  await pg.waitForFunction("window.__oly",null,{timeout:60000});
  await pg.waitForTimeout(2500);
  const r=await pg.evaluate(()=>{
    const {OCEAN,isLand}=window.__oly(); const bad=[];
    for(const L of OCEAN.limbs){ const pts=[];
      for(let i=0;i<L.n;i++){ const lon=((L.pts[i*3]+180)%360+360)%360-180, lat=L.pts[i*3+1];
        if(isLand(lat,lon)) pts.push([+lon.toFixed(1),+lat.toFixed(1)]); }
      if(pts.length) bad.push({id:L.id,n:pts.length,of:L.n,pts});
    }
    return bad;
  });
  await b.close();
  if(!r.length) console.log("CLEAN — no limb vertex falls on land");
  for(const x of r) console.log(x.id, `${x.n}/${x.of}`, JSON.stringify(x.pts));
})();
