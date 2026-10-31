async (page) => {
  await page.unrouteAll({behavior:'wait'});
  const errors = [];
  page.on('pageerror',e=>errors.push(e.message));
  const check = (ok,label) => {if(!ok) throw new Error(label);};
  const base='http://127.0.0.1:5180/assistant.html';
  await page.setViewportSize({width:1440,height:1050});
  await page.goto(base);
  await page.getByText('Chưa kết nối OpenAI',{exact:true}).waitFor();
  check(await page.locator('#send').isDisabled(),'missing key does not simulate AI');
  await page.screenshot({path:'web/evidence/assistant-no-key.png',fullPage:true});
  let data={configured:true,profile:{},deferred:[],history:[],awaiting:'address',stage:'required',confirmed:false,required:['address','area','bedrooms'],labels:{address:'Vị trí',area:'Diện tích',bedrooms:'Phòng ngủ',name:'Tên căn hộ',direction:'Hướng',windows:'Cửa sổ',rooms:'Tổng số phòng',bathrooms:'Phòng tắm',notes:'Thông tin thêm'},reply:'Mình sẽ giúp bạn tạo hồ sơ căn hộ. Căn hộ của bạn ở khu vực nào?'};
  let fail=false;
  await page.route('**/api/assistant/state',r=>r.fulfill({json:data}));
  await page.route('**/api/assistant/turn',async r=>{
    const {text}=r.request().postDataJSON();
    if(fail) return r.fulfill({status:502,json:{error:'Lỗi mô phỏng để kiểm tra thử lại.'}});
    if(text.includes('85')){data.profile={address:'Quận 7, TP.HCM',area:85,bedrooms:2};data.stage='optional';data.awaiting='name';data.reply='Đã đủ thông tin bắt buộc. Bạn muốn đặt tên gì cho căn hộ? Mục này có thể bỏ qua.';}
    else if(text.startsWith('Bỏ qua')){data.deferred=['name'];data.awaiting='direction';data.reply='Căn hộ hướng nào? Chưa biết thì để sau nhé.';}
    else if(text.startsWith('Để tất cả')){data.deferred=['name','direction','windows','rooms','bathrooms','notes'];data.stage='review';data.awaiting=null;data.reply='Bạn kiểm tra hồ sơ rồi xác nhận nhé.';}
    else if(text.includes('xác nhận')){data.stage='complete';data.confirmed=true;data.reply='Đã xác nhận hồ sơ. Bạn vẫn có thể bổ sung sau.';}
    else if(text.includes('90')){data.profile.area=90;data.confirmed=false;data.stage='review';data.reply='Đã sửa diện tích thành 90 m². Bạn xác nhận lại nhé.';}
    data.history.push({role:'user',content:text},{role:'assistant',content:data.reply});
    await r.fulfill({json:data});
  });
  await page.reload();
  await page.locator('#message').fill('Căn hộ ở Quận 7, TP.HCM, rộng 85 m², có 2 phòng ngủ.');
  await page.locator('#send').click();
  await page.getByText('3 / 3 thông tin cần có',{exact:true}).waitFor();
  check(await page.locator('#skip').isVisible(),'optional skip shown');
  await page.screenshot({path:'web/evidence/assistant-desktop.png',fullPage:true});
  await page.locator('#skip').click();
  await page.locator('.field.deferred').waitFor();
  await page.locator('#defer').click();
  await page.locator('#confirm').click();
  await page.getByText('Đã xác nhận',{exact:true}).waitFor();
  await page.locator('#message').fill('Sửa diện tích thành 90 m².');
  await page.locator('#send').click();
  await page.getByText('90 m²',{exact:true}).waitFor();
  check(await page.locator('#confirm').isVisible(),'correction reopens confirmation');
  fail=true;
  await page.locator('#message').fill('Thông tin gửi lại');
  await page.locator('#send').click();
  await page.getByText('Lỗi mô phỏng để kiểm tra thử lại.',{exact:true}).waitFor();
  check(await page.locator('#message').inputValue()==='Thông tin gửi lại','failed message preserved');
  fail=false;
  await page.evaluate(()=>{navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('Denied','NotAllowedError');};});
  await page.locator('#microphone').click();
  await page.getByText('Bạn chưa cấp quyền micro. Hãy bật quyền hoặc tiếp tục chat chữ.',{exact:true}).waitFor();
  check(await page.locator('#send').isEnabled(),'text survives microphone denial');
  await page.route('**/api/assistant/voice',r=>r.fulfill({contentType:'application/sdp',body:'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'}));
  await page.evaluate(()=>{
    window.__sent=[];window.__track={enabled:false,stopped:false,stop(){this.stopped=true;}};
    navigator.mediaDevices.getUserMedia=async()=>({getTracks:()=>[window.__track],getAudioTracks:()=>[window.__track]});
    class Channel extends EventTarget{readyState='connecting';send(raw){window.__sent.push(JSON.parse(raw));}close(){this.readyState='closed';this.dispatchEvent(new Event('close'));}}
    window.RTCPeerConnection=class extends EventTarget{
      connectionState='new';localDescription=null;
      addTransceiver(){return {sender:{replaceTrack:async()=>{}}};}
      createDataChannel(){window.__channel=new Channel();return window.__channel;}
      async createOffer(){return {type:'offer',sdp:'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'};}
      async setLocalDescription(d){this.localDescription=d;}
      async setRemoteDescription(){window.__channel.readyState='open';window.__channel.dispatchEvent(new Event('open'));}
      close(){this.connectionState='closed';}
    };
  });
  await page.locator('#microphone').click();
  await page.waitForFunction(()=>document.querySelector('#microphone').getAttribute('aria-pressed')==='true');
  await page.evaluate(()=>window.__channel.dispatchEvent(new MessageEvent('message',{data:JSON.stringify({type:'conversation.item.input_audio_transcription.completed',transcript:'Sửa diện tích thành 90 m².'})})));
  await page.waitForFunction(()=>window.__sent.some(e=>e.type==='response.create'));
  check(await page.evaluate(()=>window.__sent.find(e=>e.type==='response.create').response.instructions.includes('90 m²')),'voice reads graph reply');
  await page.locator('#stop-audio').click();
  check(await page.evaluate(()=>window.__sent.some(e=>e.type==='response.cancel')),'stop cancels output');
  await page.locator('#end-voice').click();
  check(await page.evaluate(()=>window.__track.stopped),'microphone released');
  check(await page.locator('#send').isEnabled(),'text survives voice end');
  for(const width of [390,320]){
    await page.setViewportSize({width,height:844});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width}px no overflow`);
    if(width===390)await page.screenshot({path:'web/evidence/assistant-mobile.png',fullPage:true});
  }
  check(errors.length===0,errors.join(';'));
  return 'PASS: actual missing-key UI; mocked text/optional/defer/confirm/correction/retry; microphone denied; mocked voice transcript → graph API → audio response; stop/release microphone; 320/390px layout; no page errors. No live OpenAI audio or extraction tested.';
}
