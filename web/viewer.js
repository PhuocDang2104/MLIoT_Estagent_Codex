import {$,t,language,api,node,notice,link,requestID} from './tour-common.js';
import {PanoramaCamera} from './panorama.js';
let manifest=null,libraryTours=[],index=0,camera=null,loadGeneration=0,view={yaw:0,pitch:0,fov:70,coverage:240};
let speech=null,utterance=null,paused=false;
const params=new URLSearchParams(location.search),draftID=params.get('draft'),tourID=params.get('tour');
function stop(){if('speechSynthesis' in window)window.speechSynthesis.cancel();utterance=null;speech=null;paused=false;$('#play').ariaPressed='false';}
function draw(){if(camera&&!$('#panorama').hidden)camera.draw(view);}
function say(){
  if(!$('#device-voice').checked){notice(t('Enable device voice to use the labelled fallback. Recorded audio is unavailable.','Bật giọng thiết bị để dùng fallback. Chưa có lời thu âm.'),true);return;}
  if(!('speechSynthesis' in window)){notice(t('Device speech is unavailable in this browser.','Trình duyệt chưa hỗ trợ giọng thiết bị.'),true);return;}
  const scene=manifest.scenes[index];
  if(manifest.locale!==language()){notice(t('No narration in this language. Switch to the tour language.','Chưa có lời theo ngôn ngữ này. Chuyển sang ngôn ngữ gốc của tour.'),true);return;}
  if(paused){window.speechSynthesis.resume();paused=false;$('#play').ariaPressed='true';return;}
  const localVoice=window.speechSynthesis.getVoices().find(v=>v.localService&&v.lang.toLowerCase().startsWith(language()));
  if(!localVoice){notice(t('No local device voice is available for this language. Subtitles remain available.','Thiết bị chưa có giọng cục bộ cho ngôn ngữ này. Bạn vẫn có thể đọc phụ đề.'),true);return;}
  stop();const text=scene.description||scene.name;
  utterance=new SpeechSynthesisUtterance(text);utterance.voice=localVoice;utterance.lang=language()==='vi'?'vi-VN':'en-US';utterance.volume=Number($('#voice-volume').value);
  const active=utterance;active.onend=()=>{if(utterance===active){speech=null;utterance=null;$('#play').ariaPressed='false';}};active.onerror=()=>{if(utterance===active)notice(t('Device voice failed. Read the subtitle instead.','Giọng thiết bị bị lỗi. Bạn vẫn có thể đọc phụ đề.'),true);};speech='device';window.speechSynthesis.speak(active);$('#play').ariaPressed='true';notice(t('Device voice fallback — not recorded narration.','Giọng thiết bị fallback — không phải lời thu âm.'));
}
async function select(next){
  stop();index=(next+manifest.scenes.length)%manifest.scenes.length;const scene=manifest.scenes[index],generation=++loadGeneration;
  $('#scene-title').textContent=scene.name;$('#subtitle').textContent=scene.description||t('No description supplied.','Chưa có mô tả.');$('#scene-counter').textContent=`${index+1} / ${manifest.scenes.length}`;
  $('#coverage').textContent=scene.projection==='photo'?t('Original photo · no view behind the camera.','Ảnh thường · không có góc nhìn phía sau camera.'):t(`Cylindrical panorama · ${scene.coverage_degrees}° (${scene.coverage_source==='user_provisional'?'provisional coverage':'creator calibrated'}) · blank areas were not captured · not 3D. Drag to look around.`,`Panorama chiếu trụ · ${scene.coverage_degrees}° (${scene.coverage_source==='user_provisional'?'góc phủ tạm':'người dùng hiệu chỉnh'}) · vùng trắng chưa được chụp · không phải 3D. Kéo để nhìn quanh.`);
  $('#scene-nav').querySelectorAll('button').forEach((b,i)=>b.setAttribute('aria-current',i===index?'true':'false'));
  $('#panorama').hidden=true;$('#photo').hidden=false;$('#photo').src=scene.image_url;$('#photo').alt=scene.name;
  $('#zoom-in').disabled=$('#zoom-out').disabled=$('#reset-view').disabled=scene.projection==='photo';
  if(scene.projection==='cylindrical'){
    const img=new Image();img.src=scene.image_url;
    try{await img.decode();if(generation!==loadGeneration)return;camera??=new PanoramaCamera($('#panorama'));camera.setImage(img);view={yaw:0,pitch:0,fov:70,coverage:scene.coverage_degrees};$('#photo').hidden=true;$('#panorama').hidden=false;draw();}
    catch{if(generation===loadGeneration)notice(t('Panorama rendering failed. Showing the original photo.','Không dựng được góc xem panorama. Đang hiện ảnh gốc.'),true);}
  }
}
function renderText(){if(!manifest){renderLibrary();return;}$('#tour-heading').textContent=manifest.title;$('#tour-state').textContent=(draftID?t('PRIVATE PREVIEW','XEM THỬ RIÊNG'):t('PUBLISHED SNAPSHOT','BẢN ĐÃ XUẤT BẢN'))+t(` · revision ${manifest.revision} · content: ${manifest.locale.toUpperCase()}`,` · bản ${manifest.revision} · nội dung: ${manifest.locale.toUpperCase()}`);select(index);}

