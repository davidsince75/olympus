const { chromium } = require("playwright");
const path=require("path");
(async()=>{
  const b=await chromium.launch({executablePath:"/opt/pw-browsers/chromium"});
  const pg=await b.newPage({viewport:{width:420,height:820}});
  await pg.goto("file://"+path.resolve(process.argv[2]),{waitUntil:"load",timeout:120000});
  await pg.waitForTimeout(6000);
  console.log(await pg.evaluate(()=>{
    const iw=document.documentElement.clientWidth, out=[];
    document.querySelectorAll("*").forEach(el=>{
      const r=el.getBoundingClientRect();
      if(r.right>iw+1 && r.width>0)
        out.push({tag:el.tagName.toLowerCase(), id:el.id, cls:(el.className&&el.className.toString().slice(0,40)),
                  right:Math.round(r.right), w:Math.round(r.width), left:Math.round(r.left)});
    });
    return JSON.stringify({innerWidth:iw, scrollWidth:document.documentElement.scrollWidth, offenders:out.slice(0,12)},null,1);
  }));
  await b.close();
})();
