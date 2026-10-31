async page => {
  const base='https://estagent.duckdns.org',errors=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>{if(!['GET','HEAD'].includes(route.request().method()))throw Error('Read-only production audit');return route.continue();});
  await page.goto(base+'/');await page.waitForLoadState('networkidle');
  for(const [width,height] of [[1440,1000],[390,844],[320,740]]){
    await page.setViewportSize({width,height});
    for(const locale of ['en','vi']){
      await page.locator('[data-lang='+locale+']').click();
      const links=await page.locator('.hero-actions > a').evaluateAll(nodes=>nodes.map(n=>n.getAttribute('href')));
      if(JSON.stringify(links)!==JSON.stringify(['/demos/zind-house-000','/business/create']))throw Error('Sample-home/canonical Creator links mismatch');
      if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Landing overflow '+width);
      checks.push({width,locale});
    }
    await page.screenshot({path:'/private/tmp/estagent-demo-ux-production/landing-'+width+'.png'});
  }
  await page.locator('.hero-actions a').nth(1).click();await page.locator('#photos').waitFor({state:'attached'});
  if(page.url()!==base+'/business/create')throw Error('Canonical Creator route mismatch');
  await page.goto(base+'/viewer.html');await page.locator('.library-card').first().waitFor();
  if(errors.length)throw Error(errors.join(';'));
  return {pass:true,checks,canonicalCreator:true,viewerLibrary:true,productionWrites:0,errors};
}
