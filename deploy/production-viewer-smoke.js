async page => {
  const base='https://estagent.duckdns.org',id='f9c9100bf6effa0f141594dd972bed6d';
  const errors=[],checks=[],requests=[];
  const check=(ok,message)=>{if(!ok)throw Error(message);checks.push(message);};
  const checkedWait=async(fn,arg,options={})=>{try{return await page.waitForFunction(fn,arg,{polling:100,...options});}catch(error){throw Error('Viewer wait after '+(checks.at(-1)||'initial load')+': '+error.message);}};
  page.on('pageerror',e=>errors.push(e.message));
  // Actual deployed frontend and API; GET-only, no local route overrides.
  await page.unrouteAll({behavior:'ignoreErrors'});
  await page.route('**/*',route=>{
    const req=route.request(),pathname=req.url().split('?')[0].replace(/^https?:\/\/[^/]+/,'');
    if(!['GET','HEAD'].includes(req.method()))throw Error('Read-only audit blocked '+req.method());
    requests.push(req.method()+' '+pathname);
    return route.continue();
  });
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(base+'/viewer.html?tour='+id);await page.locator('#panorama').waitFor({state:'visible'});await page.locator('[data-lang="en"]').click();
  await checkedWait(()=>document.getAnimations().length===0);
  check(await page.locator('#publish,#save-draft,#attach-audio').count()===0,'Viewer has no Creator edit/publish controls');
  const canvas=page.locator('#panorama');
  const pixels=()=>canvas.evaluate(c=>c.toDataURL());
  for(let i=0;i<4;i++){
    await page.locator('#viewer-stops summary').click();await page.locator('#scene-nav button').nth(i).click();
    await page.locator('#viewer-stops .panel-close').click();await checkedWait(()=>!document.querySelector('#panorama').hidden&&document.querySelector('#stage').ariaBusy!=='true'&&document.getAnimations().length===0);
    check((await page.locator('#coverage').textContent()).includes('240°'),'Scene '+i+' preserves 240°');
    check((await page.locator('#projection-label').textContent()).includes('provisional'),'Scene '+i+' provisional label');
  }
  const before=await pixels();await page.mouse.move(700,420);await page.mouse.down();await page.mouse.move(850,450,{steps:8});await page.mouse.up();
  check(before!==await pixels(),'Drag changes rendered camera');
  const dragged=await pixels();await page.locator('#zoom-in').click();check(dragged!==await pixels(),'Zoom changes rendered camera');
  await canvas.focus();const keyBefore=await pixels();await page.keyboard.press('ArrowLeft');check(keyBefore!==await pixels(),'Keyboard camera navigation');
  check(!await page.locator('#viewer-chat').isVisible(),'Keyless production hides AI chat');
  check(!await page.locator('#viewer-audio').isVisible(),'Empty audio panel hidden');
  await page.locator('#viewer-info summary').click();
  await page.keyboard.press('Escape');check(!await page.locator('#viewer-info').evaluate(e=>e.open),'Escape closes panel');
  check(await page.evaluate(()=>document.activeElement===document.querySelector('#viewer-info summary')),'Escape restores focus');
  await page.locator('#reset-view').click();await page.locator('#fullscreen').click();await checkedWait(()=>!!document.fullscreenElement);
  check(await page.evaluate(()=>document.fullscreenElement.id==='tour-view'),'Gesture fullscreen includes controls');
  await page.keyboard.press('Escape');await checkedWait(()=>!document.fullscreenElement);check(true,'Escape exits fullscreen');
  check(await page.locator('body').evaluate(b=>b.classList.contains('is-immersive')),'Exiting API fullscreen retains viewport layout');
  await page.locator('#previous').click();await checkedWait(()=>document.querySelector('#scene-counter').textContent==='3 / 4');
  await page.locator('#next').click();await checkedWait(()=>document.querySelector('#scene-counter').textContent==='4 / 4');
  const sizes=[];
  for(const [width,height] of [[1440,1000],[390,844],[320,740]]){
    await page.setViewportSize({width,height});await checkedWait(()=>document.querySelector('#stage').ariaBusy!=='true'&&document.getAnimations().length===0);
    const size=await page.evaluate(()=>{const r=document.querySelector('#stage').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight,iw:innerWidth,ih:innerHeight};});sizes.push(size);
    check(size.x===0&&size.y===0&&size.w===width&&size.h===height,'Stage fills '+width+' viewport');
    check(size.sw===width&&size.sh===height,'No page overflow '+width);
    check(await page.evaluate(()=>document.elementFromPoint(innerWidth/2,innerHeight*.45).id==='panorama'),'Center remains draggable '+width);
    await page.screenshot({path:'/private/tmp/estagent-demo-ux-production/after-'+width+'.png'});
    for(const id of ['viewer-info','viewer-stops']){
      await page.locator('#'+id+' summary').click();
      const box=await page.locator('#'+id+' .panel-body').boundingBox();check(box.x>=0&&box.y>=0&&box.x+box.width<=width+.5&&box.y+box.height<=height,'Panel fits '+id+' '+width);
      await page.locator('#'+id+' .panel-close').click();
    }
    if(width===390){await page.locator('[data-lang="vi"]').click();await page.locator('#viewer-info summary').click();await page.screenshot({path:'/private/tmp/estagent-demo-ux-production/details-vi-390.png'});await page.locator('#viewer-info .panel-close').click();await page.locator('[data-lang="en"]').click();}
  }
  await page.emulateMedia({reducedMotion:'reduce'});await page.locator('#previous').click();await checkedWait(()=>!document.querySelector('#panorama').hidden);check(await page.evaluate(()=>document.getAnimations().length===0),'Reduced motion disables scene transition');
  await page.locator('.viewer-back').click();await page.locator('.library-card').first().waitFor();check(!await page.locator('body').evaluate(b=>b.classList.contains('is-immersive')),'Library keeps document layout');
  await page.screenshot({path:'/private/tmp/estagent-demo-ux-production/library-320.png'});
  await page.locator('.library-card[href*="viewer.html?tour="]').first().click();await page.locator('#tour-view').waitFor();check(await page.locator('body').evaluate(b=>b.classList.contains('is-immersive')),'Library opens immersive viewer');
  check(errors.length===0,'No JS errors');
  return {pass:true,source:'actual deployed frontend + API over TLS; GET-only, no local overrides',sizes,checks,errors,methods:[...new Set(requests.map(s=>s.split(' ')[0]))]};
}
