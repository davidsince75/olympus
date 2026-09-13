const { chromium } = require("playwright");
const path=require("path"), fs=require("fs");
const HARNESS='window.__oly=()=>({st,setMode,setCam,OC,CAM,hideEx,layers});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
(async()=>{
  const raw=fs.readFileSync(process.argv[2],"utf8");
  const p=path.join("build/shots","sh.html");
  fs.writeFileSync(p, raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>"));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage({viewport:{width:1500,height:950},deviceScaleFactor:1.5});
  await pg.goto("file://"+path.resolve(p),{waitUntil:"load",timeout:120000});
  await pg.waitForFunction("window.__oly().OC && window.__oly().OC.ready",null,{timeout:90000});
  await pg.waitForTimeout(4000);
  const shots=[
    ["01-globe-atlantic", -20, -35, 1],
    ["02-globe-south",    -58,  10, 1],
    ["03-globe-pacific",   10, 200, 1],
    ["04-globe-zoom",      35, -62, 2.4],
  ];
  for(const [name,lat,lon,z] of shots){
    await pg.evaluate(([lat,lon,z])=>{ const A=window.__oly();
      A.setMode("GLOBE"); A.setCam(lat,lon); A.CAM.zoom=z; A.CAM.zTarget=z; A.CAM.auto=false;
      A.OC.budgetOff=true; A.OC.nPart=Math.round(A.OC.P*0.9); A.hideEx(); }, [lat,lon,z]);
    await pg.waitForTimeout(3500);
    await pg.locator("#map").screenshot({path:"build/shots/"+name+".png"});
    console.log("wrote "+name);
  }
  await pg.evaluate(()=>{ const A=window.__oly(); A.setMode("S"); A.hideEx(); });
  await pg.waitForTimeout(3500);
  await pg.locator("#map").screenshot({path:"build/shots/05-disc-antarctic.png"});
  await pg.evaluate(()=>{ const A=window.__oly(); A.setMode("PAIR"); A.hideEx(); });
  await pg.waitForTimeout(3500);
  await pg.locator("#map").screenshot({path:"build/shots/06-twin.png"});
  console.log("wrote discs");
  await b.close();
})();
