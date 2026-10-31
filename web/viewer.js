import {$,t,language,api,node,notice,link,requestID} from './tour-common.js';
import {PanoramaCamera} from './panorama.js';
let manifest=null,libraryTours=[],index=0,camera=null,loadGeneration=0,view={yaw:0,pitch:0,fov:70,coverage:240};
let speech=null,utterance=null,paused=false;
const params=new URLSearchParams(location.search),draftID=params.get('draft'),tourID=params.get('tour');
// Two actual media elements, one narration source at a time. No generated audio.
class RecordedTourPlayer {
  constructor(){
    this.voice=$('#narration-track');this.music=$('#music-track');this.active=false;this.generation=0;this.narrating=false;this.track=null;this.musicTrack=null;this.error='';
    for(const event of ['playing','pause','ended','waiting'])this.voice.addEventListener(event,()=>{
      this.narrating=event==='playing';this.mix();this.progress();
      if(event==='ended'&&!this.musicTrack)this.active=false;
    });
    this.voice.addEventListener('timeupdate',()=>this.progress());
    this.voice.addEventListener('loadedmetadata',()=>this.progress());
    this.voice.addEventListener('error',()=>this.failed('voice'));
    this.music.addEventListener('error',()=>this.failed('music'));
  }
  pause(){
    this.active=false;this.generation++;this.voice.pause();this.music.pause();this.narrating=false;this.mix();$('#play').ariaPressed='false';
  }
  select(scene,audio,locale,auto=false){
    this.pause();this.error='';this.scene=scene;
    const candidate=(audio?.narration||[]).find(n=>n.scene_id===scene.id&&n.locale===locale);
    this.track=candidate||null;this.wrongLocale=(audio?.narration||[]).some(n=>n.scene_id===scene.id&&n.locale!==locale);
    this.voice.removeAttribute('src');this.voice.load();
    if(this.track)this.voice.src=this.track.track.url;
    const music=audio?.music||null;
    if(music?.url!==this.musicTrack?.url){this.music.removeAttribute('src');this.music.load();if(music)this.music.src=music.url;}
    this.musicTrack=music;
    $('#music').disabled=$('#music-volume').disabled=!music;
    $('#narration-enabled').disabled=!this.track;
    $('#audio-seek').disabled=!this.track;$('#audio-seek').max=this.track?.track.duration_seconds||0;$('#audio-seek').value=0;
    $('#device-voice').disabled=!!this.track;if(this.track)$('#device-voice').checked=false;
    if(this.track?.transcript)$('#subtitle').textContent=this.track.transcript;$('#full-subtitle').textContent=this.track?.transcript||'';
    this.mix();this.progress();this.describe();if(auto)this.play();
  }
  describe(){
    const voice=this.track?t('Uploaded recording','Bản thu đã tải lên'):this.wrongLocale?t('No recording in this language','Không có bản thu theo ngôn ngữ này'):t('No recording for this scene','Chưa có bản thu cho điểm này');
    const music=this.musicTrack?t('uploaded music','có nhạc đã tải'):t('no music','chưa có nhạc');
    $('#audio-state').textContent=this.error||`${voice} · ${music}. `+(this.track&&!this.track.transcript?t('No transcript supplied.','Chưa có lời chép của bản thu.'):'');
    const sources=[this.track?.track,this.musicTrack].filter(Boolean).map(track=>`${track.source_label} · ${track.rights}: ${track.rights_note}`);
    $('#audio-source').textContent=sources.join(' / ');
  }
  mix(){
    this.voice.muted=!$('#narration-enabled').checked;this.voice.volume=Number($('#voice-volume').value);
    this.music.muted=!$('#music').checked;
    const duck=this.narrating&&!this.voice.muted&&this.voice.volume>0;
    this.music.volume=Number($('#music-volume').value)*(duck?.2:1);
  }
  progress(){
    const duration=this.track?.track.duration_seconds||0,current=Math.min(this.voice.currentTime||0,duration);
    $('#audio-time').textContent=`${current.toFixed(1)} / ${duration.toFixed(1)}s`;
    $('#audio-seek').value=String(current);
  }
  seek(value){
    if(!this.track)return;
    if(this.voice.readyState<1){this.error=t('Recording is still loading; try seeking again.','Bản thu đang tải; thử tua lại sau.');this.describe();return;}
    this.voice.currentTime=Math.min(Math.max(0,Number(value)),this.track.track.duration_seconds);this.progress();
  }
  failed(which){
    if(which==='voice'&&!this.track||which==='music'&&!this.musicTrack)return;
    this.error=which==='voice'?t('Recording failed to load. Subtitles and scene navigation remain available.','Không tải được bản thu. Phụ đề và các điểm xem vẫn hoạt động.'):t('Music failed to load. Narration and the visual tour remain available.','Không tải được nhạc. Bản thu lời và tour hình ảnh vẫn hoạt động.');
    if(which==='voice'){this.narrating=false;this.voice.pause();}else this.music.pause();
    this.mix();this.describe();
  }
  async play(){
    if(!this.track&&!this.musicTrack){this.describe();notice(t('No recorded audio here. Enable device voice for the labelled fallback.','Chưa có audio thu sẵn. Bật giọng thiết bị nếu muốn dùng fallback.'),true);return;}
    this.active=true;const generation=++this.generation;$('#play').ariaPressed='true';this.error='';this.describe();
    if(this.voice.ended)this.voice.currentTime=0;
    const sources=[...(this.track?[this.voice]:[]),...(this.musicTrack?[this.music]:[])];
    const results=await Promise.allSettled(sources.map(element=>element.play()));
    if(generation!==this.generation)return;
    if(results.some(r=>r.status==='rejected')){
      // Keep a successful track playing, but never call a missing/blocked track a success.
      this.error=t('One audio track could not start. Check playback permission or the recording; the visual tour still works.','Một track audio chưa phát được. Kiểm tra quyền phát hoặc bản thu; tour hình ảnh vẫn hoạt động.');this.describe();
      this.active=sources.some(element=>!element.paused);
    }
    this.mix();
  }
}
const recorded=new RecordedTourPlayer();
function stop(){recorded.pause();if('speechSynthesis' in window)window.speechSynthesis.cancel();utterance=null;speech=null;paused=false;$('#play').ariaPressed='false';}
// Fit the initial vertical view to captured pixels without changing projection/coverage.
function fittedFov(){const stage=$('#stage'),aspect=stage.clientWidth/stage.clientHeight;return camera?Math.max(30,Math.min(70,2*Math.atan(view.coverage*Math.PI/180*camera.ratio/2*Math.max(1,aspect))*180/Math.PI)):70;}
function draw(){if(camera&&!$('#panorama').hidden)camera.draw({...view,yaw:Math.max(-view.coverage/2,Math.min(view.coverage/2,view.yaw))});}
function say(){
  recorded.pause();
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
  const continueAudio=recorded.active;stop();index=(next+manifest.scenes.length)%manifest.scenes.length;const scene=manifest.scenes[index],generation=++loadGeneration;
  $('#scene-title').textContent=scene.name;$('#scene-description').textContent=scene.description||scene.name;$('#projection-label').textContent=scene.projection==='cylindrical'?`${scene.coverage_degrees}° · ${scene.coverage_source==='user_calibrated'?t('calibrated panorama','panorama đã hiệu chỉnh'):t('provisional panorama','panorama góc tạm tính')}`:t('Photo · original perspective','Ảnh · góc nhìn gốc');$('#subtitle').textContent=scene.description||t('No description supplied.','Chưa có mô tả.');$('#scene-counter').textContent=`${index+1} / ${manifest.scenes.length}`;
  $('#coverage').textContent=scene.projection==='photo'?t('Original photo · no view behind the camera.','Ảnh thường · không có góc nhìn phía sau camera.'):t(`Cylindrical panorama · ${scene.coverage_degrees}° (${scene.coverage_source==='user_provisional'?'provisional coverage':'creator calibrated'}) · blank areas were not captured · not 3D. Drag to look around.`,`Panorama chiếu trụ · ${scene.coverage_degrees}° (${scene.coverage_source==='user_provisional'?'góc phủ tạm':'người dùng hiệu chỉnh'}) · vùng trống chưa được chụp · không phải 3D. Kéo để nhìn quanh.`);
  recorded.select(scene,manifest.audio,language(),continueAudio);
  $('#scene-nav').querySelectorAll('button').forEach((b,i)=>b.setAttribute('aria-current',i===index?'true':'false'));
  const keepPanorama=scene.projection==='cylindrical'&&camera&&!$('#panorama').hidden;$('#panorama').hidden=!keepPanorama;$('#photo').hidden=!!keepPanorama;$('#stage').ariaBusy='true';$('#photo').src=scene.image_url;$('#photo').alt=scene.name;
  $('#zoom-in').disabled=$('#zoom-out').disabled=$('#reset-view').disabled=scene.projection==='photo';
  if(scene.projection==='cylindrical'){
    const img=new Image();img.src=scene.image_url;
    try{await img.decode();if(generation!==loadGeneration)return;camera??=new PanoramaCamera($('#panorama'));camera.setImage(img);view={yaw:0,pitch:0,fov:70,coverage:scene.coverage_degrees};view.fov=fittedFov();$('#photo').hidden=true;$('#panorama').hidden=false;$('#stage').ariaBusy='false';draw();revealScene();}
    catch{if(generation===loadGeneration){$('#panorama').hidden=true;$('#photo').hidden=false;$('#stage').ariaBusy='false';notice(t('Panorama rendering failed. Showing the original photo.','Không dựng được góc xem panorama. Đang hiện ảnh gốc.'),true);}}
  }else{$('#stage').ariaBusy='false';}
}
function renderText(){if(!manifest){renderLibrary();return;}$('#tour-heading').textContent=manifest.title;$('#tour-state').textContent=(draftID?t('PRIVATE PREVIEW','XEM THỬ RIÊNG'):t('PUBLISHED SNAPSHOT','BẢN ĐÃ XUẤT BẢN'))+t(` · revision ${manifest.revision} · content: ${manifest.locale.toUpperCase()}`,` · bản ${manifest.revision} · nội dung: ${manifest.locale.toUpperCase()}`);select(index);}

