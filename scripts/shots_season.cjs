/* Visual check for the seasonal and coverage layers: the same view in January
   and July, and the same view coloured by coverage instead of speed. */
const { chromium } = require("playwright");
const path=require("path"), fs=require("fs");
const HARNESS='window.__oly=()=>({st,setMode,setCam,OC,CAM,hideEx,ocSetMonth,sync,NMON,flowNote,drawMap});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
(async()=>{
  const raw=fs.readFileSync(process.argv[2],"utf8");
  const p=path.join("build/shots","ss.html");
  fs.writeFileSync(p, raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>"));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage({viewport:{width:1400,height:900},deviceScaleFactor:1.5});
  await pg.goto("file://"+path.resolve(p),{waitUntil:"load",timeout:120000});
  await pg.waitForFunction("window.__oly().OC && window.__oly().OC.sok",null,{timeout:120000});
  await pg.waitForTimeout(4000);
  const go = async (name, mon, col, lat, lon, zoom) => {
    await pg.evaluate(([mon,col,lat,lon,zoom])=>{
      const A=window.__oly();
      A.setMode("GLOBE"); A.setCam(lat,lon);
      A.CAM.zoom=zoom; A.CAM.zTarget=zoom; A.CAM.auto=false;
      A.st.flowCol=col; A.st.flowSeason=true;
      A.OC.budgetOff=true; A.OC.nPart=Math.round(A.OC.P*0.95);
      for(let k=A.NMON-1;k>0;k--){ A.st.t=k; A.ocSetMonth(); if(Math.floor(A.OC.mon)===mon-1) break; }
      A.sync(); A.flowNote(); A.hideEx();
    },[mon,col,lat,lon,zoom]);
    await pg.waitForTimeout(4000);
    await pg.locator("#map").screenshot({path:"build/shots/"+name+".png"});
    console.log("wrote "+name);
  };
  // the monsoon reversal, same view, two seasons
  await go("10-indian-jan", 1, "speed",  8, 65, 1.9);
  await go("10-indian-jul", 7, "speed",  8, 65, 1.9);
  // coverage: where the ocean has actually been sampled
  await go("11-coverage-global", 7, "dens", 10, -30, 1);
  await go("12-coverage-south",  7, "dens", -55, 20, 1);
  await b.close();
})();
