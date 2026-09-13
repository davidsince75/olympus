const { chromium } = require("playwright");
const path=require("path"), fs=require("fs");
const HARNESS='window.__oly=()=>({st,setMode,setCam,OC,CAM,hideEx,sync,flowNote,drawMap});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
(async()=>{
  const raw=fs.readFileSync(process.argv[2],"utf8");
  const p=path.join("build/shots","sw.html");
  fs.writeFileSync(p, raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>"));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage({viewport:{width:1400,height:900},deviceScaleFactor:1.5});
  await pg.goto("file://"+path.resolve(p),{waitUntil:"load",timeout:120000});
  await pg.waitForFunction("window.__oly().OC && window.__oly().OC.tok",null,{timeout:120000});
  await pg.waitForTimeout(4000);
  const go=async(name,col,lat,lon,zoom)=>{
    await pg.evaluate(([col,lat,lon,zoom])=>{ const A=window.__oly();
      A.setMode("GLOBE"); A.setCam(lat,lon); A.CAM.zoom=zoom; A.CAM.zTarget=zoom; A.CAM.auto=false;
      A.st.flowCol=col; A.OC.budgetOff=true; A.OC.nPart=Math.round(A.OC.P*0.95);
      A.sync(); A.flowNote(); A.hideEx(); },[col,lat,lon,zoom]);
    await pg.waitForTimeout(4500);
    await pg.locator("#map").screenshot({path:"build/shots/"+name+".png"});
    console.log("wrote "+name);
  };
  await go("13-warm-atlantic","speed", 20,-40,1);
  await go("14-temp-atlantic","temp",  20,-40,1);
  await go("15-temp-gulfstream","temp",36,-60,2.3);
  await go("16-warm-south","speed",   -45,-20,1);
  await b.close();
})();