function renderLibrary(){
  $('#tour-library').replaceChildren();
  if(!libraryTours.length)$('#tour-library').append(node('p',t('No published tours yet. A Creator must review and publish a tour first.','Chưa có tour được xuất bản. Creator cần xem thử và duyệt tour trước.'),'empty-state'));
  for(const tour of libraryTours){const card=link('',`/viewer.html?tour=${tour.id}`,'library-card');const img=node('img');img.src=tour.thumbnail_url;img.alt='';card.append(img,node('h2',tour.title),node('span',t('Open tour ↗','Mở tour ↗')));$('#tour-library').append(card);}
}
$('#previous').onclick=()=>select(index-1);$('#next').onclick=()=>select(index+1);
$('#zoom-in').onclick=()=>{view.fov=Math.max(30,view.fov-8);draw();};$('#zoom-out').onclick=()=>{view.fov=Math.min(110,view.fov+8);draw();};$('#reset-view').onclick=()=>{view.yaw=0;view.pitch=0;view.fov=fittedFov();draw();};
$('#fullscreen').onclick=async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else if($('#tour-view').requestFullscreen)await $('#tour-view').requestFullscreen();else throw new Error();}catch{notice(t('Fullscreen is unavailable in this browser.','Trình duyệt chưa hỗ trợ toàn màn hình.'),true);}};
let drag=null;const canvas=$('#panorama');canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY};canvas.setPointerCapture(e.pointerId);};canvas.onpointermove=e=>{if(!drag)return;view.yaw=Math.max(-view.coverage/2,Math.min(view.coverage/2,view.yaw-(e.clientX-drag.x)*.16));view.pitch=Math.max(-65,Math.min(65,view.pitch+(e.clientY-drag.y)*.12));drag={x:e.clientX,y:e.clientY};draw();};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;canvas.addEventListener('wheel',e=>{e.preventDefault();view.fov=Math.max(30,Math.min(110,view.fov+e.deltaY*.025));draw();},{passive:false});
canvas.onkeydown=e=>{const steps={ArrowLeft:[-8,0],ArrowRight:[8,0],ArrowUp:[0,6],ArrowDown:[0,-6]};if(steps[e.key]){e.preventDefault();view.yaw=Math.max(-view.coverage/2,Math.min(view.coverage/2,view.yaw+steps[e.key][0]));view.pitch=Math.max(-65,Math.min(65,view.pitch+steps[e.key][1]));draw();}};
window.addEventListener('resize',()=>{view.fov=Math.min(view.fov,fittedFov());draw();});document.addEventListener('fullscreenchange',()=>{syncFullscreen();draw();});
function syncFullscreen(){const active=!!document.fullscreenElement;$('#fullscreen').ariaPressed=String(active);$('#fullscreen').setAttribute('aria-label',active?t('Exit fullscreen','Thoát toàn màn hình'):t('Fullscreen','Toàn màn hình'));}
$('#play').onclick=()=>{if($('#device-voice').checked&&!recorded.track)say();else{if('speechSynthesis'in window)window.speechSynthesis.cancel();utterance=null;speech=null;paused=false;recorded.play();}};
$('#pause').onclick=()=>{recorded.pause();if(speech){window.speechSynthesis.pause();paused=true;$('#play').ariaPressed='false';}};$('#device-voice').onchange=stop;
$('#music').onchange=$('#narration-enabled').onchange=()=>recorded.mix();$('#music-volume').oninput=()=>recorded.mix();$('#audio-seek').oninput=e=>recorded.seek(e.target.value);
$('#voice-volume').oninput=()=>{recorded.mix();if(utterance){const active=speech==='device'&&!paused;stop();if(active)say();}};
const panels=[...document.querySelectorAll('.viewer-panel')];
for(const panel of panels){
  panel.addEventListener('toggle',()=>{if(panel.open){for(const other of panels)if(other!==panel)other.open=false;if(panel.id==='viewer-chat')stop();}});
  panel.querySelector('.panel-close').onclick=()=>{panel.open=false;panel.querySelector('summary').focus();};
}
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const open=panels.find(p=>p.open);if(open){open.open=false;open.querySelector('summary').focus();}else if(document.fullscreenElement){document.exitFullscreen().catch(()=>notice(t('Could not exit fullscreen. Use the browser fullscreen control.','Không thoát được toàn màn hình. Hãy dùng điều khiển toàn màn hình của trình duyệt.'),true));}}});
function revealScene(){if(!matchMedia('(prefers-reduced-motion: reduce)').matches)$('#panorama').animate([{opacity:.65},{opacity:1}],{duration:240,easing:'ease-out'});}
$('#question').onfocus=stop;
$('#question-form').onsubmit=async e=>{e.preventDefault();stop();$('#ask').disabled=true;try{const data=await api(`/published/${tourID}/chat`,{method:'POST',body:{text:$('#question').value,revision:manifest.revision,request_id:requestID(),locale:language(),scene_id:manifest.scenes[index].id}});$('#answer').textContent=data.reply;if(data.scene_id){const target=manifest.scenes.findIndex(s=>s.id===data.scene_id);if(target>=0)await select(target);}}catch(e){$('#answer').textContent=e.message;}finally{$('#ask').disabled=false;}};
window.addEventListener('pagehide',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});document.addEventListener('languagechange',()=>{stop();notice('');renderText();syncFullscreen();});
$('#photo').onerror=()=>notice(t('This scene image is unavailable. Other scenes remain accessible.','Ảnh này không tải được. Bạn vẫn xem được các điểm khác.'),true);
try{
  await api('/session');
  if(draftID||tourID){manifest=await api(draftID?`/drafts/${draftID}`:`/published/${tourID}`);$('#tour-view').hidden=false;document.body.classList.add('is-immersive');
    $('#immersive-title').append($('#tour-heading'));$('#immersive-language').append($('.language-switch'));$('#snapshot-info').append($('#tour-state'));$('#tour-view').append($('#status'));$('#viewer-chat').hidden=!!draftID;$('#preview-label').hidden=!draftID;
    manifest.scenes.forEach((scene,i)=>{const button=node('button',undefined,'scene-thumb');button.type='button';const image=node('img');image.src=scene.thumbnail_url;image.alt='';button.append(image,node('span',scene.name));button.onclick=()=>select(i);$('#scene-nav').append(button);});
    index=manifest.scenes.findIndex(s=>s.id===manifest.start_scene_id);renderText();
  }else{libraryTours=await api('/published');renderLibrary();}
}catch(e){notice(e.message,true);}
