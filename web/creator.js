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
  $('#tour-title').value=manifest.title;$('#revision').textContent=t(`Saved revision ${manifest.revision} · Audio not available`,`Đã lưu bản ${manifest.revision} · Chưa có âm thanh`);
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
  e.preventDefault();if(busy)return;const text=$('#message').value.trim();if(!manifest&&!attachments.length){notice(t('Attach at least one photo first.','Thêm ít nhất một ảnh trước.'),true);return;}if(manifest&&(!text||dirty)){notice(t('Save edits and enter a message first.','Lưu thay đổi và nhập tin nhắn trước.'),true);return;}
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
  $('#published-link').replaceChildren(link(t('Open published tour ↗','Mở tour đã xuất bản ↗'),path),copy);notice(t('Published a separate snapshot. Audio is not available yet.','Đã xuất bản snapshot riêng. Chưa có âm thanh.'));
}catch(e){notice(e.message,true);}finally{setBusy(false);}};
document.addEventListener('languagechange',()=>{notice('');render();});
window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
try{await refreshList();const id=new URLSearchParams(location.search).get('draft');if(id)await load(id);else render();}catch(e){notice(e.message,true);}
