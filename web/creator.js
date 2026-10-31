import {$,t,language,api,node,notice,link,requestID} from './tour-common.js';
let manifest=null, session=null, attachments=[], busy=false, dirty=false, pendingCreate=null, pendingTurn=null;
function dirtyState(){dirty=true;$('#reviewed').checked=false;$('#publish').disabled=true;$('#preview').removeAttribute('href');$('#revision').textContent=t('Unsaved changes — save before preview.','Có thay đổi chưa lưu — lưu trước khi xem thử.');}
function resetReview(){dirty=false;$('#reviewed').checked=false;$('#publish').disabled=true;}
function setBusy(value){
  busy=value;
  document.querySelectorAll('#composer button,#composer input,#composer textarea,#draft-editor input,#draft-editor textarea,#draft-editor select,#draft-editor button,#new-tour,#draft-list').forEach(el=>el.disabled=value);
  if(!value)render();
  $('#publish').disabled=value||dirty||!$('#reviewed').checked;
}
function bubble(role,text){const el=node('p',text,`chat-bubble ${role}`);$('#messages').append(el);}
function drawAttachments(){
  $('#attachments').replaceChildren();
  for(const item of attachments){const row=node('div',undefined,'attachment');const img=node('img');img.src=item.preview;img.alt=item.file.name;row.append(img,node('span',item.file.name));
    const remove=node('button','×','quiet');remove.type='button';remove.ariaLabel=t('Remove image','Bỏ ảnh');remove.disabled=busy;remove.onclick=()=>{URL.revokeObjectURL(item.preview);attachments=attachments.filter(a=>a!==item);pendingCreate=null;drawAttachments();};row.append(remove);$('#attachments').append(row);}
}
function attach(files){
  if(manifest){notice(t('Start a new tour to upload another image set.','Bắt đầu tour mới để tải bộ ảnh khác.'),true);return;}
  for(const file of files){if(attachments.length>=20){notice(t('Maximum 20 photos.','Tối đa 20 ảnh.'),true);break;}if(file.size>12*1024*1024){notice(t(`${file.name}: exceeds 12 MB.`,`${file.name}: quá 12 MB.`),true);continue;}attachments.push({file,preview:URL.createObjectURL(file),asset:null});}
  pendingCreate=null;drawAttachments();
}
$('#photos').onchange=e=>{attach(e.target.files);e.target.value='';};
$('#drop-zone').ondragover=e=>e.preventDefault();$('#drop-zone').ondrop=e=>{e.preventDefault();attach(e.dataTransfer.files);};
function field(label,value,change,tag='input'){const wrap=node('label',label);const input=node(tag);input.value=value;input.oninput=()=>{change(input.value);dirtyState();};wrap.append(input);return wrap;}
function render(){
  $('#empty-draft').hidden=!!manifest;$('#draft-editor').hidden=!manifest;$('#drop-zone').hidden=!!manifest;
  $('#send').textContent=manifest?t('Send to assistant ↗','Gửi cho trợ lý ↗'):t('Send & create draft ↗','Gửi & tạo bản nháp ↗');
  $('#connection').textContent=session?.configured?t('AI configured','AI đã cấu hình'):t('AI not connected','AI chưa kết nối');
  if($('#published-link a'))$('#published-link a').textContent=t('Open published tour ↗','Mở tour đã xuất bản ↗');
  if($('#published-link button'))$('#published-link button').textContent=t('Copy link','Sao chép link');
  if(!manifest)return;
  $('#tour-title').value=manifest.title;$('#revision').textContent=t(`Saved revision ${manifest.revision} · Audio: ${manifest.audio.status}`,`Đã lưu bản ${manifest.revision} · Audio: ${manifest.audio.status==='ready'?'đủ lời theo điểm':manifest.audio.status==='partial'?'còn thiếu':'chưa có'}`);
  if(!dirty)$('#preview').href=`/viewer.html?draft=${manifest.id}`;
  $('#scene-cards').replaceChildren();
  manifest.scenes.forEach((scene,index)=>{
    const card=node('article',undefined,'scene-card');card.dataset.scene=scene.id;
    const img=node('img');img.src=scene.thumbnail_url;img.alt=scene.name;card.append(img);
    const body=node('div',undefined,'scene-fields');body.append(field(t('Name','Tên điểm xem'),scene.name,v=>scene.name=v));
    body.append(field(t('Description / subtitle','Mô tả / phụ đề'),scene.description,v=>scene.description=v,'textarea'));
    const projection=node('label',t('Image type — choose explicitly','Loại ảnh — bạn xác định'));const select=node('select');
    for(const [value,label] of [['photo',t('Ordinary photo / gallery','Ảnh thường / gallery')],['cylindrical',t('Panorama / provisional cylinder','Panorama / chiếu trụ tạm')]]){const opt=node('option',label);opt.value=value;select.append(opt);}select.value=scene.projection;
    select.onchange=()=>{scene.projection=select.value;scene.coverage_degrees=select.value==='photo'?null:240;scene.coverage_source=select.value==='photo'?'unknown':'user_provisional';dirtyState();render();};projection.append(select);body.append(projection);
    if(scene.projection==='cylindrical'){
      const angle=field(t('Coverage ° (provisional, not inferred)','Góc phủ ° (tạm, không suy từ ảnh)'),scene.coverage_degrees,v=>{scene.coverage_degrees=Number(v);scene.coverage_source='user_provisional';});const input=angle.querySelector('input');input.type='number';input.min=30;input.max=360;body.append(angle);
      const warning=node('p',t('Uncaptured space stays blank. This is not 3D.','Phần chưa chụp để trống. Đây không phải 3D.'),'hint');body.append(warning);
    }
    const controls=node('div',undefined,'scene-actions');
    for(const [label,delta] of [['↑',-1],['↓',1]]){const button=node('button',label,'quiet');button.type='button';button.ariaLabel=delta<0?t('Move up','Đưa lên'):t('Move down','Đưa xuống');button.disabled=index+delta<0||index+delta>=manifest.scenes.length;button.onclick=()=>{[manifest.scenes[index],manifest.scenes[index+delta]]=[manifest.scenes[index+delta],manifest.scenes[index]];dirtyState();render();};controls.append(button);}
    const start=node('button',scene.id===manifest.start_scene_id?t('Opening scene ✓','Điểm mở đầu ✓'):t('Start here','Bắt đầu ở đây'),'quiet');start.type='button';start.onclick=()=>{manifest.start_scene_id=scene.id;dirtyState();render();};controls.append(start);body.append(controls);card.append(body);$('#scene-cards').append(card);
  });
  renderAudioAttachments();
  if(dirty){$('#preview').removeAttribute('href');$('#revision').textContent=t('Unsaved changes — save before preview.','Có thay đổi chưa lưu — lưu trước khi xem thử.');}
}
async function refreshList(){session=await api('/session');$('#draft-list').replaceChildren(node('option','—'));$('#draft-list').firstChild.value='';for(const d of session.drafts){const opt=node('option',d.title);opt.value=d.id;$('#draft-list').append(opt);}if(manifest)$('#draft-list').value=manifest.id;}
async function load(id){manifest=await api(`/drafts/${id}`);resetReview();$('#messages').replaceChildren();const messages=await api(`/drafts/${id}/messages`);for(const m of messages){if(m.text)bubble(m.role,m.text);}history.replaceState(null,'',`?draft=${id}`);$('#draft-list').value=id;render();}
$('#draft-list').onchange=async e=>{if(!e.target.value)return;if(dirty&&!confirm(t('Discard unsaved edits?','Bỏ thay đổi chưa lưu?')))return;try{await load(e.target.value);}catch(e){notice(e.message,true);}};
$('#new-tour').onclick=()=>{if(dirty&&!confirm(t('Discard unsaved edits?','Bỏ thay đổi chưa lưu?')))return;location.href='/creator.html?new=1';};
$('#tour-title').oninput=e=>{manifest.title=e.target.value;dirtyState();};
$('#save-draft').onclick=async()=>{if(busy)return;setBusy(true);try{
  const scenes=manifest.scenes.map(({image_url,thumbnail_url,...s})=>s);
  manifest=await api(`/drafts/${manifest.id}`,{method:'PUT',body:{revision:manifest.revision,title:manifest.title,locale:language(),scenes,start_scene_id:manifest.start_scene_id}});
  resetReview();await refreshList();render();notice(t('Changes saved. Open the preview to review.','Đã lưu. Mở xem thử để kiểm tra.'));
}catch(e){notice(e.message,true);}finally{setBusy(false);}};
$('#composer').onsubmit=async e=>{
  e.preventDefault();$('#creator-audio-preview').pause();if(busy)return;const text=$('#message').value.trim();if(!manifest&&!attachments.length){notice(t('Attach at least one photo first.','Thêm ít nhất một ảnh trước.'),true);return;}if(manifest&&(!text||dirty)){notice(t('Save edits and enter a message first.','Lưu thay đổi và nhập tin nhắn trước.'),true);return;}
  setBusy(true);notice(t('Working…','Đang xử lý…'));
  try{
    if(!manifest){
      for(const item of attachments){if(!item.asset){notice(t(`Uploading ${item.file.name}…`,`Đang tải ${item.file.name}…`));item.asset=await api('/assets',{method:'POST',body:item.file,binary:true});}}
      const ids=attachments.map(a=>a.asset.id);if(new Set(ids).size!==ids.length)throw new Error(t('The same photo is attached twice. Remove the duplicate.','Cùng một ảnh được thêm hai lần. Bỏ ảnh trùng rồi gửi lại.'));
      pendingCreate??={request_id:requestID(),asset_ids:ids,text,locale:language(),title:t('My space','Không gian của tôi')};
      manifest=await api('/drafts',{method:'POST',body:pendingCreate});pendingCreate=null;
      for(const a of attachments)URL.revokeObjectURL(a.preview);attachments=[];drawAttachments();await refreshList();await load(manifest.id);
      notice(t('Visual draft saved. Labels are placeholders; review each scene.','Đã lưu bản nháp hình ảnh. Tên đang là nhãn tạm; hãy kiểm tra từng điểm.'));
    }
    if(text){
      // Actual backend; no local fake NLP. Failure keeps the message for retry.
      const fingerprint=JSON.stringify({id:manifest.id,text,revision:manifest.revision,locale:language()});
      if(pendingTurn?.fingerprint!==fingerprint)pendingTurn={fingerprint,body:{text,request_id:requestID(),revision:manifest.revision,locale:language()}};
      const result=await api(`/drafts/${manifest.id}/chat`,{method:'POST',body:pendingTurn.body});
      pendingTurn=null;
      manifest=result.manifest;resetReview();await load(manifest.id);$('#message').value='';notice(t('Assistant response saved. Review any proposed edits.','Đã lưu phản hồi trợ lý. Kiểm tra các thay đổi được đề xuất.'));
    }
  }catch(error){notice(error.message,true);}finally{render();setBusy(false);}
};
$('#reviewed').onchange=()=>{$('#publish').disabled=!$('#reviewed').checked||dirty||busy;};
$('#publish').onclick=async()=>{if(busy||dirty||!$('#reviewed').checked)return;setBusy(true);try{
  await api(`/drafts/${manifest.id}/review`,{method:'POST',body:{revision:manifest.revision}});
  const published=await api(`/drafts/${manifest.id}/publish`,{method:'POST',body:{revision:manifest.revision}});
  const path=`/viewer.html?tour=${published.id}`;
  const copy=node('button',t('Copy link','Sao chép link'),'quiet');copy.type='button';copy.onclick=async()=>{try{await navigator.clipboard.writeText(new URL(path,location.origin).href);notice(t('Link copied.','Đã sao chép link.'));}catch{notice(t('Copy the address after opening the tour.','Mở tour rồi sao chép địa chỉ trên thanh trình duyệt.'));}};
  $('#published-link').replaceChildren(link(t('Open published tour ↗','Mở tour đã xuất bản ↗'),path),copy);notice(t('Published a separate snapshot. Audio availability is shown for each scene.','Đã xuất bản snapshot riêng. Tình trạng audio được hiển thị theo từng điểm.'));
}catch(e){notice(e.message,true);}finally{setBusy(false);}};
document.addEventListener('languagechange',()=>{notice('');render();});
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
try{await refreshList();const id=new URLSearchParams(location.search).get('draft');if(id)await load(id);else render();}catch(e){notice(e.message,true);}


