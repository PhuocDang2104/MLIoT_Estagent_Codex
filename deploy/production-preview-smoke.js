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
  // Synthetic PCM tone only; keep this draft private and exercise MinIO-backed audio UI.
  await page.evaluate(()=>{
    const rate=16000,frames=rate*2,buffer=new ArrayBuffer(44+frames*2),view=new DataView(buffer);
    const text=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};
    text(0,'RIFF');view.setUint32(4,36+frames*2,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);
    view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);
    view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,frames*2,true);
    for(let i=0;i<frames;i++)view.setInt16(44+i*2,Math.round(1200*Math.sin(2*Math.PI*440*i/rate)),true);
    const transfer=new DataTransfer();transfer.items.add(new File([buffer],'deployment-synthetic-tone.wav',{type:'audio/wav'}));
    const input=document.querySelector('#audio-file');input.files=transfer.files;input.dispatchEvent(new Event('change',{bubbles:true}));
  });
  await page.locator('#audio-source').fill('Synthetic PCM tone');
  await page.locator('#audio-rights-note').fill('Generated test tone; no human narration or copyrighted music.');
  const attached=page.waitForResponse(r=>r.request().method()==='PUT'&&r.url().endsWith('/audio'));
  await page.locator('#attach-audio').click();
  if((await attached).status()!==200)throw Error('Private audio attach failed');
  await page.waitForFunction(()=>!document.querySelector('#attach-audio').disabled);
  const preview=await page.locator('#preview').getAttribute('href');
  await page.reload();await page.locator('.scene-card').nth(1).waitFor();
  if(await page.locator('#tour-title').inputValue()!=='Unpublished deployment QA — synthetic')throw Error('Reload lost draft');
  await page.goto(base+preview);await page.waitForLoadState('networkidle');
  if(await page.locator('#viewer-chat').isVisible())throw Error('Private preview exposes published chat');
  await page.locator('#viewer-audio summary').click();await page.locator('#play').click();
  await page.waitForFunction(()=>document.querySelector('#narration-track').currentTime>.15);
  await page.locator('#pause').click();
  if(!await page.locator('#narration-track').evaluate(a=>a.paused&&a.duration===2))throw Error('WAV decode/pause failed');
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});
    if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Overflow '+width);
  }
  if(errors.length)throw Error(errors.join(';'));
  // Do not publish QA media into the public tour library.
  return {pass:true,origin:base,pages:['landing','Creator','private preview'],
    upload:'two synthetic PNGs + private synthetic PCM WAV',audio:'actual decode/play/pause',persistence:'reload verified',locale:'VI',
    mobile:[390,320],ai:'explicit 503, no paid calls',published:false};
}
