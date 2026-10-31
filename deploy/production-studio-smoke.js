async page => {
  const base='https://estagent.duckdns.org',errors=[],writes=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{const request=route.request();if(!['GET','HEAD'].includes(request.method())){writes.push(request.url());return route.abort();}return route.continue();});
  await page.goto(base+'/business/create');
  await page.waitForFunction(()=>document.querySelector('#connection')?.textContent.length);
  const session=await page.evaluate(async()=>(await fetch('/api/tours/session')).json());
  if(session.configured)throw Error('Expected keyless production for this release');
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});
    if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Creator overflow '+width);
    if(!await page.locator('#message').isVisible()||!await page.locator('#drop-zone').isVisible())throw Error('Creation inputs unavailable');
    const text=await page.locator('body').innerText();
    if(/OPENAI_API_KEY|Open AI Generation Studio|No file chosen/.test(text))throw Error('Technical or duplicate creation copy leaked');
    await page.screenshot({path:'/private/tmp/estagent-demo-ux-production/creator-'+width+'.png',fullPage:true});
  }
  await page.goto(base+'/studio.html');await page.locator('#message').waitFor();
  if(page.url()!==base+'/business/create')throw Error('Old Studio entry does not converge');
  await page.goto(base+'/creator.html?new=1');await page.locator('#message').waitFor();
  if(page.url()!==base+'/business/create?new=1')throw Error('Creator compatibility link lost state');
  if(errors.length||writes.length)throw Error(JSON.stringify({errors,writes}));
  return {pass:true,keyless:true,canonicalCreator:true,mobile:[390,320],productionWrites:0,pageErrors:errors};
}
