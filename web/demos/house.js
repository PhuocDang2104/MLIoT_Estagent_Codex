// Product shell around the audited user-provided cached renderer. No model/audio generation.
let demoRendererReady=false;
const observer=new MutationObserver(()=>{
  if(document.querySelector('#houseMode.active'))demoRendererReady=true;
  const header=document.querySelector('#app aside header');
  if(!header||header.dataset.estagent)return;
  header.dataset.estagent='1';
  header.innerHTML='<div><a class="demo-back" href="/viewer.html">← Xem tour · Estagent.</a><strong>NHÀ DEMO</strong><small>Model + ảnh mẫu có sẵn · không dựng mới</small></div>';
  const pano=document.querySelector('#panoMode'),house=document.querySelector('#houseMode');
  if(pano)pano.textContent='Khám phá phòng';if(house)house.textContent='Tổng thể 3D';
  document.querySelector('#app main').insertAdjacentHTML('beforeend','<div id="demo-cache-label">MODEL / ẢNH MẪU CÓ SẴN</div>');
  document.documentElement.dataset.demoSource='cached-zind-house-000';
});
observer.observe(document.querySelector('#app'),{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});

function placeDemoSettings(){
 const target=document.querySelector('#demo-settings-content');if(!target)return;
 for(const id of ['demo-rotate','demo-intro','demo-source']){const element=document.getElementById(id);if(element&&element.parentElement!==target)target.append(element);}
}
// Optional intros stay in settings. Guided playback uses existing recordings only.
async function mountIntro(){
  const response=await fetch('/api/demos/zind-house-000/intro');
  if(!response.ok)throw new Error('Không tải được lời chào mẫu.');
  const tracks=await response.json();if(!tracks.length)return;
  const panel=document.createElement('details');panel.id='demo-intro';
  panel.innerHTML='<summary>Nghe lời chào · AI</summary><div><label>Ngôn ngữ <select aria-label="Ngôn ngữ lời chào"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label><audio controls preload="metadata"></audio><p class="intro-script"></p><small>AI-generated · OpenAI. Chỉ lời chào chung, không mô tả từng phòng.</small><p role="status"></p></div>';
  document.body.append(panel);placeDemoSettings();
  const select=panel.querySelector('select'),audio=panel.querySelector('audio');
  function choose(){audio.pause();const track=tracks.find(t=>t.locale===select.value);audio.removeAttribute('src');panel.querySelector('.intro-script').textContent=track?.script||'Chưa có lời chào ngôn ngữ này.';if(track)audio.src=track.url;audio.load();}
  select.addEventListener('change',choose);audio.addEventListener('error',()=>{panel.querySelector('[role=status]').textContent='Không phát được lời chào. Hãy thử lại.';});
  window.addEventListener('pagehide',()=>audio.pause(),{once:true});choose();
}
mountIntro().catch(error=>{const note=document.createElement('p');note.textContent=error.message;document.querySelector('#demo-source>div').append(note);});

// Slow rotation stays inside the existing captured panorama; never translates the camera.
const motionPreference=matchMedia('(prefers-reduced-motion: reduce)');
let rotating=false,rotationWanted=!motionPreference.matches,lastRotation=0,rotationCarry=0;
const rotatePanel=document.createElement('div');rotatePanel.id='demo-rotate';
rotatePanel.innerHTML='<button type="button" aria-pressed="false">Xoay nhẹ: Tắt</button>';
document.body.append(rotatePanel);
const rotateButton=rotatePanel.querySelector('button');
function setRotation(value){
 rotating=Boolean(value)&&!motionPreference.matches;
 rotateButton.setAttribute('aria-pressed',String(rotating));rotateButton.textContent='Xoay nhẹ: '+(rotating?'Bật':'Tắt');
 rotateButton.disabled=motionPreference.matches;rotateButton.title=motionPreference.matches?'Đã tắt theo tùy chọn giảm chuyển động':'';
 lastRotation=0;rotationCarry=0;
}
rotateButton.addEventListener('click',()=>{rotationWanted=!rotating;setRotation(rotationWanted);});
motionPreference.addEventListener('change',()=>{rotationWanted=false;setRotation(false);});setRotation(false);
function rotateFrame(now){
 if(rotating&&!document.hidden&&document.querySelector('#panoMode')?.classList.contains('active')){
  if(lastRotation)rotationCarry+=Math.min(50,now-lastRotation)*.002; // 2 degrees/second.
  while(rotationCarry>=.05){document.querySelector('#viewport').dispatchEvent(new KeyboardEvent('keydown',{key:'EstagentRotate',bubbles:true}));rotationCarry-=.05;}
  lastRotation=now;
 }else lastRotation=0;
 requestAnimationFrame(rotateFrame);
}
requestAnimationFrame(rotateFrame);
for(const type of ['pointerdown','wheel','keydown'])document.addEventListener(type,event=>{
 if(event.isTrusted&&event.target.closest('#viewport,#rooms,#captures,#floorplan,#checkpoints,#panoWalk,#houseMode,#panoMode'))setRotation(false);
},{capture:true,passive:true});
document.addEventListener('visibilitychange',()=>{if(document.hidden)setRotation(false);});
window.addEventListener('pagehide',()=>setRotation(false),{once:true});

