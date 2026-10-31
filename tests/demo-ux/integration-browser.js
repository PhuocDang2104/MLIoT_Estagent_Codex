async page => {
  const base='__BASE_URL__',evidence='__EVIDENCE_DIR__',errors=[],writes=[];
  const check=(ok,message)=>{if(!ok)throw Error(message);};
  page.on('pageerror',error=>errors.push(error.message));
  await page.context().route('**/*',route=>{
    const request=route.request();
    if(!request.url().startsWith(base+'/'))return route.abort();
    if(!['GET','HEAD'].includes(request.method()))writes.push(request.url().slice(base.length).split('?')[0]);
    return route.continue();
  });
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(base+'/business/create');
  await page.waitForFunction(()=>document.querySelector('#connection')?.textContent.length);
  await page.locator('[data-lang="vi"]').click();
  check(await page.locator('#content-locale').inputValue()==='vi','Content language must be visible and default VI');
  const description='Căn hộ 2PN Quận 7, hướng Đông Nam. Có ban công thoáng.';
  await page.locator('#message').fill(description);
  await page.locator('#photos').setInputFiles(['__IMAGE_ONE__','__IMAGE_TWO__','__IMAGE_THREE__']);
  check((await page.locator('#photo-count').innerText()).includes('3'),'Attachment count missing');
  const create=page.waitForResponse(r=>r.url().endsWith('/api/tours/drafts')&&r.request().method()==='POST');
  await page.locator('#send').click();let draft=await (await create).json();
  await page.locator('.scene-card').nth(2).waitFor();
  await page.waitForFunction(()=>!document.querySelector('#save-draft').disabled);
  check(draft.title.startsWith('Căn hộ 2PN Quận 7')&&!/My space/.test(draft.title),'Draft title ignored user description');
  check(draft.locale==='vi'&&draft.scenes[0].description===description,'Draft description/locale mismatch');
  check(draft.scenes.every(scene=>!/^Photo \d/.test(scene.name)),'Photo N placeholder remains');
  check(await page.locator('#message').inputValue()==='','Successful text was not cleared');
  check(!await page.locator('.creator-audio').evaluate(el=>el.open),'Advanced audio must start folded');
  check(!await page.locator('#composer').isVisible(),'Keyless creator still invites failed AI chat');
  check(!/OPENAI_API_KEY|No file chosen/.test(await page.locator('body').innerText()),'Technical or contradictory file copy leaked');
  check(await page.locator('#publish').isDisabled()&&(await page.locator('#publish-help').innerText()).length>0,'Publish lacks review explanation');
  const draftURL=page.url();
  await page.locator('[data-lang="en"]').click();
  await page.locator('.scene-card').nth(2).getByRole('button',{name:'Set opening scene',exact:true}).click();
  const save=page.waitForResponse(r=>r.url().endsWith('/api/tours/drafts/'+draft.id)&&r.request().method()==='PUT');
  await page.locator('#save-draft').click();draft=await (await save).json();
  check(draft.locale==='vi','Changing UI language relabeled saved content');
  const opening=draft.scenes.find(scene=>scene.id===draft.start_scene_id);
  const preview=await page.context().newPage();await preview.goto(base+await page.locator('#preview').getAttribute('href'));
  await preview.locator('#scene-title').waitFor();
  check(await preview.locator('#scene-counter').innerText()==='1 / 3','Opening scene was not first in preview');
  check(await preview.locator('#scene-title').innerText()===opening.name,'Preview starts at wrong scene');
  check(!await preview.locator('#viewer-chat').isVisible()&&!await preview.locator('#viewer-audio').isVisible(),'Empty controls shown in preview');
  await preview.close();
  await page.locator('#reviewed').check();
  const publish=page.waitForResponse(r=>r.url().endsWith('/publish')&&r.request().method()==='POST');
  await page.locator('#publish').click();const snapshot=await (await publish).json();
  await page.locator('#published-link a').first().click();await page.locator('#photo').waitFor({state:'visible'});
  await page.waitForFunction(()=>document.querySelector('#photo').complete&&document.querySelector('#photo').naturalWidth>0);
  check(!await page.locator('#viewer-chat').isVisible()&&!await page.locator('#viewer-audio').isVisible(),'Keyless or empty media panels shown');
  check(await page.locator('#scene-counter').innerText()==='1 / 3','Published opening scene not first');
  const sizes=[];
  for(const [width,height] of [[1440,1000],[390,844],[320,740]]){
    await page.setViewportSize({width,height});
    const state=await page.evaluate(()=>{const r=document.querySelector('#stage').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,sw:document.documentElement.scrollWidth,sh:document.documentElement.scrollHeight};});
    check(state.x===0&&state.y===0&&state.w===width&&state.h===height&&state.sw===width&&state.sh===height,'Photo tour is not a single full viewport at '+width);
    sizes.push({width,height,...state});await page.screenshot({path:evidence+'/photo-viewer-'+width+'.png'});
  }
  await page.locator('[data-lang="vi"]').click();await page.locator('[data-lang="en"]').click();
  const immutable=await (await page.request.get(base+'/api/tours/published/'+snapshot.id)).json();
  check(JSON.stringify(immutable)===JSON.stringify(snapshot),'Viewer changed immutable published content');
  await page.goto(draftURL);await page.locator('.scene-card').nth(2).waitFor();
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:900});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Creator overflow '+width);
    await page.screenshot({path:evidence+'/creator-'+width+'.png',fullPage:true});
  }
  await page.locator('#tour-title').fill('Later private edit');
  const changed=page.waitForResponse(r=>r.url().endsWith('/api/tours/drafts/'+draft.id)&&r.request().method()==='PUT');
  await page.locator('#save-draft').click();await changed;
  check(JSON.stringify(await (await page.request.get(base+'/api/tours/published/'+snapshot.id)).json())===JSON.stringify(snapshot),'Later draft edit mutated published snapshot');
  // Existing Studio projects keep their original runtime; no provider request.
  const legacy=await page.evaluate(async()=>{
    await fetch('/api/studio/session');
    const response=await fetch('/api/studio/projects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:'Existing Studio QA',description:'Synthetic saved legacy project',request_id:crypto.randomUUID()})});
    if(!response.ok)throw Error('Legacy project create '+response.status);return response.json();
  });
  await page.goto(base+'/business/projects/'+legacy.id+'/generate');await page.locator('#project-name').waitFor();
  check(await page.locator('#project-name').innerText()==='Existing Studio QA','Existing Studio project route broken');
  await page.goto(base+'/studio.html');await page.locator('#composer').waitFor();
  check(page.url()===base+'/business/create','Duplicate Studio create entry remained');
  await page.goto(base+'/experience.html?new=1');await page.locator('#composer').waitFor();
  check(page.url()===base+'/business/create?new=1','Experience alias dropped state');
  check(!writes.some(path=>path.endsWith('/chat')||path.includes('/narration/jobs')||path.endsWith('/generations')),'Unexpected AI or generation request');
  check(errors.length===0,'JS errors: '+errors.join('; '));
  return {pass:true,source:'actual localhost HTTP + SQLite + synthetic PNG uploads; no AI provider',draftTitle:snapshot.title,sourceLocale:snapshot.locale,openingFirst:true,immutableSnapshot:true,keylessNoChat:true,canonicalCreator:true,legacyStudio:true,sizes,errors};
}
