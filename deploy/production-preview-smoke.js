async page => {
  const base='https://estagent.duckdns.org';
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/');
  await page.waitForLoadState('networkidle');
  await page.locator('[data-lang=vi]').click();
  await page.waitForFunction(()=>document.documentElement.lang==='vi');
  await page.goto(base+'/creator.html');
  await page.waitForFunction(()=>document.querySelector('#connection')?.textContent.includes('AI'));
  await page.evaluate(async()=>{
    const transfer=new DataTransfer();
    for(let i=0;i<2;i++){
      const canvas=document.createElement('canvas');canvas.width=64;canvas.height=32;
      const context=canvas.getContext('2d');context.fillStyle=i?'#b7d1c7':'#dec197';context.fillRect(0,0,64,32);
      context.fillStyle='#263b4d';context.fillRect(i?20:5,5,12,20);
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/png'));
      transfer.items.add(new File([blob],`deployment-synthetic-${i}.png`,{type:'image/png'}));
    }
    const input=document.querySelector('#photos');input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
  });
  await page.locator('#message').fill('Synthetic deployment smoke only; not a real property.');
  const missing=page.waitForResponse(r=>r.url().endsWith('/chat')&&r.request().method()==='POST');
  await page.locator('#send').click();
  if((await missing).status()!==503)throw Error('Expected explicit keyless AI response');
  await page.waitForFunction(()=>!document.querySelector('#send').disabled);
  if(await page.locator('.scene-card').count()!==2)throw Error('Production upload/draft failed');
  await page.locator('#tour-title').fill('Unpublished deployment QA — synthetic');
  const saved=page.waitForResponse(r=>r.request().method()==='PUT'&&r.url().includes('/drafts/'));
  await page.locator('#save-draft').click();
  if((await saved).status()!==200)throw Error('Save failed');
  await page.waitForFunction(()=>!document.querySelector('#save-draft').disabled);
  const preview=await page.locator('#preview').getAttribute('href');
  await page.reload();await page.locator('.scene-card').nth(1).waitFor();
  if(await page.locator('#tour-title').inputValue()!=='Unpublished deployment QA — synthetic')throw Error('Reload lost draft');
  await page.goto(base+preview);await page.waitForLoadState('networkidle');
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});
    if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Overflow '+width);
  }
  if(errors.length)throw Error(errors.join(';'));
  // Do not publish QA media into the public tour library.
  return {pass:true,origin:base,pages:['landing','Creator','private preview'],
    upload:'two synthetic PNGs',persistence:'reload verified',locale:'VI',
    mobile:[390,320],ai:'explicit 503, no paid calls',published:false};
}