async function mountGuidedTour(){
 const [guideResponse,manifestResponse]=await Promise.all([fetch('/api/demos/zind-house-000/guide'),fetch('/api/demos/zind-house-000/assets/house/manifest.json')]);
 if(!guideResponse.ok||!manifestResponse.ok)throw Error('Không tải được thông tin tour có lời dẫn.');
 const tracks=await guideResponse.json(),manifest=await manifestResponse.json();
 if(!tracks.length)return; // Missing guide is explicit; neutral intro is never substituted.
 const selected=manifest.rooms.flatMap(room=>room.dollhouseCaptureIds.map(id=>({id,room_id:room.id})));
 const panel=document.createElement('section');panel.id='demo-guide';panel.setAttribute('aria-label','Điều khiển tour');
 panel.innerHTML='<button type="button" class="guide-toggle" data-action="toggle" disabled>Đang mở tour…</button><p class="guide-status" role="status" aria-live="polite">Đang chuẩn bị</p><details id="demo-settings"><summary aria-label="Tuỳ chọn tour" title="Tuỳ chọn tour">⋯</summary><div class="guide-settings-panel"><label>Ngôn ngữ <select aria-label="Ngôn ngữ tour"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label><p class="guide-description"></p><details class="guide-transcript"><summary>Lời bản thu</summary><p class="guide-script"></p><small class="guide-audio-note"></small></details><small>Giọng AI · Nội dung theo metadata nguồn.</small><div id="demo-settings-content"></div></div></details><audio preload="auto" hidden></audio>';
 document.body.append(panel);placeDemoSettings();
 document.addEventListener('fullscreenchange',()=>{const host=document.fullscreenElement||document.body;if(host instanceof HTMLElement&&host.tagName!=='CANVAS')host.append(panel);});
 const audio=panel.querySelector(':scope > audio'),locale=panel.querySelector('select'),toggle=panel.querySelector('[data-action=toggle]'),status=panel.querySelector('[role=status]');
 let index=0,running=false,token=0,finished=false,changing=false,started=false;
 const list=()=>selected.map(c=>tracks.find(t=>t.capture_id===c.id&&t.room_id===c.room_id&&t.locale===locale.value));
 function stop(message='Đã tạm dừng'){
  running=false;token++;audio.pause();setRotation(false);toggle.disabled=false;toggle.textContent=finished?'Xem lại tour':started?'Tiếp tục':'Bắt đầu tour';toggle.setAttribute('aria-pressed','false');if(message)status.textContent=message;
 }
 function waitReady(){return new Promise((resolve,reject)=>{
  const watcher=new MutationObserver(check),timeout=setTimeout(()=>done(Error('Trình xem chưa sẵn sàng.')),20000);
  function done(error){clearTimeout(timeout);watcher.disconnect();error?reject(error):resolve();}
  function check(){const first=list()[index];if((demoRendererReady||document.querySelector('#houseMode.active'))&&first&&document.querySelector('#rooms button[data-room="'+first.room_id+'"]')&&document.querySelector('#panoMode')){demoRendererReady=true;done();}}
  watcher.observe(document.querySelector('#app'),{childList:true,subtree:true,attributes:true,attributeFilter:['class']});check();
 });}
 function waitCapture(id,version,buttonOnly=false){return new Promise((resolve,reject)=>{
  const observer=new MutationObserver(check);const timeout=setTimeout(()=>done(Error('Ảnh chưa tải xong. Hãy thử lại.')),12000);
  function done(error){clearTimeout(timeout);observer.disconnect();error?reject(error):resolve();}
  function check(){if(version!==token)return done(Error('cancelled'));if(buttonOnly?document.querySelector('#captures button[data-id="'+id+'"]'):document.querySelector('#captures button.active')?.dataset.id===id&&document.querySelector('#panoMode.active')&&!document.querySelector('#notice')?.textContent)done();}
  observer.observe(document.querySelector('#app'),{attributes:true,childList:true,subtree:true,characterData:true});check();
 });}
 async function step(){
  const version=++token,track=list()[index];
  if(!track){stop('Thiếu lời dẫn đúng ngôn ngữ tại điểm này; tour đã dừng.');return;}
  running=true;toggle.disabled=false;toggle.textContent='Tạm dừng';toggle.setAttribute('aria-pressed','true');changing=true;
  try{
   await waitReady();if(version!==token)return;
   document.querySelector('#demo-intro audio')?.pause();
   document.querySelector('#panoMode').click();
   document.querySelector('#rooms button[data-room="'+track.room_id+'"]').click();
   await waitCapture(track.capture_id,version,true);if(version!==token)return;
   document.querySelector('#captures button[data-id="'+track.capture_id+'"]').click();
   if(audio.src!==new URL(track.url,location.origin).href)audio.src=track.url;
   panel.querySelector('.guide-description').textContent=track.description||track.script;
   panel.querySelector('.guide-script').textContent=track.script;
   panel.querySelector('.guide-audio-note').textContent=track.description!==track.script?'Bản thu ngắn được giữ nguyên; mô tả khu bên trên đã được bổ sung.':'';
   status.textContent='Đang tải điểm '+(index+1)+' / '+selected.length;
   await waitCapture(track.capture_id,version);if(version!==token)return;
   await audio.play();if(version!==token){audio.pause();return;}
   started=true;changing=false;status.textContent='Điểm '+(index+1)+' / '+selected.length;setRotation(rotationWanted);
  }catch(error){changing=false;if(version===token)stop(error.name==='NotAllowedError'?'Chạm để bật âm thanh':error.message==='cancelled'?'Đã dừng':'Không phát được lời dẫn. Chạm để thử lại.');}
 }
 toggle.addEventListener('click',()=>{if(running){stop();return;}if(finished){index=0;finished=false;}step();});
 audio.addEventListener('ended',()=>{if(!running||changing||!audio.ended)return;index++;if(index>=selected.length){finished=true;stop('Đã hoàn tất tour');}else step();});
 audio.addEventListener('pause',()=>{if(running&&!changing&&!audio.ended)stop();});
 audio.addEventListener('error',()=>{if(running)stop('Không tải được lời dẫn. Tour đã dừng.');});
 locale.addEventListener('change',()=>{stop('Đã đổi ngôn ngữ');index=0;finished=false;started=false;toggle.textContent='Bắt đầu tour';});
 for(const type of ['pointerdown','wheel','keydown','click'])document.addEventListener(type,event=>{
  if(event.isTrusted&&event.target.closest('#viewport,#rooms,#captures,#floorplan,#checkpoints,#panoWalk,#houseMode,#panoMode,[data-chat],#chat-toggle')){stop('Bạn đang tự khám phá; tour tự động đã dừng.');panel.querySelector('.guide-description').textContent='Tiếp tục tour để nghe lời dẫn tại điểm xem.';panel.querySelector('.guide-script').textContent='';panel.querySelector('.guide-audio-note').textContent='';audio.removeAttribute('src');audio.load();}
 },{capture:true,passive:true});
 document.addEventListener('narration-preview-start',()=>stop());document.addEventListener('chat-start',()=>stop());
 document.addEventListener('play',event=>{if(event.target!==audio&&event.target instanceof HTMLMediaElement)stop();},true);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});window.addEventListener('pagehide',()=>stop(),{once:true});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&panel.querySelector('#demo-settings').open){event.preventDefault();event.stopPropagation();panel.querySelector('#demo-settings').open=false;panel.querySelector('#demo-settings>summary').focus();}},{capture:true});
 step(); // Attempt real playback on entry; browser denial becomes the single start button.
}
mountGuidedTour().catch(error=>{const note=document.createElement('p');note.textContent=error.message;document.querySelector('#demo-source>div').append(note);});
