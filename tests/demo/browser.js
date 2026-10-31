async page => {
 const base='__BASE__',errors=[],network=[],checks=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 page.on('response',r=>{if(r.url().includes('/api/demos/'))network.push({url:r.url(),status:r.status()});});
 await page.setViewportSize({width:1440,height:1000});
 await page.goto(base+'/viewer.html');
 const card=page.locator('.library-card').filter({hasText:'NHÀ DEMO'});
 await card.waitFor();await card.click();
 await page.waitForFunction(()=>document.querySelectorAll('.checkpoint').length===16&&document.querySelector('#houseMode')?.classList.contains('active'),null,{polling:100,timeout:25000});
 if(!network.some(r=>r.url.endsWith('dollhouse-studio.glb')&&r.status===200))throw Error('Actual GLB not loaded');
 if(!await page.locator('#demo-cache-label').isVisible())throw Error('Cache provenance label missing');
 if(await page.locator('#rooms button').count()!==15)throw Error('Wrong room count');
 if(await page.locator('#floorplan polygon').count()!==15)throw Error('Missing source floorplan');
 const manifest=await (await page.request.get(base+'/api/demos/zind-house-000/assets/house/manifest.json')).json();
 if(manifest.captures.length!==32||manifest.rooms.reduce((n,r)=>n+r.dollhouseCaptureIds.length,0)!==16)throw Error('Capture/marker mapping changed');
 const shots=[];
 for(const index of [0,6,11]){
  const room=manifest.rooms[index];await page.locator('#rooms button[data-room="'+room.id+'"]').click();
  await page.waitForFunction(()=>document.querySelector('#notice').textContent==='',null,{polling:100,timeout:15000});
  if((await page.locator('#title').textContent())!==room.label)throw Error('Room label mismatch');
  const capture=manifest.captures.find(c=>c.id===room.primaryId);
  if(!network.some(r=>r.url.endsWith(capture.url)&&r.status===200))throw Error('Source panorama not loaded');
  shots.push((await page.locator('#viewport canvas').screenshot()).toString('base64'));
  checks.push('actual room '+room.id+' capture '+capture.id);
 }
 if(new Set(shots).size!==3)throw Error('Room changes did not change rendered panorama');
 await page.locator('#houseMode').click();
 await page.waitForFunction(()=>!document.querySelector('#checkpoints').hidden,null,{polling:100});
 const marker=page.locator('.checkpoint:visible').first();await marker.click();
 await page.waitForFunction(()=>document.querySelector('#panoMode').classList.contains('active')&&document.querySelector('#notice').textContent==='',null,{polling:100,timeout:10000});
 checks.push('real GLB marker opens source panorama');
 await page.locator('#floorplan polygon').nth(2).click();
 await page.waitForFunction(()=>document.querySelector('#notice').textContent==='',null,{polling:100,timeout:10000});
 checks.push('source map polygon changes room');
 for(const [width,height] of [[1440,1000],[390,844],[320,740]]){
  await page.setViewportSize({width,height});
  await page.waitForFunction(()=>document.querySelector('#notice').textContent==='',null,{timeout:10000});
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight))throw Error('Overflow '+width);
  const box=await page.locator('#viewport canvas').boundingBox();if(box.width<width*.7||box.height<height*.7)throw Error('Viewer not immersive '+width);
  await page.screenshot({path:'/private/tmp/estagent-house-evidence/panorama-'+width+'.png'});
  await page.locator('#houseMode').click();await page.screenshot({path:'/private/tmp/estagent-house-evidence/model-'+width+'.png'});
  await page.locator('#panoMode').click();checks.push('viewport '+width);
 }
 if(errors.length)throw Error('Browser errors: '+errors.join(';'));
 if(network.some(r=>r.status>=400))throw Error('Demo asset failed');
 return {pass:true,base,glbLoaded:true,rooms:15,captures:32,markers:16,threeDistinctPanoramas:true,checks,source:'user-provided cached model and captures, not newly reconstructed',errors};
}