function renderLibrary(){
  $('#tour-library').replaceChildren();
  if(!libraryTours.length)$('#tour-library').append(node('p',t('No published tours yet. A Creator must review and publish a tour first.','Chưa có tour được xuất bản. Creator cần xem thử và duyệt tour trước.'),'empty-state'));
  for(const tour of libraryTours){const card=link('',tour.viewer_url||`/viewer.html?tour=${tour.id}`,'library-card');const img=node('img');img.src=tour.thumbnail_url;img.alt='';card.append(img,node('h2',tour.title),node('span',tour.format==='studio'?t('3D + panorama · Open tour ↗','3D + panorama · Mở tour ↗'):t('Open tour ↗','Mở tour ↗')));$('#tour-library').append(card);}
}
$('#previous').onclick=()=>select(index-1);$('#next').onclick=()=>select(index+1);
$('#zoom-in').onclick=()=>{view.fov=Math.max(30,view.fov-8);draw();};$('#zoom-out').onclick=()=>{view.fov=Math.min(110,view.fov+8);draw();};$('#reset-view').onclick=()=>{view.yaw=0;view.pitch=0;view.fov=70;draw();};
$('#fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if($('#stage').requestFullscreen)await $('#stage').requestFullscreen();else throw new Error();}catch{notice(t('Fullscreen is unavailable in this browser.','Trình duyệt chưa hỗ trợ toàn màn hình.'),true);}};
let drag=null;const canvas=$('#panorama');canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(!drag)return;view.yaw-=(e.clientX-drag.x)*.16;view.pitch=Math.max(-65,Math.min(65,view.pitch+(e.clientY-drag.y)*.12));drag={x:e.clientX,y:e.clientY};draw();};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;canvas.addEventListener('wheel',e=>{e.preventDefault();view.fov=Math.max(30,Math.min(110,view.fov+e.deltaY*.025));draw();},{passive:false});
canvas.onkeydown=e=>{const steps={ArrowLeft:[-8,0],ArrowRight:[8,0],ArrowUp:[0,6],ArrowDown:[0,-6]};if(steps[e.key]){e.preventDefault();view.yaw+=steps[e.key][0];view.pitch=Math.max(-65,Math.min(65,view.pitch+steps[e.key][1]));draw();}};
window.addEventListener('resize',draw);document.addEventListener('fullscreenchange',draw);
$('#play').onclick=say;$('#pause').onclick=()=>{if(speech){window.speechSynthesis.pause();paused=true;$('#play').ariaPressed='false';}};$('#device-voice').onchange=stop;
$('#voice-volume').oninput=()=>{if(utterance){const active=speech==='device'&&!paused;stop();if(active)say();}};
$('#viewer-chat').ontoggle=()=>{if($('#viewer-chat').open)stop();};$('#question').onfocus=stop;
$('#question-form').onsubmit=async e=>{e.preventDefault();stop();$('#ask').disabled=true;try{const data=await api(`/published/${tourID}/chat`,{method:'POST',body:{text:$('#question').value,revision:manifest.revision,request_id:requestID(),locale:language()}});$('#answer').textContent=data.reply;if(data.scene_id)await select(manifest.scenes.findIndex(s=>s.id===data.scene_id));}catch(e){$('#answer').textContent=e.message;}finally{$('#ask').disabled=false;}};
window.addEventListener('pagehide',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});document.addEventListener('languagechange',()=>{stop();notice('');renderText();});
$('#photo').onerror=()=>notice(t('This scene image is unavailable. Other scenes remain accessible.','Ảnh này không tải được. Bạn vẫn xem được các điểm khác.'),true);
try{
  await api('/session');
  if(draftID||tourID){manifest=await api(draftID?`/drafts/${draftID}`:`/published/${tourID}`);$('#tour-view').hidden=false;$('#viewer-chat').hidden=!!draftID;
    manifest.scenes.forEach((scene,i)=>{const button=node('button',undefined,'scene-thumb');button.type='button';const image=node('img');image.src=scene.thumbnail_url;image.alt='';button.append(image,node('span',scene.name));button.onclick=()=>select(i);$('#scene-nav').append(button);});
    index=manifest.scenes.findIndex(s=>s.id===manifest.start_scene_id);renderText();
  }else{
    const results=await Promise.allSettled([api('/published'),fetch('/api/studio-tours').then(async response=>{
      if(!response.ok)throw new Error('Studio library unavailable');return response.json();})]);
    libraryTours=results.flatMap(result=>result.status==='fulfilled'?result.value:[]);renderLibrary();
    if(results.some(result=>result.status==='rejected'))notice(t('Part of the tour library could not be loaded. Please refresh.','Một phần thư viện chưa tải được. Vui lòng tải lại.'),true);
  }
}catch(e){notice(e.message,true);}