function audioBindings(){return (manifest.audio.narration||[]).map(n=>({scene_id:n.scene_id,locale:n.locale,transcript:n.transcript,asset_id:n.track.asset_id}));}
async function saveAudio(music,narration){
  manifest=await api(`/drafts/${manifest.id}/audio`,{method:'PUT',body:{revision:manifest.revision,music_asset_id:music,narration}});
  resetReview();render();notice(t('Audio saved. Review this new revision before publishing.','Đã lưu audio. Cần xem thử và duyệt revision mới trước khi xuất bản.'));
}
function renderAudioAttachments(){
  const selected=$('#audio-scene').value;$('#audio-scene').replaceChildren();
  for(const scene of manifest.scenes){const option=node('option',scene.name);option.value=scene.id;$('#audio-scene').append(option);}
  if(manifest.scenes.some(s=>s.id===selected))$('#audio-scene').value=selected;
  $('#audio-locale').textContent=t(`Narration language: ${manifest.locale.toUpperCase()}. Changing the interface language does not translate recordings.`,`Ngôn ngữ bản thu: ${manifest.locale.toUpperCase()}. Đổi ngôn ngữ giao diện không dịch bản thu.`);
  $('#audio-attachments').replaceChildren();
  const entries=[...(manifest.audio.music?[{label:t('Music','Nhạc nền'),track:manifest.audio.music,kind:'music'}]:[]),...(manifest.audio.narration||[]).map(n=>({label:`${manifest.scenes.find(s=>s.id===n.scene_id)?.name} · ${n.locale.toUpperCase()}`,track:n.track,kind:'narration',scene_id:n.scene_id,locale:n.locale}))];
  if(!entries.length)$('#audio-attachments').append(node('p',t('No uploaded audio. Visual tour remains available.','Chưa tải audio. Tour hình ảnh vẫn hoạt động.'),'hint'));
  for(const entry of entries){
    const row=node('div',undefined,'attached-audio');row.append(node('strong',entry.label),node('span',`${entry.track.duration_seconds.toFixed(2)}s · ${entry.track.source_label}`),node('small',`${entry.track.rights}: ${entry.track.rights_note}`));
    const preview=node('button',t('Listen','Nghe thử'),'quiet');preview.type='button';preview.onclick=async()=>{const player=$('#creator-audio-preview');player.pause();player.src=entry.track.url;player.hidden=false;try{await player.play();}catch{notice(t('Audio could not play. Check the file or browser playback permission.','Không phát được audio. Kiểm tra file hoặc quyền phát của trình duyệt.'),true);}};
    const remove=node('button',t('Remove','Gỡ'),'quiet');remove.type='button';remove.onclick=async()=>{if(busy||dirty){notice(t('Save visual edits first.','Lưu thay đổi hình ảnh trước.'),true);return;}setBusy(true);$('#creator-audio-preview').pause();try{await saveAudio(entry.kind==='music'?null:manifest.audio.music?.asset_id||null,audioBindings().filter(n=>entry.kind!=='narration'||n.scene_id!==entry.scene_id||n.locale!==entry.locale));}catch(e){notice(e.message,true);}finally{setBusy(false);}};
    row.append(preview,remove);$('#audio-attachments').append(row);
  }
  if((manifest.audio.narration||[]).some(n=>n.locale!==manifest.locale)){
    const clear=node('button',t('Remove recordings from the previous language','Gỡ bản thu thuộc ngôn ngữ cũ'),'quiet');clear.type='button';clear.onclick=async()=>{if(busy||dirty)return;setBusy(true);try{await saveAudio(manifest.audio.music?.asset_id||null,audioBindings().filter(n=>n.locale===manifest.locale));}catch(e){notice(e.message,true);}finally{setBusy(false);}};$('#audio-attachments').append(clear);
  }
}
$('#audio-upload-form').onsubmit=async event=>{
  event.preventDefault();if(busy||!manifest)return;if(dirty){notice(t('Save visual changes before attaching audio.','Lưu thay đổi hình ảnh trước khi gắn audio.'),true);return;}
  const file=$('#audio-file').files[0];if(!file)return;if(file.size>20*1024*1024){notice(t('WAV exceeds 20 MiB.','WAV vượt 20 MiB.'),true);return;}
  const kind=$('#audio-kind').value,scene=$('#audio-scene').value,transcript=$('#audio-transcript').value.trim();
  const metadata={source_label:$('#audio-source').value,rights:$('#audio-rights').value,rights_note:$('#audio-rights-note').value};
  setBusy(true);$('#creator-audio-preview').pause();notice(t('Validating WAV and uploading…','Đang kiểm WAV và tải lên…'));
  try{
    const response=await fetch('/api/tours/audio-assets',{method:'POST',headers:{'Content-Type':'audio/wav','X-Audio-Metadata':encodeURIComponent(JSON.stringify(metadata))},body:file});
    const track=await response.json();if(!response.ok)throw new Error(typeof track.detail==='string'?track.detail:track.error||t('Audio upload failed.','Tải audio thất bại.'));
    let narrations=audioBindings(),music=manifest.audio.music?.asset_id||null;
    if(kind==='music')music=track.asset_id;else{narrations=narrations.filter(n=>n.scene_id!==scene||n.locale!==manifest.locale);narrations.push({scene_id:scene,locale:manifest.locale,transcript,asset_id:track.asset_id});}
    await saveAudio(music,narrations);$('#audio-file').value='';$('#audio-transcript').value='';
  }catch(error){notice(error.message,true);}finally{setBusy(false);}
};
