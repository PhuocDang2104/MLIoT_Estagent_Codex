async page=>{
  const base='__BASE__',check=(value,message)=>{if(!value)throw new Error(message);};
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.context().route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
  await page.context().addCookies([{name:'estagent_tours',value:'__COOKIE__',url:base+'/api/tours/',httpOnly:true,sameSite:'Strict'}]);
  await page.setViewportSize({width:1100,height:900});
  await page.goto(base+'/export.html?tour=__TOUR__');await page.locator('#preview').waitFor();
  check(await page.locator('.scene').count()===2,'Wrong snapshot scenes');
  const results=[];
  for(const aspect of ['portrait','landscape']){
    await page.locator(`input[value="${aspect}"]`).check();
    await page.waitForFunction(aspect=>document.querySelector('.scene')?.classList.contains(aspect),aspect);
    const created=page.waitForResponse(r=>r.url()===base+'/api/tours/exports'&&r.request().method()==='POST');
    await page.locator('#create').click();const response=await created;check(response.status()===200,'Export admission failed');
    const job=await response.json();
    check((await page.request.get(base+'/__qa/wait',{timeout:240000})).ok(),'Actual renderer did not finish');
    await page.locator('#refresh').click();await page.locator('#video').waitFor();
    await page.locator('#video').evaluate(video=>video.play());
    await page.waitForFunction(()=>document.querySelector('#video').currentTime>.5);
    const media=await page.locator('#video').evaluate(video=>({width:video.videoWidth,height:video.videoHeight,duration:video.duration,currentTime:video.currentTime,readyState:video.readyState}));
    check(media.width===(aspect==='portrait'?720:1280)&&media.height===(aspect==='portrait'?1280:720),'Video dimensions wrong');
    check(Math.abs(media.duration-6)<.3,'Video duration wrong');
    await page.locator('#video').evaluate(video=>video.pause());
    await page.locator('#video').screenshot({path:`tests/exports/evidence/${aspect}-playback.png`});
    check((await page.request.get(base+'/api/tours/exports/'+job.id+'/download',{headers:{Range:'bytes=0-99'}})).status()===206,'Private MP4 Range download failed');
    results.push({aspect,...media,actualPlayback:true});
  }
  await page.setViewportSize({width:390,height:844});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Export UI overflows mobile');
  await page.screenshot({path:'tests/exports/evidence/export-mobile.png',fullPage:true});
  const anonymous=await page.context().browser().newContext();
  const denied=await anonymous.request.get(base+'/api/tours/exports/sources');check(denied.status()===401,'Anonymous exports visible');await anonymous.close();
  check(errors.length===0,'Page errors: '+errors.join(';'));
  return {pass:true,source:'owned synthetic published snapshot',browser:results,anonymousDenied:true,errors};
}
