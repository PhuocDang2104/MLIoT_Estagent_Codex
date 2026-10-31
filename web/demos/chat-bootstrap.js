import {mountDemoChat} from './chat-panel.js';
const demo='zind-house-000';
async function api(path,options={}){const response=await fetch(path,{credentials:'same-origin',...options});if(!response.ok){let error={};try{error=await response.json();}catch{}throw new Error(typeof error.detail==='string'?error.detail:error.error||`Request failed (${response.status})`);}return response;}
const digest=async text=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('').slice(0,32);
let ready=null;
async function load(){
  const [house,guide]=await Promise.all([api(`/api/demos/${demo}/assets/house/manifest.json`).then(r=>r.json()),api(`/api/demos/${demo}/guide`).then(r=>r.json())]);
  const rows=guide.tracks||guide;
  const keys=rows.map(r=>[r.capture_id,r.room_id,r.locale,r.description||r.script]).sort((a,b)=>{for(let i=0;i<a.length;i++){if(a[i]<b[i])return -1;if(a[i]>b[i])return 1;}return 0;});
  const id=await digest(JSON.stringify(keys)),captures={},byScene={};
  for(const room of house.rooms)for(const capture of room.dollhouseCaptureIds){const scene=await digest(`${demo}\n${capture}`);captures[capture]={scene,room:room.id,label:`${room.label} · ${capture}`};byScene[scene]=capture;}
  const prefix=`/api/tours/published/${id}`;
  const [session,manifest]=await Promise.all([api('/api/tours/session').then(r=>r.json()),api(prefix).then(r=>r.json())]);
  const history=await api(prefix+'/messages').then(r=>r.json());return {prefix,session,manifest,captures,byScene,history};
}
const state=()=>ready??=(load().catch(error=>{ready=null;throw error;}));
function active(){return document.querySelector('#captures button.active')?.dataset.id||null;}
async function navigate(capture){const s=await state(),target=s.captures[capture];if(!target)return;
  document.querySelector('#panoMode')?.click();
  const room=Array.from(document.querySelectorAll('#rooms button')).find(b=>b.dataset.room===target.room);room?.click();
  const select=()=>{const button=Array.from(document.querySelectorAll('#captures button')).find(b=>b.dataset.id===capture);if(button){button.click();return true;}return false;};
  if(select())return;const observer=new MutationObserver(()=>{if(select()){observer.disconnect();clearTimeout(timer);}});observer.observe(document.querySelector('#app'),{childList:true,subtree:true});const timer=setTimeout(()=>observer.disconnect(),5000);
}
let loaded=null;
mountDemoChat({
  loadSession:async()=>{loaded=await state();return {...loaded.session,configured:loaded.session.viewer_configured??loaded.session.configured,history:loaded.history};},
  getContext:()=>{const capture=active();return {capture_id:capture,label:loaded?.captures[capture]?.label||document.querySelector('#rooms button.active')?.textContent};},
  send:async({text,locale,capture_id,request_id})=>{const s=await state();const response=await api(s.prefix+'/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,locale,request_id,revision:s.manifest.revision,scene_id:s.captures[capture_id]?.scene||null})}).then(r=>r.json());return {...response,target_capture_id:s.byScene[response.scene_id]||null};},
  transcribe:async(wav,locale,id)=>{const s=await state();return api(s.prefix+'/transcribe',{method:'POST',headers:{'Content-Type':'audio/wav','X-Request-ID':id,'X-Audio-Locale':locale},body:wav}).then(r=>r.json());},
  speak:async id=>{const s=await state();return api(s.prefix+'/speech',{method:'POST',headers:{'X-Request-ID':id}}).then(r=>r.blob());},navigate,
});
