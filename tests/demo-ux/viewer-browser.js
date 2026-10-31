async page => {
  const base='http://127.0.0.1:5277',errors=[];await page.unroute(base+'/api/tours/**');await page.goto('about:blank');
  const check=(value,message)=>{if(!value)throw Error(message);};
  page.on('pageerror',error=>errors.push(error.message));
  const image=await page.evaluate(()=>{const canvas=document.createElement('canvas');canvas.width=1600;canvas.height=400;const ctx=canvas.getContext('2d');ctx.fillStyle='#efb45a';ctx.fillRect(0,0,1600,400);return canvas.toDataURL('image/png');});
  let configured=false,withAudio=false,chatError=false,englishAudio=false;
  const scene=(id,projection,coverage)=>({id,asset_id:id,name:`Điểm ${id}`,description:`Mô tả gốc ${id}`,projection,coverage_degrees:coverage,coverage_source:projection==='photo'?'unknown':'user_provisional',image_url:image,thumbnail_url:image});
  const track={url:base+'/tone.wav',duration_seconds:8,source_label:'Synthetic tone',rights:'owned',rights_note:'Generated test tone, not narration.'};
  const manifest=()=>({id:'demo',revision:1,status:'published',title:'Căn hộ mẫu',locale:'vi',start_scene_id:'s2',scenes:[scene('s1','cylindrical',240),scene('s2','photo',null),scene('s3','cylindrical',30)],audio:{status:withAudio?'ready':'unavailable',source:withAudio?'user_uploaded':'none',music:null,narration:withAudio?[{scene_id:'s2',locale:'vi',track,transcript:'Bản kiểm thử âm thanh.'},...(englishAudio?[{scene_id:'s2',locale:'en',track:{...track,generation:{provider:'fixture'}},transcript:'Synthetic audio test.'}]:[])]:null}});
  await page.route(base+'/api/tours/**',async route=>{
    const path=route.request().url().split('?')[0];
    if(path.endsWith('/session'))return route.fulfill({json:{configured,drafts:[]}});
    if(path.endsWith('/chat'))return route.fulfill(chatError?{status:503,json:{detail:'OPENAI_API_KEY internal error'}}:{json:{reply:'Thông tin từ mô tả đã duyệt.'}});
    return route.fulfill({json:manifest()});
  });
  track.url=await page.evaluate(()=>{
    const bytes=new Uint8Array(44+16000*2*8),v=new DataView(bytes.buffer);
    const text=(offset,s)=>{for(let i=0;i<s.length;i++)bytes[offset+i]=s.charCodeAt(i);};
    text(0,'RIFF');v.setUint32(4,bytes.length-8,true);text(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,16000,true);v.setUint32(28,32000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);text(36,'data');v.setUint32(40,bytes.length-44,true);
    for(let n=0;n<16000*8;n++)v.setInt16(44+n*2,Math.round(700*Math.sin(2*Math.PI*440*n/16000)),true);
    let textBytes='';for(const byte of bytes)textBytes+=String.fromCharCode(byte);return 'data:audio/wav;base64,'+btoa(textBytes);
  });
  await page.setViewportSize({width:1440,height:1000});await page.goto(base+'/viewer.html?tour=demo');await page.locator('#scene-title').waitFor();
  check(await page.locator('#scene-counter').innerText()==='1 / 3','Opening scene not first');
  check(await page.locator('#scene-title').innerText()==='Điểm s2','Wrong opening scene');
  check(!await page.locator('#viewer-chat').isVisible(),'Keyless chat exposed');
  check(!await page.locator('#viewer-audio').isVisible(),'Empty audio exposed');
  check(!await page.locator('#listen').isVisible(),'Empty introduction exposed');
  check(await page.evaluate(()=>document.documentElement.lang)==='vi','Source language was not initial default');
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:844});
    const rect=await page.locator('#stage').boundingBox();check(rect.width===width&&rect.height===844,'Photo stage not full viewport');
    check(await page.locator('#photo').evaluate(el=>getComputedStyle(el).objectFit)==='cover','Photo not filling screen');
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.documentElement.scrollHeight<=innerHeight),'Page overflow');
    await page.screenshot({path:`tests/demo-ux/viewer-photo-${width}.png`});
  }
  await page.locator('#next').click();await page.locator('#panorama').waitFor();
  const pixels=async()=>page.locator('#panorama').evaluate(canvas=>{const gl=canvas.getContext('webgl');const buffer=new Uint8Array(canvas.width*canvas.height*4);gl.readPixels(0,0,canvas.width,canvas.height,gl.RGBA,gl.UNSIGNED_BYTE,buffer);let blank=0;for(let i=0;i<buffer.length;i+=4)if(buffer[i]<40&&buffer[i+1]<40&&buffer[i+2]<40)blank++;return blank;});
  for(const width of [320,390,1440]){
    await page.setViewportSize({width,height:844});
    await page.locator('#panorama').focus();
    for(const key of ['ArrowRight','ArrowUp','ArrowLeft','ArrowDown']){for(let i=0;i<30;i++)await page.keyboard.press(key);check(await pixels()===0,`${key} revealed blank pixels at ${width}`);}
    await page.mouse.move(width/2,400);await page.mouse.wheel(0,4000);check(await pixels()===0,'Wheel exposed blank pixels');
    await page.mouse.down();await page.mouse.move(width-1,20,{steps:10});await page.mouse.up();check(await pixels()===0,'Drag exposed blank pixels');
  }
  await page.screenshot({path:'tests/demo-ux/viewer-panorama-edge.png'});
  await page.locator('#next').click();await page.waitForFunction(()=>document.querySelector('#stage').ariaBusy==='false');
  for(let i=0;i<20;i++)await page.locator('#panorama').press('ArrowRight');const narrowPixels=await pixels();check(narrowPixels===0,'Narrow panorama exposed blank pixels '+narrowPixels+' scene '+await page.locator('#scene-title').innerText());
  await page.locator('#viewer-info summary').first().click();
  check(await page.locator('.source-disclosure').count()===1,'Missing compact source disclosure');
  check(!await page.locator('#tour-state').isVisible(),'Technical details expanded by default');
  await page.locator('.source-disclosure summary').click();check((await page.locator('#tour-state').innerText()).includes('Tiếng Việt'),'Wrong content locale');
  withAudio=true;configured=true;await page.reload();await page.locator('#listen').waitFor();
  await page.locator('#listen').click();await page.waitForFunction(()=>document.querySelector('#narration-track').currentTime>.1);
  check(await page.locator('#listen').getAttribute('aria-pressed')==='true','Listen state not active');
  await page.locator('#viewer-audio summary').click();await page.locator('#audio-language').selectOption('en');
  check(await page.locator('#viewer-audio').isVisible(),'Other-language recording hides selector');check(!await page.locator('#listen').isVisible(),'Missing language has listen button');
  await page.locator('#audio-language').selectOption('vi');check(await page.locator('#listen').isVisible(),'Cannot restore available narration');
  await page.locator('#listen').click();await page.waitForFunction(()=>!document.querySelector('#narration-track').paused);
  await page.locator('[data-lang=en]').click();check(await page.locator('#narration-track').evaluate(el=>el.paused),'Locale change auto-resumed');
  check(await page.locator('#subtitle').getAttribute('lang')==='vi','Subtitle language mislabeled');await page.locator('[data-lang=vi]').click();
  await page.locator('#listen').click();await page.waitForFunction(()=>!document.querySelector('#narration-track').paused);
  await page.locator('#audio-seek').fill('7.8');await page.locator('#audio-seek').dispatchEvent('input');await page.waitForFunction(()=>document.querySelector('#narration-track').ended);
  check(await page.locator('#listen').getAttribute('aria-pressed')==='false','Listen state remained active after end');
  englishAudio=true;await page.reload();await page.locator('#viewer-audio summary').click();await page.locator('#audio-language').selectOption('en');
  check((await page.locator('#audio-state').innerText()).includes('Giọng AI tạo'),'Generated source label lost');check(await page.locator('#subtitle').getAttribute('lang')==='en','English subtitle has wrong lang');
  await page.locator('#listen').click();await page.waitForFunction(()=>document.querySelector('#narration-track').currentTime>.1);
  await page.locator('#viewer-chat summary').click();check(await page.locator('#narration-track').evaluate(el=>el.paused),'Opening chat did not pause');
  await page.locator('#viewer-chat summary').click();await page.waitForTimeout(200);check(await page.locator('#narration-track').evaluate(el=>el.paused),'Closing chat automatically resumed audio');await page.locator('#viewer-chat summary').click();
  await page.locator('#question-suggestions button').first().click();await page.locator('#ask').click();await page.locator('.viewer-message.assistant').waitFor();
  check(await page.locator('.viewer-message.user').count()===1,'Question not retained');
  check(await page.locator('#question').inputValue()==='','Sent question not cleared');
  chatError=true;await page.locator('#question').fill('Câu hỏi thứ hai');await page.locator('#ask').click();await page.waitForFunction(()=>document.querySelector('#answer').textContent.includes('tạm thời'));
  check(!(await page.locator('#answer').innerText()).includes('OPENAI'),'Technical error leaked');
  check(await page.locator('.viewer-message.user').count()===2,'History lost');
  check(await page.locator('#tour-view').evaluate(el=>el.scrollTop===0),'Chat scrolled immersive viewport');
  check(await page.locator('.immersive-header').isVisible(),'Chat hid header');
  await page.screenshot({path:'tests/demo-ux/viewer-chat.png'});
  check(errors.length===0,errors.join('; '));
  return {pass:true,source:'synthetic image/WAV with mocked API, actual Chromium/WebGL/media',photoViewport:[1440,390,320],openingFirst:true,blankPixels:0,cameraInputs:['keyboard','drag','wheel','resize'],hiddenUnavailable:true,recordedPlayback:true,chatCloseNoAutoResume:true,chatHistory:true,sanitizedError:true,errors};
}
