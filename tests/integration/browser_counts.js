async page => {
  const base='__BASE_URL__',check=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.goto(base+'/viewer.html');
  const tours=await page.evaluate(async()=>{
    await fetch('/api/tours/session');
    const assets=[];
    for(let i=0;i<5;i++){
      const c=document.createElement('canvas');c.width=100;c.height=80;const ctx=c.getContext('2d');ctx.fillStyle=`hsl(${i*65} 50% 60%)`;ctx.fillRect(0,0,100,80);
      const blob=await new Promise(resolve=>c.toBlob(resolve));
      const r=await fetch('/api/tours/assets',{method:'POST',headers:{'Content-Type':'application/octet-stream'},body:blob});if(!r.ok)throw new Error('Dynamic fixture upload failed');assets.push((await r.json()).id);
    }
    const result=[];
    for(const count of [1,4,5]){
      const r=await fetch('/api/tours/drafts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({asset_ids:assets.slice(0,count),title:`Synthetic ${count} checkpoints`,locale:'en',request_id:crypto.randomUUID()})});if(!r.ok)throw new Error('Dynamic fixture draft failed');result.push({count,doc:await r.json()});
    }
    return result;
  });
  for(const {count,doc} of tours){
    await page.goto(`${base}/viewer.html?draft=${doc.id}`);await page.locator('#scene-title').waitFor();
    check(await page.locator('#scene-nav button').count()===count,`Wrong manifest-driven count ${count}`);
    for(let i=0;i<count;i++){await page.locator('#scene-nav button').nth(i).click();check(await page.locator('#scene-counter').innerText()===`${i+1} / ${count}`,'Scene navigation/count mismatch');check(await page.locator('#scene-title').innerText()===doc.scenes[i].name,'Scene name mismatch');await page.waitForFunction(()=>document.querySelector('#photo').naturalWidth>0);}
    await page.locator('#next').click();check(await page.locator('#scene-counter').innerText()===`1 / ${count}`,'Wrap failed');
  }
  return {pass:true,manifestSceneCounts:[1,4,5],eachSceneNavigable:true,images:'synthetic runtime canvas, actual image decoder and HTTP; no user/demo assets'};
}
