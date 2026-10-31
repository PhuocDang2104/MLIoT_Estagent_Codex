import { houseModel } from '/studio-model.js';
import { panorama } from '/studio-panorama.js';

const base='/api/demos/seoul-apartment/assets/';
const stage=document.querySelector('#stage'), select=document.querySelector('#captures');
const modes=[...document.querySelectorAll('[data-view]')];
let manifest, dispose=()=>{}, index=0, mode='model';
function asset(name) {
  // Asset membership is enforced again by the backend. Reject external URLs here.
  if(!/^house\/[a-zA-Z0-9_./-]+$/.test(name)||name.split('/').includes('..')) throw new Error('Invalid sample asset');
  return base+name;
}
function render(nextMode) {
  if(!manifest) return;
  mode=nextMode; dispose(); stage.replaceChildren(); stage.dataset.view=mode;
  document.querySelector('.capture-controls').hidden=mode!=='panorama';
  modes.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===mode)));
  if(mode==='model') {
    dispose=houseModel(stage,asset(manifest.model),manifest.captures,id=>{
      index=manifest.captures.findIndex(c=>c.checkpoint_id===id); render('panorama'); select.focus();
    }, {cameraDirection:[-.8,1.1,1],framing:.48,exposure:1});
  } else if(mode==='panorama') {
    const capture=manifest.captures[index]; select.value=String(index);
    dispose=panorama(stage,asset(capture.image),capture.initial_yaw_degrees);
  } else {
    const img=new Image();img.src=asset(manifest.floorplan);img.alt='Seoul apartment floorplan with source camera locations; approximate scale';img.className='floorplan';stage.append(img);dispose=()=>img.remove();
  }
}
modes.forEach(b=>b.onclick=()=>render(b.dataset.view));
select.onchange=()=>{index=Number(select.value);render('panorama');};
document.querySelector('#previous').onclick=()=>{index=(index+manifest.captures.length-1)%manifest.captures.length;render('panorama');};
document.querySelector('#next').onclick=()=>{index=(index+1)%manifest.captures.length;render('panorama');};
window.addEventListener('pagehide',()=>dispose(),{once:true});
try {
  const response=await fetch(base+'house/manifest.json'); if(!response.ok) throw new Error('Sample unavailable');
  manifest=await response.json();
  manifest.captures.forEach((c,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=`${i+1} / ${manifest.captures.length} · ${c.label}`;select.append(option);});
  render('model');
} catch {
  const message=document.createElement('p');message.className='loading';message.setAttribute('role','alert');message.textContent='The sample could not load. Reload to try again, or return to the library.';stage.replaceChildren(message);
}
