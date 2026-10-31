// Product shell around the audited user-provided cached renderer. No model/audio generation.
const observer=new MutationObserver(()=>{
  const header=document.querySelector('#app aside header');
  if(!header||header.dataset.estagent)return;
  header.dataset.estagent='1';
  header.innerHTML='<div><a class="demo-back" href="/viewer.html">← Xem tour · Estagent.</a><strong>NHÀ DEMO</strong><small>Model + ảnh mẫu có sẵn · không dựng mới</small></div>';
  const pano=document.querySelector('#panoMode'),house=document.querySelector('#houseMode');
  if(pano)pano.textContent='Khám phá phòng';if(house)house.textContent='Tổng thể 3D';
  document.querySelector('#app main').insertAdjacentHTML('beforeend','<div id="demo-cache-label">MODEL / ẢNH MẪU CÓ SẴN</div>');
  document.documentElement.dataset.demoSource='cached-zind-house-000';
});
observer.observe(document.querySelector('#app'),{childList:true,subtree:true});
window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});

// Playback of two pre-generated neutral intros. No Speech API request or autoplay.
async function mountIntro(){
  const response=await fetch('/api/demos/zind-house-000/intro');
  if(!response.ok)throw new Error('Không tải được lời chào mẫu.');
  const tracks=await response.json();if(!tracks.length)return;
  const panel=document.createElement('details');panel.id='demo-intro';
  panel.innerHTML='<summary>Nghe lời chào · AI</summary><div><label>Ngôn ngữ <select aria-label="Ngôn ngữ lời chào"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label><audio controls preload="metadata"></audio><p class="intro-script"></p><small>AI-generated · OpenAI. Chỉ lời chào chung, không mô tả từng phòng.</small><p role="status"></p></div>';
  document.body.append(panel);
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
 const panel=document.createElement('details');panel.id='demo-guide';panel.open=true;
 panel.innerHTML='<summary>Tour có lời dẫn · AI</summary><div><label>Ngôn ngữ <select aria-label="Ngôn ngữ tour"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label><div class="guide-buttons"><button type="button" data-action="play">Play tour</button><button type="button" data-action="pause" disabled>Pause</button></div><p class="guide-description"></p><audio controls preload="none"></audio><p role="status">Nhấn Play tour để bắt đầu.</p><small>AI-generated · Nội dung theo metadata nguồn. Hết lời sẽ chuyển điểm xem kế tiếp.</small></div>';
 document.body.append(panel);
 const audio=panel.querySelector('audio'),locale=panel.querySelector('select'),play=panel.querySelector('[data-action=play]'),pause=panel.querySelector('[data-action=pause]'),status=panel.querySelector('[role=status]');
 let index=0,running=false,token=0,finished=false,changing=false;
 const list=()=>selected.map(c=>tracks.find(t=>t.capture_id===c.id&&t.room_id===c.room_id&&t.locale===locale.value));
 function stop(message='Đã tạm dừng. Nhấn Play tour để tiếp tục.'){
  running=false;token++;audio.pause();setRotation(false);pause.disabled=true;play.disabled=false;if(message)status.textContent=message;
 }
 function waitCapture(id,version){return new Promise((resolve,reject)=>{
  const observer=new MutationObserver(check);const timeout=setTimeout(()=>done(Error('Ảnh chưa tải xong. Hãy thử lại.')),12000);
  function done(error){clearTimeout(timeout);observer.disconnect();error?reject(error):resolve();}
  function check(){if(version!==token)return done(Error('cancelled'));if(document.querySelector('#captures button.active')?.dataset.id===id&&!document.querySelector('#notice')?.textContent)done();}
  observer.observe(document.querySelector('#app'),{attributes:true,childList:true,subtree:true,characterData:true});check();
 });}
 async function step(){
  const version=++token,track=list()[index];
  if(!track){stop('Thiếu lời dẫn đúng ngôn ngữ tại điểm này; tour đã dừng.');return;}
  running=true;play.disabled=true;pause.disabled=false;changing=true;
  try{
   document.querySelector('#demo-intro audio')?.pause();
   document.querySelector('#rooms button[data-room="'+track.room_id+'"]').click();
   document.querySelector('#captures button[data-id="'+track.capture_id+'"]').click();
   if(audio.src!==new URL(track.url,location.origin).href)audio.src=track.url;
   panel.querySelector('.guide-description').textContent=track.description||track.script;
   status.textContent='Đang tải điểm '+(index+1)+' / '+selected.length;
   await waitCapture(track.capture_id,version);if(version!==token)return;
   await audio.play();if(version!==token){audio.pause();return;}
   changing=false;status.textContent='Điểm '+(index+1)+' / '+selected.length;setRotation(rotationWanted);
  }catch(error){changing=false;if(version===token)stop(error.message==='cancelled'?'Đã dừng.':'Không phát được lời dẫn. Nhấn Play tour để thử lại.');}
 }
 play.addEventListener('click',()=>{if(finished){index=0;finished=false;play.textContent='Play tour';}step();});
 pause.addEventListener('click',()=>stop());
 audio.addEventListener('ended',()=>{if(!running||changing||!audio.ended)return;index++;if(index>=selected.length){finished=true;stop('Đã hoàn tất tour.');play.textContent='Replay tour';}else step();});
 audio.addEventListener('pause',()=>{if(running&&!changing&&!audio.ended)stop();});
 audio.addEventListener('error',()=>{if(running)stop('Không tải được lời dẫn. Tour đã dừng.');});
 locale.addEventListener('change',()=>{stop('Đã đổi ngôn ngữ. Nhấn Play tour để bắt đầu.');index=0;finished=false;play.textContent='Play tour';});
 for(const type of ['pointerdown','wheel','keydown','click'])document.addEventListener(type,event=>{
  if(event.isTrusted&&event.target.closest('#viewport,#rooms,#captures,#floorplan,#checkpoints,#panoWalk,#houseMode,#panoMode,[data-chat],#chat-toggle'))stop('Bạn đang tự khám phá; tour tự động đã dừng.');
 },{capture:true,passive:true});
 document.addEventListener('narration-preview-start',()=>stop());document.addEventListener('chat-start',()=>stop());
 document.addEventListener('play',event=>{if(event.target!==audio&&event.target instanceof HTMLMediaElement)stop();},true);
 document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});window.addEventListener('pagehide',()=>stop(),{once:true});
}
mountGuidedTour().catch(error=>{const note=document.createElement('p');note.textContent=error.message;document.querySelector('#demo-source>div').append(note);});
