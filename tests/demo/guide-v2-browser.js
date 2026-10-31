async page=>{
 const base='__BASE__',errors=[];page.on('pageerror',e=>errors.push(e.message));await page.emulateMedia({reducedMotion:'no-preference'});await page.setViewportSize({width:1440,height:1000});
 await page.goto(base+'/demos/zind-house-000');await page.waitForFunction(()=>document.querySelectorAll('.checkpoint').length===16,null,{timeout:15000});
 const tracks=await (await page.request.get(base+'/api/demos/zind-house-000/guide')).json();
 if(tracks.length!==32||new Set(tracks.filter(t=>t.narration_version===2).map(t=>t.room_id)).size!==8||new Set(tracks.filter(t=>t.narration_version===1).map(t=>t.room_id)).size!==7)throw Error('Wrong v2/v1 room mapping');
 if(tracks.some(t=>t.description_version!==2))throw Error('Not all descriptions v2');
 const panel=page.locator('#demo-guide'),audio=panel.locator('audio'),results=[];
 for(const locale of ['vi','en']){
  await panel.locator('select').selectOption(locale);await panel.locator('[data-action=play]').click();await page.waitForFunction(()=>document.querySelector('#demo-guide audio').currentTime>.2,null,{timeout:10000});
  const track=tracks.find(t=>t.capture_id==='pano_15'&&t.locale===locale);const duration=await audio.evaluate(a=>a.duration);
  if(Math.abs(duration-track.duration_seconds)>.01||duration<19)throw Error('Wrong detailed live audio duration');
  if(await panel.locator('.guide-description').textContent()!==track.description||await panel.locator('.guide-script').textContent()!==track.script)throw Error('Description/transcript mismatch');
  await page.waitForFunction(()=>document.querySelector('#captures button.active')?.dataset.id==='pano_29'&&!document.querySelector('#demo-guide audio').paused,null,{timeout:35000,polling:100});
  const aux=tracks.find(t=>t.capture_id==='pano_29'&&t.locale===locale);if(aux.description===aux.script)throw Error('Auxiliary description incorrectly treated as old transcript');
  if(await panel.locator('.guide-script').textContent()!==aux.script||await panel.locator('.guide-description').textContent()!==aux.description)throw Error('Retained v1 script incorrect');
  await panel.locator('[data-action=pause]').click();results.push({locale,duration,natural_ended_next:true,retained_v1_script_separate:true});
 }
 await page.locator('#rooms button').nth(2).click();if(await panel.locator('.guide-script').textContent()||await audio.getAttribute('src'))throw Error('Manual navigation kept stale speech');
 if(!(await panel.locator('.guide-description').textContent()).includes('Play tour'))throw Error('Manual stale description');
 for(const [width,height] of [[1440,1000],[390,844],[320,740]]){await page.setViewportSize({width,height});if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Overflow '+width);await page.screenshot({path:'/private/tmp/estagent-house-evidence/guide-v2-'+width+'.png'});}
 if(errors.length)throw Error(errors.join(';'));return {pass:true,base,content_version:2,rooms_description:15,rooms_new_audio:8,rooms_retained_audio:7,actual_audio:results,manual_stale_content_cleared:true,viewports:[1440,390,320],errors};
}
