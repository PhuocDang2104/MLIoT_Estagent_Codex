async page => {
  const base='__BASE_URL__',errors=[],turns=[];const check=(ok,msg)=>{if(!ok)throw Error(msg);};
  page.on('pageerror',e=>errors.push(e.message));
  page.on('request',r=>{if(r.url().endsWith('/chat'))turns.push(r.postDataJSON());});
  await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/business/create?new=1');
  await page.waitForFunction(()=>document.querySelector('#connection')?.textContent==='AI assistant available');
  await page.locator('#content-locale').selectOption('en');
  await page.locator('#message').fill('Rename the first scene Lobby and reverse the order.');
  await page.locator('#photos').setInputFiles(['__IMAGE_ONE__','__IMAGE_TWO__']);
  await page.locator('#send').click();
  await page.waitForFunction(()=>document.querySelector('#messages')?.textContent.includes('Test provider fixture'));
  await page.waitForFunction(()=>!document.querySelector('#send').disabled);
  check(turns.length===1,'Configured creation did not submit one assistant turn');
  check((await page.locator('.scene-fields input').evaluateAll(es=>es.map(e=>e.value))).includes('Lobby'),'AI edit not visible in draft');
  check(await page.locator('#message').inputValue()==='','Successful assistant turn not cleared');
  await page.locator('[data-lang="vi"]').click();
  await page.locator('#message').fill('Rename the first scene Lobby and reverse the order.');
  const reply=page.waitForResponse(r=>r.url().endsWith('/chat'));await page.locator('#send').click();check((await reply).status()===200,'Assistant followup failed');
  await page.waitForFunction(()=>!document.querySelector('#send').disabled);
  check(turns[1].locale==='en','Interface language changed AI source language');
  check((await page.locator('#messages .assistant').count())>=2,'Assistant history lost');
  check(!errors.length,'JS errors '+errors.join('; '));
  return {pass:true,configuredAssistant:true,provider:'injected finite test interpreter, zero OpenAI calls',visibleEdits:true,history:true,sourceLocalePreserved:true,errors};
}
