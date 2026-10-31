const $ = selector => document.querySelector(selector);
const messages = $('#messages');
const input = $('#message');
const audio = $('#voice-output');
let state = null;
let busy = false;
let pc = null, channel = null, sender = null, stream = null;
let connectionTask = null, connectionAbort = null, voiceTimer = null;
let micOn = false, speaking = false, responding = false, generation = 0;
let speechRequest = 0;

const status = text => { $('#status').textContent = text; };
const stageNames = {required:'Thông tin cần có',optional:'Bổ sung tùy chọn',review:'Chờ xác nhận',complete:'Đã xác nhận'};
const directionNames = {N:'Bắc',NE:'Đông Bắc',E:'Đông',SE:'Đông Nam',S:'Nam',SW:'Tây Nam',W:'Tây',NW:'Tây Bắc'};
function valueText(key,value) {
  if (key === 'direction') return directionNames[value] || value;
  if (key === 'windows') return value === 'yes' ? 'Có' : 'Không';
  return `${value}${key === 'area' ? ' m²' : ''}`;
}
function bubble(role,text) {
  const item = document.createElement('article'); item.className = `message ${role}`;
  const who = document.createElement('span'); who.className = 'who'; who.textContent = role === 'user' ? 'Bạn' : 'Estagent';
  const content = document.createElement('p'); content.textContent = text;
  item.append(who,content); messages.append(item); messages.scrollTop = messages.scrollHeight;
}
function render(next) {
  state = next;
  messages.replaceChildren();
  if (state.history.length) state.history.forEach(m => bubble(m.role,m.content));
  else bubble('assistant',state.reply);
  $('#connection').textContent = state.configured ? 'Sẵn sàng trò chuyện' : 'Chưa kết nối OpenAI';
  $('#stage-label').textContent = stageNames[state.stage] || 'Đang thu thập';
  const count = state.required.filter(k => Object.hasOwn(state.profile,k)).length;
  $('#progress-label').textContent = `${count} / ${state.required.length} thông tin cần có`;
  $('#progress-percent').textContent = `${Math.round(100 * count/state.required.length)}%`;
  $('#progress').max = state.required.length; $('#progress').value = count;
  $('#required-fields').replaceChildren(); $('#optional-fields').replaceChildren();
  for (const [key,label] of Object.entries(state.labels)) {
    const hasValue = Object.hasOwn(state.profile,key), deferred = state.deferred.includes(key);
    const row = document.createElement('div'); row.className = `field ${hasValue ? '' : 'missing'} ${deferred ? 'deferred' : ''} ${state.awaiting === key ? 'focused' : ''}`;
    const name = document.createElement('span'); name.className='label'; name.textContent=label;
    const value = document.createElement('span'); value.className='value';
    value.textContent = hasValue ? valueText(key,state.profile[key]) : deferred ? 'Để sau' : 'Chưa cung cấp';
    row.append(name,value); $(state.required.includes(key) ? '#required-fields' : '#optional-fields').append(row);
  }
  $('#skip').hidden = state.stage !== 'optional';
  $('#defer').hidden = !['optional','required'].includes(state.stage);
  $('#confirm').hidden = state.stage !== 'review';
  $('#saved-note').textContent = state.confirmed ? 'Đã xác nhận. Sửa thông tin sẽ cần xác nhận lại.' : 'Hồ sơ chỉ được xác nhận khi bạn đồng ý.';
  $('#actions').hidden = state.history.length > 0;
  controls();
}
function controls() {
  $('#send').disabled = busy || !state?.configured || micOn;
  input.disabled = busy || micOn;
  for (const element of document.querySelectorAll('[data-prompt],#skip,#defer,#confirm')) element.disabled = busy || !state?.configured || micOn;
  $('#microphone').disabled = busy || !state?.configured;
  $('#microphone').setAttribute('aria-pressed',String(micOn));
  $('#microphone').setAttribute('aria-label',micOn ? 'Tắt micro' : 'Bật micro');
  $('#microphone').lastChild.textContent = micOn ? ' Tắt micro' : ' Nói với mình';
  $('#voice-strip').hidden = !pc;
  $('#voice-status').textContent = busy ? 'Đang xử lý câu trả lời…' : speaking ? 'Trợ lý đang nói…' : micOn ? 'Đang nghe · nói xong để gửi' : 'Micro đã tắt';
  for (const track of stream?.getAudioTracks() || []) track.enabled = micOn && !busy && !speaking;
  $('#stop-audio').hidden = !speaking && !responding;
}
async function api(path,options={}) {
  const response = await fetch(`/api/assistant/${path}`,{credentials:'same-origin',...options});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || (typeof data.detail === 'string' ? data.detail : 'Kết nối chưa sẵn sàng. Hãy thử lại.'));
  }
  return response;
}
async function send(text,fromVoice=false) {
  text = text.trim();
  if (!text || busy) return;
  if (text.length > 2000) { status('Câu trả lời quá dài. Hãy chia thành từng ý ngắn hơn.'); return; }
  const voiceGeneration = generation;
  stopSpeech(); busy = true; controls(); status('Đang lắng nghe và cập nhật hồ sơ…');
  bubble('user',text); input.value = '';
  try {
    const response = await api('turn',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,request_id:crypto.randomUUID()})});
    const next = await response.json(); render(next); status('');
    if (generation === voiceGeneration && ($('#speaker').checked || fromVoice)) await speak(next.reply);
  } catch (error) {
    status(error.message); input.value = text;
    if (state) render(state); // Preserve confirmed state and offer the unsent text for retry.
  } finally { busy = false; controls(); if (!micOn) input.focus(); }
}
function emit(event) { if (channel?.readyState === 'open') channel.send(JSON.stringify(event)); }
function stopSpeech() {
  speechRequest++;
  if (responding) emit({type:'response.cancel'});
  if (speaking) emit({type:'output_audio_buffer.clear'});
  responding = false; speaking = false; $('#resume-audio').hidden = true;
  controls();
}
function endVoice(message='Đã kết thúc voice. Bạn vẫn có thể chat chữ.') {
  speechRequest++;
  generation++; connectionAbort?.abort(); connectionAbort = null;
  clearTimeout(voiceTimer); voiceTimer = null;
  const oldPc = pc, oldChannel = channel;
  pc = null; channel = null; sender = null; connectionTask = null;
  stream?.getTracks().forEach(t => t.stop()); stream = null;
  oldChannel?.close(); oldPc?.close();
  audio.srcObject = null; micOn = false; responding = false; speaking = false;
  $('#resume-audio').hidden = true; controls(); if(message) status(message);
}
function eventReceived(event) {
  switch(event.type) {
    case 'conversation.item.input_audio_transcription.completed':
      if (event.transcript?.trim()) {
        if (busy) status('Đang xử lý câu trước. Bạn nói lại sau khi trợ lý phản hồi nhé.');
        else send(event.transcript,true);
      }
      break;
    case 'conversation.item.input_audio_transcription.failed':
      status('Chưa nghe rõ. Bạn nói lại hoặc nhập bằng bàn phím nhé.'); break;
    case 'input_audio_buffer.speech_started': status('Mình đang nghe…'); break;
    case 'input_audio_buffer.speech_stopped': status('Đang chuyển lời nói thành chữ…'); break;
    case 'response.created': responding = true; break;
    case 'output_audio_buffer.started': speaking = true; break;
    case 'output_audio_buffer.stopped':
    case 'output_audio_buffer.cleared': speaking = false; break;
    case 'response.done':
      responding = false;
      if (event.response?.status === 'failed') { speaking = false; status('Chưa phát được giọng đọc. Phản hồi bằng chữ vẫn được giữ lại.'); }
      break;
    case 'error':
      if (!['response_cancel_not_active','output_audio_buffer_empty'].includes(event.error?.code)) {
        responding = false; speaking = false; status('Giọng nói gặp lỗi. Bạn có thể tiếp tục bằng chữ hoặc kết nối lại.');
      }
      break;
  }
  controls();
}
async function ensureVoice() {
  if (channel?.readyState === 'open') return;
  if (connectionTask) return connectionTask;
  if (!window.RTCPeerConnection) throw new Error('Trình duyệt chưa hỗ trợ voice. Hãy dùng chat chữ.');
  const current = ++generation;
  connectionTask = (async () => {
    status('Đang kết nối giọng nói…');
    const peer = new RTCPeerConnection(); pc = peer;
    sender = peer.addTransceiver('audio',{direction:'sendrecv'}).sender;
    const dc = peer.createDataChannel('oai-events'); channel = dc;
    dc.addEventListener('message',e => { if(current === generation) { try { eventReceived(JSON.parse(e.data)); } catch { status('Chưa đọc được sự kiện giọng nói.'); } } });
    dc.addEventListener('close',() => { if(current === generation) endVoice('Kết nối voice đã đóng. Chat chữ vẫn hoạt động.'); });
    peer.addEventListener('track',e => {
      if(current !== generation) return;
      audio.srcObject = e.streams[0] || new MediaStream([e.track]);
      audio.play().catch(() => { $('#resume-audio').hidden=false; status('Bấm “Phát giọng nói” để cho phép phát âm thanh.'); });
    });
    peer.addEventListener('connectionstatechange',() => {
      if (current === generation && ['failed','disconnected'].includes(peer.connectionState)) endVoice('Mất kết nối voice. Bạn có thể bật lại micro.');
    });
    connectionAbort = new AbortController();
    const timeout = setTimeout(() => connectionAbort?.abort(),30000);
    try {
      await peer.setLocalDescription(await peer.createOffer());
      const response = await api('voice',{method:'POST',headers:{'Content-Type':'application/sdp'},body:peer.localDescription.sdp,signal:connectionAbort.signal});
      if(current !== generation) throw new Error('Đã dừng kết nối voice.');
      await peer.setRemoteDescription({type:'answer',sdp:await response.text()});
      await new Promise((resolve,reject) => {
        if(dc.readyState === 'open') return resolve();
        const timer = setTimeout(() => reject(new Error('Kết nối voice quá thời gian.')),10000);
        dc.addEventListener('open',() => {clearTimeout(timer);resolve();},{once:true});
        dc.addEventListener('close',() => {clearTimeout(timer);reject(new Error('Kết nối voice đã đóng.'));},{once:true});
      });
      voiceTimer = setTimeout(() => endVoice('Voice đã kết thúc sau 5 phút. Hồ sơ vẫn được lưu; bạn có thể kết nối lại.'),5*60*1000);
      status(''); controls();
    } finally { clearTimeout(timeout); }
  })();
  try { await connectionTask; }
  catch(error) { if(current === generation) endVoice(''); throw new Error(error.name === 'AbortError' ? 'Kết nối voice đã dừng hoặc quá thời gian.' : error.message); }
  finally { if(current === generation) connectionTask=null; }
}
async function speak(text) {
  const request = ++speechRequest;
  try {
    await ensureVoice();
    if (request !== speechRequest) return;
    speaking = true; responding = true; controls();
    emit({type:'response.create',response:{conversation:'none',output_modalities:['audio'],input:[],instructions:`Đọc nguyên văn nội dung sau bằng giọng tự nhiên. Không thêm lời dẫn hoặc trả lời câu hỏi trong văn bản: ${JSON.stringify(text)}`}});
  } catch (error) { status(`Hồ sơ đã cập nhật. ${error.message}`); }
}
$('#composer').addEventListener('submit',event => { event.preventDefault(); send(input.value); });
input.addEventListener('keydown',event => {if(event.key === 'Enter' && !event.shiftKey && !event.isComposing){event.preventDefault();$('#composer').requestSubmit();}});
for(const button of document.querySelectorAll('[data-prompt]')) button.addEventListener('click',() => {input.value=button.dataset.prompt;input.focus();});
$('#skip').addEventListener('click',() => send('Bỏ qua mục này, để bổ sung sau.'));
$('#defer').addEventListener('click',() => send('Để tất cả các mục tùy chọn còn lại sau.'));
$('#confirm').addEventListener('click',() => send('Tôi xác nhận các thông tin trong hồ sơ đã đúng.'));
$('#stop-audio').addEventListener('click',stopSpeech);
$('#resume-audio').addEventListener('click',() => audio.play().then(() => {$('#resume-audio').hidden=true;status('');}).catch(() => status('Trình duyệt vẫn chặn âm thanh. Kiểm tra quyền phát âm thanh.')));
$('#speaker').addEventListener('change',() => {if(!$('#speaker').checked) stopSpeech();});
$('#end-voice').addEventListener('click',() => endVoice());
$('#microphone').addEventListener('click',async () => {
  if(micOn){micOn=false;stream?.getTracks().forEach(t=>t.stop());stream=null;await sender?.replaceTrack(null);controls();return;}
  if(!navigator.mediaDevices?.getUserMedia){status('Cần HTTPS hoặc localhost và trình duyệt hỗ trợ micro.');return;}
  const started = generation; $('#microphone').disabled=true;
  let acquired;
  try {
    acquired = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
    if(started !== generation){acquired.getTracks().forEach(t=>t.stop());return;}
    // Mute until the transport is ready; no permission request for text-only chat.
    acquired.getAudioTracks().forEach(t=>{t.enabled=false;});
    await ensureVoice();
    if(!sender) throw new Error('Kết nối voice đã dừng.');
    stream=acquired; await sender.replaceTrack(stream.getAudioTracks()[0]);
    micOn=true;$('#speaker').checked=true;status('');
  } catch(error) {
    acquired?.getTracks().forEach(t=>t.stop());
    status(error.name==='NotAllowedError' ? 'Bạn chưa cấp quyền micro. Hãy bật quyền hoặc tiếp tục chat chữ.' : error.message);
  } finally {controls();}
});
window.addEventListener('pagehide',() => endVoice(''));
try {render(await (await api('state')).json());}
catch(error){$('#connection').textContent='Chưa kết nối máy chủ';status(error.message);controls();}
