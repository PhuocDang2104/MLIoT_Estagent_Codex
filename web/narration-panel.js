// Creator integration is explicit; this component never loads or translates facts automatically.
export function mountNarrationPanel(container,{getManifest,onManifest,api,intervalMs=700}={}) {
  let manifest=null,job=null,pending=false,disposed=false,timer=null,token=0,request=null;
  const make=(tag,text)=>{const el=document.createElement(tag);if(text)el.textContent=text;return el;};
  const root=make('section');root.className='narration-panel';
  const heading=make('h3','Tour narration · Giọng giới thiệu');
  const disclosure=make('p','AI-generated voice / Giọng AI. Review the exact script before generating. No automatic translation.');
  const scene=make('select'),locale=make('select'),voice=make('select'),text=make('textarea');text.rows=5;text.maxLength=2000;
  scene.setAttribute('aria-label','Scene / Khu');locale.setAttribute('aria-label','Audio language / Ngôn ngữ lời');voice.setAttribute('aria-label','Voice / Giọng');text.setAttribute('aria-label','Approved script / Lời giới thiệu');
  for(const [value,label] of [['en','English'],['vi','Tiếng Việt']]){const o=make('option',label);o.value=value;locale.append(o);}
  const source=make('button','Use source description / Lấy mô tả gốc');source.type='button';
  const approval=make('input');approval.type='checkbox';const approvalLabel=make('label','I reviewed this script and language / Tôi đã duyệt lời và ngôn ngữ ');approvalLabel.prepend(approval);
  const generate=make('button','Generate voice / Sinh giọng'),attach=make('button','Attach to draft / Gắn vào bản nháp'),cancel=make('button','Cancel job / Hủy tác vụ');
  for(const b of [generate,attach,cancel])b.type='button';
  const preview=make('audio');preview.controls=true;preview.preload='metadata';
  const status=make('p');status.setAttribute('role','status');let configured=false;
  root.append(heading,disclosure,scene,locale,voice,source,text,approvalLabel,generate,cancel,preview,attach,status);container.append(root);
  function controls(){for(const el of [scene,locale,voice,text,source,approval])el.disabled=pending||['queued','running'].includes(job?.status);generate.disabled=!configured||!approval.checked||pending||!manifest||!text.value.trim();attach.disabled=!job?.track||job.status!=='completed'||pending||job.attached;cancel.disabled=!job||!['queued','running'].includes(job.status);}
  function reset(){token++;clearTimeout(timer);job=null;request=null;approval.checked=false;preview.pause();preview.removeAttribute('src');preview.load();status.textContent='';controls();}
  async function refresh(){const next=await getManifest();if(disposed)return;manifest=next;const current=scene.value;scene.replaceChildren();for(const s of next?.scenes||[]){const o=make('option',s.name);o.value=s.id;scene.append(o);}if(next?.scenes.some(s=>s.id===current))scene.value=current;controls();}
  const showError=e=>{status.textContent=e.message||'Request failed / Yêu cầu lỗi';};
  source.onclick=()=>{reset();const s=manifest?.scenes.find(s=>s.id===scene.value);text.value=s?.description||'';locale.value=manifest?.locale||'en';status.textContent='Source text copied unchanged; review before generation / Đã chép nguyên mô tả, cần duyệt lại.';controls();};
  for(const el of [scene,locale,voice,text])el.addEventListener('input',reset);
  approval.onchange=controls;
  async function hash(value){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))].map(b=>b.toString(16).padStart(2,'0')).join('');}
  async function follow(id,current){
    if(disposed||current!==token)return;
    try{job=await api(`/narration/jobs/${id}`);if(disposed||current!==token)return;status.textContent=`${job.status}${job.error?': '+job.error:''}`;
      if(job.track){preview.src=job.track.url;preview.load();}
      if(['queued','running'].includes(job.status))timer=setTimeout(()=>follow(id,current),intervalMs);
    }catch(e){showError(e);}finally{controls();}
  }
  generate.onclick=async()=>{
    if(!approval.checked||pending)return;
    pending=true;controls();const current=++token;clearTimeout(timer);
    try{const latest=await getManifest();if(!manifest||latest.revision!==manifest.revision||latest.id!==manifest.id){manifest=latest;reset();throw new Error('Draft changed. Reload and review the script again / Bản nháp đã đổi, hãy duyệt lại.');}
      const body={draft_id:manifest.id,scene_id:scene.value,revision:manifest.revision,locale:locale.value,voice:voice.value,text:text.value,approved:true,script_sha256:await hash(text.value)};
      const fingerprint=JSON.stringify(body);if(!request||request.fingerprint!==fingerprint)request={fingerprint,id:crypto.randomUUID()};
      job=await api('/narration/jobs',{method:'POST',body:{...body,request_id:request.id}});
      status.textContent=job.status;await follow(job.id,current);
    }catch(e){showError(e);}finally{pending=false;controls();}
  };
  cancel.onclick=async()=>{if(!job)return;try{job=await api(`/narration/jobs/${job.id}/cancel`,{method:'POST'});clearTimeout(timer);status.textContent=job.status;}catch(e){showError(e);}controls();};
  attach.onclick=async()=>{if(!job?.track||pending)return;pending=true;controls();try{const next=await api(`/narration/jobs/${job.id}/attach`,{method:'POST',body:{revision:job.revision}});await onManifest(next);manifest=next;job.attached=true;approval.checked=false;status.textContent='Attached. Review the new revision before publishing / Đã gắn. Duyệt lại trước khi xuất bản.';}catch(e){showError(e);}finally{pending=false;controls();}};
  preview.addEventListener('play',()=>{container.dispatchEvent(new CustomEvent('narration-preview-start',{bubbles:true}));});
  const pause=()=>preview.pause();window.addEventListener('pagehide',pause);
  async function init(){try{await refresh();const config=await api('/narration/config');if(disposed)return;configured=config.configured;text.maxLength=config.max_script_chars;voice.replaceChildren();for(const v of config.voices){const o=make('option',v);o.value=v;voice.append(o);}voice.value='coral';locale.value=manifest?.locale||'en';if(!configured)status.textContent=`Narration unavailable / Chưa bật TTS: ${config.reason}`;}catch(e){showError(e);}controls();}
  init();return {refresh:async()=>{reset();await refresh();},pause,destroy(){disposed=true;token++;clearTimeout(timer);pause();window.removeEventListener('pagehide',pause);root.remove();}};
}
