import { houseModel } from '/studio-model.js';
import { panorama } from '/studio-panorama.js';

const base='/api/demos/seoul-apartment/assets/';
const stage=document.querySelector('#stage'), select=document.querySelector('#captures');
const modes=[...document.querySelectorAll('[data-view]')];
let manifest, exports, dispose=()=>{}, index=0, mode='model';
const narration=document.querySelector('#narration');
function asset(name) {
  // Asset membership is enforced again by the backend. Reject external URLs here.
  if(!/^house\/[a-zA-Z0-9_./-]+$/.test(name)||name.split('/').includes('..')) throw new Error('Invalid sample asset');
  return base+name;
}
function render(nextMode) {
  if(!manifest) return;
  mode=nextMode; narration.pause(); dispose(); stage.replaceChildren(); stage.dataset.view=mode;
  document.querySelector('.capture-controls').hidden=mode!=='panorama';
  modes.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===mode)));
  if(mode==='model') {
    dispose=houseModel(stage,asset(manifest.model),manifest.captures,id=>{
      index=manifest.captures.findIndex(c=>c.checkpoint_id===id); render('panorama'); select.focus();
    }, {cameraDirection:[-.8,1.1,1],framing:.48,exposure:1});
  } else if(mode==='panorama') {
    const capture=manifest.captures[index]; select.value=String(index);
    dispose=panorama(stage,asset(capture.image),capture.initial_yaw_degrees);
  } else if(mode==='video' && exports) {
    const video=document.createElement('video');video.controls=true;video.preload='metadata';video.playsInline=true;video.poster=asset('house/preview.jpg');video.src=exports.video.url;video.className='tour-video';video.setAttribute('aria-label','Seoul apartment narrated tour video');
    const track=document.createElement('track');track.kind='captions';track.srclang='en';track.label='English';track.src=exports.captions.url;video.append(track);video.onplay=()=>narration.pause();stage.append(video);
    dispose=()=>{video.pause();video.removeAttribute('src');video.load();video.remove();};
  } else {
    const img=new Image();img.src=asset(manifest.floorplan);img.alt='Seoul apartment floorplan with source camera locations; approximate scale';img.className='floorplan';stage.append(img);dispose=()=>img.remove();
  }
}
modes.forEach(b=>b.onclick=()=>render(b.dataset.view));
select.onchange=()=>{index=Number(select.value);render('panorama');};
document.querySelector('#previous').onclick=()=>{index=(index+manifest.captures.length-1)%manifest.captures.length;render('panorama');};
document.querySelector('#next').onclick=()=>{index=(index+1)%manifest.captures.length;render('panorama');};
window.addEventListener('pagehide',()=>{narration.pause();dispose();},{once:true});
narration.onplay=()=>stage.querySelector('video')?.pause();
try {
  const response=await fetch(base+'house/manifest.json'); if(!response.ok) throw new Error('Sample unavailable');
  manifest=await response.json();
  manifest.captures.forEach((c,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=`${i+1} / ${manifest.captures.length} · ${c.label}`;select.append(option);});
  render('model');
  // The export exception is an allowlisted Seoul package, never a generation request.
  const media=await fetch('/api/demos/seoul-apartment/exports').catch(()=>null);
  if(media?.ok) {
    exports=await media.json();narration.src=exports.audio.url;
    document.querySelector('[data-view=video]').hidden=false;document.querySelector('.exports').hidden=false;
    for(const [kind,label] of [['video','Video · MP4'],['transcript','Transcript · TXT'],['audio','Voice · WAV']]) {
      const link=document.createElement('a');link.href=exports[kind].download_url;link.download='';link.textContent=label;document.querySelector('#download-links').append(link);
    }
    for(const chapter of exports.chapters) {
      const title=document.createElement('h3');title.textContent=chapter.title;const text=document.createElement('p');text.textContent=chapter.text;document.querySelector('#transcript').append(title,text);
    }
  }
} catch {
  const message=document.createElement('p');message.className='loading';message.setAttribute('role','alert');message.textContent='The sample could not load. Reload to try again, or return to the library.';stage.replaceChildren(message);
}
