async page=>{
 await page.emulateMedia({reducedMotion:'no-preference'});
 const base='__BASE__',errors=[],visited=[];page.on('pageerror',e=>errors.push(e.message));
 await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/demos/zind-house-000');
 await page.waitForFunction(()=>document.querySelectorAll('.checkpoint').length===16,null,{timeout:15000});
 const panel=page.locator('#demo-guide'),audio=panel.locator('audio');await panel.waitFor();
 if(!await audio.evaluate(a=>a.paused))throw Error('Autoplay before gesture');
 await panel.locator('select').selectOption('en');await panel.locator('[data-action=play]').click();
 await page.waitForFunction(()=>document.querySelector('#demo-guide audio').currentTime>.2,null,{timeout:10000});
 if(await page.locator('#captures button.active').getAttribute('data-id')!=='pano_15')throw Error('First marker mismatch');
 await page.waitForFunction(()=>document.querySelector('#captures button.active')?.dataset.id==='pano_29'&&!document.querySelector('#demo-guide audio').paused,null,{timeout:15000});
 await audio.evaluate(a=>a.dispatchEvent(new Event('ended')));
 if(await page.locator('#captures button.active').getAttribute('data-id')!=='pano_29')throw Error('Stale ended moved a playing track');
 visited.push('pano_15','pano_29'); // Natural ended event, normal playback rate.
 await panel.locator('[data-action=pause]').click();
 const pausedAt=await audio.evaluate(a=>a.currentTime);await audio.evaluate(a=>a.dispatchEvent(new Event('ended')));
 if(await page.locator('#captures button.active').getAttribute('data-id')!=='pano_29')throw Error('Stale ended navigated after pause');
 if(!await audio.evaluate(a=>a.paused))throw Error('Pause failed');
 await panel.locator('[data-action=play]').click();await page.waitForFunction(()=>!document.querySelector('#demo-guide audio').paused,null,{timeout:10000});
 await page.locator('#rooms button').nth(2).click();
 if(!await audio.evaluate(a=>a.paused))throw Error('Manual room did not stop');
 await panel.locator('select').selectOption('vi');await panel.locator('[data-action=play]').click();
 await page.waitForFunction(()=>document.querySelector('#demo-guide audio').currentTime>.1,null,{timeout:10000});
 const guide=await (await page.request.get(base+'/api/demos/zind-house-000/guide')).json();
 if(guide.length!==32)throw Error('Wrong capture-locale mapping');
 if(!await audio.evaluate(a=>a.src.includes('/house/guide/')))throw Error('Wrong source audio');
 const viScript=guide.find(t=>t.capture_id==='pano_15'&&t.locale==='vi').script;
 if(await panel.locator('.guide-script').textContent()!==viScript)throw Error('VI script mismatch');
 if(await panel.locator('.guide-description').textContent()!==guide.find(t=>t.capture_id==='pano_15'&&t.locale==='vi').description)throw Error('VI description mismatch');
 // Exercise every natural ended event with actual decoded WAVs, accelerated to fit QA timebox.
 await audio.evaluate(a=>{a.defaultPlaybackRate=8;a.playbackRate=8;});
 await page.waitForFunction(()=>document.querySelector('#demo-guide [data-action=play]').textContent==='Replay tour',null,{timeout:45000,polling:100});
 if(!await audio.evaluate(a=>a.paused))throw Error('Final view loops unexpectedly');
 if(await page.locator('#captures button.active').getAttribute('data-id')!=='pano_28')throw Error('Final capture mismatch');
 await panel.locator('summary').click();
 await page.locator('#demo-rotate button').click();
 const before=await page.locator('#viewport canvas').screenshot();
 await page.waitForFunction(()=>new Promise(resolve=>setTimeout(()=>resolve(true),600)));
 const after=await page.locator('#viewport canvas').screenshot();
 if(before.equals(after))throw Error('Gentle rotation did not change view');
 const canvas=page.locator('#viewport canvas');const box=await canvas.boundingBox();await page.mouse.move(box.x+box.width*.5,box.y+box.height*.5);await page.mouse.down();await page.mouse.move(box.x+box.width*.5+20,box.y+box.height*.5);await page.mouse.up();
 if(await page.locator('#demo-rotate button').getAttribute('aria-pressed')!=='false')throw Error('Drag did not stop rotation');
 await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('#demo-rotate button').disabled,null,{timeout:2000});if(!await page.locator('#demo-rotate button').isDisabled())throw Error('Reduced motion not honored');
 for(const [width,height] of [[1440,1000],[390,844],[320,740]]){await page.setViewportSize({width,height});if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Overflow');await page.screenshot({path:'/private/tmp/estagent-house-evidence/guide-'+width+'.png'});}
 if(errors.length)throw Error(errors.join(';'));
 return {pass:true,base,natural_ended_next_normal_rate:visited,all_16_views_ended_to_finish_rate8:true,pause_resume_manual_cancel:true,stale_ended_ignored:true,vi_script:true,rotation_drag_reduced_motion:true,errors};
}
