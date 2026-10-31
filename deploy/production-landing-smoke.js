async page => {
  const base='https://estagent.duckdns.org',errors=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/');await page.waitForLoadState('networkidle');
  for(const [width,height] of [[1440,1000],[390,844],[320,740]]){
    await page.setViewportSize({width,height});
    for(const locale of ['en','vi']){
      await page.locator('[data-lang='+locale+']').click();
      await page.waitForFunction(lang=>document.documentElement.lang===lang,locale,{polling:100});
      const links=await page.locator('.hero-actions > a').evaluateAll(nodes=>nodes.map(n=>({href:n.getAttribute('href'),text:n.textContent.trim()})));
      if(links.length!==2||links[0].href!=='creator.html'||links[1].href!=='viewer.html')throw Error('Landing must keep exactly Creator and Viewer hero entries');
      const expected=locale==='vi'?['Tạo tour','Xem tour']:['Create tour','View tours'];
      if(!links.every((link,i)=>link.text.includes(expected[i])))throw Error('Entry locale mismatch '+locale);
      if(await page.locator('a[href="/business/create"]').count())throw Error('Standalone Studio CTA remains on landing');
      if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Landing overflow '+width);
      checks.push({width,locale,entries:expected});
    }
    await page.screenshot({path:'/private/tmp/estagent-wave3-viewer-evidence/landing-'+width+'.png'});
  }
  await page.locator('.hero-actions a').nth(0).click();
  if(!page.url().endsWith('/creator.html'))throw Error('Creator route changed');
  await page.locator('#photos').waitFor();
  await page.goto(base+'/');await page.locator('.hero-actions a').nth(1).click();
  if(!page.url().endsWith('/viewer.html'))throw Error('Viewer route changed');
  await page.locator('.library-card').first().waitFor();
  if((await page.request.get(base+'/business/create')).status()!==200)throw Error('Existing Studio route removed');
  if(errors.length)throw Error(errors.join(';'));
  return {pass:true,checks,creatorEntry:true,viewerEntry:true,studioRoutePreserved:true,errors};
}
