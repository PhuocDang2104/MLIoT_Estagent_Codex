async page=>{
 const root='__ROOT__',errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1440,height:1000});
 await page.route('https://estagent.duckdns.org/',route=>route.fulfill({path:root+'/web/index.html',contentType:'text/html'}));
 for(const file of ['app.js','styles.css','assets/panoramas/lythwood-lounge-8k.jpg'])await page.route('**/'+file,route=>route.fulfill({path:root+'/web/'+file}));
 await page.reload();await page.waitForFunction(()=>document.querySelector('#demo-hero').naturalWidth===8192&&!document.querySelector('#hero-panorama').hidden);
 const hash=()=>page.locator('#hero-panorama').evaluate(c=>c.toDataURL());
 const first=await hash();await page.waitForFunction(v=>document.querySelector('#hero-panorama').toDataURL()!==v,first);
 await page.locator('[data-lang=en]').click();await page.locator('#hero-rotation').click();
 const results=[];
 for(const width of [1440,390,320]){
  await page.setViewportSize({width,height:width===1440?1000:844});
  const bounds=await page.locator('#hero-panorama').boundingBox();
  if(bounds.width!==width||bounds.height!==(width===1440?1000:844))throw Error('Viewport coverage '+JSON.stringify(bounds));
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Overflow');
  await page.screenshot({path:'/private/tmp/landing-sharp-'+width+'.png'});results.push({width,bounds});
 }
 if(await page.locator('.hero-actions a').first().getAttribute('href')!=='/demos/zind-house-000')throw Error('Sample link');
 await page.locator('[data-lang=vi]').click();if(!await page.locator('.hero-credit').innerText().then(t=>t.includes('Ảnh minh hoạ')))throw Error('VI credit');
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('#hero-rotation').disabled);
 const still=await hash();await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));if(still!==await hash())throw Error('Reduced motion moved');
 if(errors.length)throw Error(errors.join(';'));
 return {pass:true,source:[8192,4096],rotationChangesPixels:true,reducedMotion:true,sampleLinkUnchanged:true,results,errors};
}
