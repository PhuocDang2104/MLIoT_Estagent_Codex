async page => {
  const base='__BASE_URL__',jobs=[];
  page.on('request',request=>{if(request.method()==='POST'&&request.url().includes('/narration/jobs'))jobs.push(request.url());});
  await page.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
  const config=page.waitForResponse(response=>response.url().endsWith('/narration/config'));
  await page.goto(base+'/qa/narration');
  await page.waitForFunction(()=>!!window.panel);
  if((await config).status()!==200)throw Error('Narration configuration failed');
  if(await page.locator('.narration-panel').isVisible())throw Error('Unavailable narration panel must be hidden');
  if(/OPENAI_API_KEY|Narration unavailable/.test(await page.locator('body').innerText()))throw Error('Operator config leaked');
  if(jobs.length)throw Error('Unavailable narration triggered generation');
  return {pass:true,missing_key:'hidden unavailable panel',generationCalls:0};
}
