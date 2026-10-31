const t=(en,vi)=>window.estagentI18n?.t(en,vi)??en;
// Creator integration is explicit; this component never loads or translates facts automatically.
export function mountNarrationPanel(container,{getManifest,onManifest,api,intervalMs=700}={}) {
  let manifest=null,job=null,pending=false,disposed=false,timer=null,token=0,request=null;
  const make=(tag,text)=>{const el=document.createElement(tag);if(text)el.textContent=text;return el;};
  const root=make('section');root.className='narration-panel';root.hidden=true;
  const heading=make('h3');
  const disclosure=make('p');
  const scene=make('select'),locale=make('select'),voice=make('select'),text=make('textarea');text.rows=5;text.maxLength=2000;
  for(const [value,label] of [['en','English'],['vi','Tiếng Việt']]){const o=make('option',label);o.value=value;locale.append(o);}
  const source=make('button');source.type='button';
  const approval=make('input');approval.type='checkbox';const approvalLabel=make('label');const approvalText=document.createTextNode('');approvalLabel.append(approval,approvalText);
  const generate=make('button'),attach=make('button'),cancel=make('button');
  for(const b of [generate,attach,cancel])b.type='button';
  const preview=make('audio');preview.controls=true;preview.preload='metadata';
  const status=make('p');status.setAttribute('role','status');let configured=false,statusKind='';
  const jobLabel=()=>({queued:t('Waiting to generate','Đang chờ tạo giọng'),running:t('Generating narration…','Đang tạo lời giới thiệu…'),completed:t('Ready to listen and attach','Sẵn sàng nghe thử và gắn vào tour'),cancelled:t('Cancelled','Đã huỷ'),failed:t('Narration could not be generated. Please try again later.','Chưa tạo được lời giới thiệu. Vui lòng thử lại sau.')})[job?.status]||'';
  function statusText(){status.textContent=statusKind==='copied'?t('Source description copied. Review the script and language before generating.','Đã chép mô tả gốc. Kiểm tra lời và ngôn ngữ trước khi tạo giọng.'):statusKind==='attached'?t('Narration attached. Review this version before publishing.','Đã gắn lời giới thiệu. Kiểm tra bản này trước khi xuất bản.'):statusKind==='error'?t('Could not complete narration. Save draft changes and try again.','Chưa hoàn tất lời giới thiệu. Lưu thay đổi bản nháp rồi thử lại.'):jobLabel();}
  function localize(){
    heading.textContent=t('Tour narration','Lời giới thiệu tour');
    disclosure.textContent=t('AI voice reads the script you approve. Choose its language; the script is not automatically translated.','Giọng AI đọc nội dung bạn duyệt. Chọn ngôn ngữ lời đọc; nội dung không được tự động dịch.');
    source.textContent=t('Use scene description','Dùng mô tả điểm xem');approvalText.textContent=t('I reviewed this script and language','Tôi đã duyệt lời giới thiệu và ngôn ngữ');
    generate.textContent=t('Generate narration','Tạo lời giới thiệu');attach.textContent=t('Attach to draft','Gắn vào bản nháp');cancel.textContent=t('Cancel generation','Huỷ tạo giọng');
    for(const [el,en,vi] of [[scene,'Scene','Điểm xem'],[locale,'Narration language','Ngôn ngữ lời đọc'],[voice,'Voice','Giọng đọc'],[text,'Approved script','Lời giới thiệu đã duyệt']])el.setAttribute('aria-label',t(en,vi));
    statusText();
  }
  document.addEventListener('languagechange',localize);localize();
  root.append(heading,disclosure,scene,locale,voice,source,text,approvalLabel,generate,cancel,preview,attach,status);container.append(root);
  function controls(){for(const el of [scene,locale,voice,text,source,approval])el.disabled=pending||['queued','running'].includes(job?.status);generate.disabled=!configured||!approval.checked||pending||!manifest||!text.value.trim();attach.disabled=!job?.track||job.status!=='completed'||pending||job.attached;cancel.disabled=!job||!['queued','running'].includes(job.status);cancel.hidden=cancel.disabled;preview.hidden=!job?.track;attach.hidden=!job?.track;}
  function reset(){token++;clearTimeout(timer);job=null;request=null;approval.checked=false;preview.pause();preview.removeAttribute('src');preview.load();statusKind='';status.textContent='';controls();}
  async function refresh(){const next=await getManifest();if(disposed)return;manifest=next;const current=scene.value;scene.replaceChildren();for(const s of next?.scenes||[]){const o=make('option',s.name);o.value=s.id;scene.append(o);}if(next?.scenes.some(s=>s.id===current))scene.value=current;controls();}
  const showError=()=>{statusKind='error';statusText();};
  source.onclick=()=>{reset();const s=manifest?.scenes.find(s=>s.id===scene.value);text.value=s?.description||'';locale.value=manifest?.locale||'en';statusKind='copied';statusText();controls();};
  for(const el of [scene,locale,voice,text])el.addEventListener('input',reset);
  approval.onchange=controls;
  async function hash(value){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))].map(b=>b.toString(16).padStart(2,'0')).join('');}
  async function follow(id,current){
    if(disposed||current!==token)return;
    try{job=await api(`/narration/jobs/${id}`);if(disposed||current!==token)return;statusKind='';statusText();
      if(job.track){preview.src=job.track.url;preview.load();}
      if(['queued','running'].includes(job.status))timer=setTimeout(()=>follow(id,current),intervalMs);
    }catch(e){showError(e);}finally{controls();}
  }
  generate.onclick=async()=>{
    if(!approval.checked||pending)return;
    pending=true;controls();const current=++token;clearTimeout(timer);
    try{const latest=await getManifest();if(!manifest||latest.revision!==manifest.revision||latest.id!==manifest.id){manifest=latest;reset();throw new Error(t('Draft changed. Review the script again.','Bản nháp đã đổi. Hãy duyệt lại lời giới thiệu.'));}
      const body={draft_id:manifest.id,scene_id:scene.value,revision:manifest.revision,locale:locale.value,voice:voice.value,text:text.value,approved:true,script_sha256:await hash(text.value)};
      const fingerprint=JSON.stringify(body);if(!request||request.fingerprint!==fingerprint)request={fingerprint,id:crypto.randomUUID()};
      job=await api('/narration/jobs',{method:'POST',body:{...body,request_id:request.id}});
      statusKind='';statusText();await follow(job.id,current);
    }catch(e){showError(e);}finally{pending=false;controls();}
  };
  cancel.onclick=async()=>{if(!job)return;try{job=await api(`/narration/jobs/${job.id}/cancel`,{method:'POST'});clearTimeout(timer);statusKind='';statusText();}catch(e){showError(e);}controls();};
  attach.onclick=async()=>{if(!job?.track||pending)return;const targetJob=job;pending=true;controls();try{const next=await api(`/narration/jobs/${targetJob.id}/attach`,{method:'POST',body:{revision:targetJob.revision}});await onManifest(next);manifest=next;if(job===targetJob)job.attached=true;approval.checked=false;statusKind='attached';statusText();}catch(e){showError(e);}finally{pending=false;controls();}};
  preview.addEventListener('play',()=>{container.dispatchEvent(new CustomEvent('narration-preview-start',{bubbles:true}));});
  const pause=()=>preview.pause();window.addEventListener('pagehide',pause);
  async function init(){try{await refresh();const config=await api('/narration/config');if(disposed)return;configured=config.configured;root.hidden=!configured;text.maxLength=config.max_script_chars;voice.replaceChildren();for(const v of config.voices){const o=make('option',v);o.value=v;voice.append(o);}voice.value='coral';locale.value=manifest?.locale||'en';}catch(e){showError(e);}controls();}
  init();return {refresh:async()=>{reset();await refresh();},pause,destroy(){disposed=true;token++;clearTimeout(timer);pause();window.removeEventListener('pagehide',pause);document.removeEventListener('languagechange',localize);root.remove();}};
}
