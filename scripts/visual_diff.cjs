/* Does the cached living layer draw the same picture as the per-frame one?
   Renders the same disc from both files and compares pixels. */
const { chromium } = require("playwright");
const path=require("path"), fs=require("fs");
const HARNESS='window.__oly=()=>({st,setMode,setCam,drawMap});\n';
const ANCHOR="\nrequestAnimationFrame(frame);\n})();\n</script>";
async function shot(file,tag,mode){
  const raw=fs.readFileSync(file,"utf8");
  const p=path.join("build/shots","vd_"+tag+".html");
  fs.writeFileSync(p, raw.replace(ANCHOR,"\nrequestAnimationFrame(frame);\n"+HARNESS+"})();\n</script>"));
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage({viewport:{width:1100,height:900},deviceScaleFactor:1});
  await pg.goto("file://"+path.resolve(p),{waitUntil:"load",timeout:120000});
  await pg.waitForFunction("window.__oly",null,{timeout:60000});
  await pg.waitForTimeout(6000);
  await pg.evaluate((m)=>{ const A=window.__oly();
    for(const k in A.st.lay) A.st.lay[k]=true;
    A.st.lay.flow=false; A.st.lay.fronts=false; A.st.lay.deep=false;  // isolate the living layer
    A.st.lay.track=false; A.st.lay.vel=false; A.st.lay.argo=false;    // these animate
    A.setMode(m); A.drawMap();
  }, mode);
  await pg.waitForTimeout(1200);
  const out=path.join("build/shots","vd_"+tag+"_"+mode+".png");
  await pg.locator("#map").screenshot({path:out});
  await b.close();
  return out;
}
(async()=>{
  for(const mode of ["S","N"]){
    const a=await shot(process.argv[2],"before",mode);
    const c=await shot(process.argv[3],"after",mode);
    const {execSync}=require("child_process");
    execSync(`python3 - <<'PY'
from PIL import Image
import numpy as np
a=np.asarray(Image.open("${a}").convert("RGB"),float)
b=np.asarray(Image.open("${c}").convert("RGB"),float)
if a.shape!=b.shape: print("${mode}: SIZE MISMATCH",a.shape,b.shape); raise SystemExit
d=np.abs(a-b)
print(f"${mode}  mean abs diff {d.mean():.3f}/255   max {d.max():.0f}   pixels >8: {(d.max(2)>8).sum()} of {d.shape[0]*d.shape[1]} ({(d.max(2)>8).mean()*100:.2f}%)")
Image.fromarray((np.clip(d.max(2)*6,0,255)).astype('uint8')).save("build/shots/vd_diff_${mode}.png")
PY`,{stdio:"inherit"});
  }
})();
