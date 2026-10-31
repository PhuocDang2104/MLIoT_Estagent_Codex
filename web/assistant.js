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
const stageNames = {required:'Required information',optional:'Optional information',review:'Awaiting confirmation',complete:'Confirmed'};
const directionNames = {N:'North',NE:'Northeast',E:'East',SE:'Southeast',S:'Nam',SW:'Southwest',W:'West',NW:'Northwest'};
function valueText(key,value) {
  if (key === 'direction') return directionNames[value] || value;
  if (key === 'windows') return value === 'yes' ? 'Yes' : 'No';
  return `${value}${key === 'area' ? ' m²' : ''}`;
}
function bubble(role,text) {
  const item = document.createElement('article'); item.className = `message ${role}`;
  const who = document.createElement('span'); who.className = 'who'; who.textContent = role === 'user' ? 'You' : 'Estagent';
  const content = document.createElement('p'); content.textContent = text;
  item.append(who,content); messages.append(item); messages.scrollTop = messages.scrollHeight;
}
function render(next) {
  state = next;
  messages.replaceChildren();
  if (state.history.length) state.history.forEach(m => bubble(m.role,m.content));
  else bubble('assistant',state.reply);
  $('#connection').textContent = state.configured ? 'Ready to chat' : 'OpenAI is not connected';
  $('#stage-label').textContent = stageNames[state.stage] || 'Collecting details';
  const count = state.required.filter(k => Object.hasOwn(state.profile,k)).length;
  $('#progress-label').textContent = `${count} / ${state.required.length} required details`;
  $('#progress-percent').textContent = `${Math.round(100 * count/state.required.length)}%`;
  $('#progress').max = state.required.length; $('#progress').value = count;
  $('#required-fields').replaceChildren(); $('#optional-fields').replaceChildren();
  for (const [key,label] of Object.entries(state.labels)) {
    const hasValue = Object.hasOwn(state.profile,key), deferred = state.deferred.includes(key);
    const row = document.createElement('div'); row.className = `field ${hasValue ? '' : 'missing'} ${deferred ? 'deferred' : ''} ${state.awaiting === key ? 'focused' : ''}`;
    const name = document.createElement('span'); name.className='label'; name.textContent=label;
    const value = document.createElement('span'); value.className='value';
    value.textContent = hasValue ? valueText(key,state.profile[key]) : deferred ? 'Later' : 'Not provided';
    row.append(name,value); $(state.required.includes(key) ? '#required-fields' : '#optional-fields').append(row);
  }
  $('#skip').hidden = state.stage !== 'optional';
  $('#defer').hidden = !['optional','required'].includes(state.stage);
  $('#confirm').hidden = state.stage !== 'review';
  $('#saved-note').textContent = state.confirmed ? 'Confirmed. Editing information will require confirmation again.' : 'The brief is confirmed only with your approval.';
  $('#actions').hidden = state.history.length > 0;
  controls();
}
function controls() {
  $('#send').disabled = busy || !state?.configured || micOn;
  input.disabled = busy || micOn;
  for (const element of document.querySelectorAll('[data-prompt],#skip,#defer,#confirm')) element.disabled = busy || !state?.configured || micOn;
  $('#microphone').disabled = busy || !state?.configured;
  $('#microphone').setAttribute('aria-pressed',String(micOn));
  $('#microphone').setAttribute('aria-label',micOn ? 'Mute microphone' : 'Enable microphone');
  $('#microphone').lastChild.textContent = micOn ? ' Mute microphone' : ' Talk to me';
  $('#voice-strip').hidden = !pc;
  $('#voice-status').textContent = busy ? 'Processing your answer…' : speaking ? 'The assistant is speaking…' : micOn ? 'Listening · finish speaking to send' : 'Microphone muted';
  for (const track of stream?.getAudioTracks() || []) track.enabled = micOn && !busy && !speaking;
  $('#stop-audio').hidden = !speaking && !responding;
}
async function api(path,options={}) {
  const response = await fetch(`/api/assistant/${path}`,{credentials:'same-origin',...options});
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.error || (typeof data.detail === 'string' ? data.detail : 'The connection is not ready. Try again.'));
  }
  return response;
}
async function send(text,fromVoice=false) {
  text = text.trim();
  if (!text || busy) return;
  if (text.length > 2000) { status('Your answer is too long. Please split it into shorter messages.'); return; }
  const voiceGeneration = generation;
  stopSpeech(); busy = true; controls(); status('Listening and updating your brief…');
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
function endVoice(message='Voice session ended. You can still use text chat.') {
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
        if (busy) status('Processing the previous answer. Speak again after the assistant responds.');
        else send(event.transcript,true);
      }
      break;
    case 'conversation.item.input_audio_transcription.failed':
      status('Could not hear clearly. Please repeat or type your answer.'); break;
    case 'input_audio_buffer.speech_started': status('Listening…'); break;
    case 'input_audio_buffer.speech_stopped': status('Transcribing your speech…'); break;
    case 'response.created': responding = true; break;
    case 'output_audio_buffer.started': speaking = true; break;
    case 'output_audio_buffer.stopped':
    case 'output_audio_buffer.cleared': speaking = false; break;
    case 'response.done':
      responding = false;
      if (event.response?.status === 'failed') { speaking = false; status('Could not play the voice response. The text response is preserved.'); }
      break;
    case 'error':
      if (!['response_cancel_not_active','output_audio_buffer_empty'].includes(event.error?.code)) {
        responding = false; speaking = false; status('Voice encountered an error. Continue by text or reconnect.');
      }
      break;
  }
  controls();
}
async function ensureVoice() {
  if (channel?.readyState === 'open') return;
  if (connectionTask) return connectionTask;
  if (!window.RTCPeerConnection) throw new Error('This browser does not support voice. Please use text chat.');
  const current = ++generation;
  connectionTask = (async () => {
    status('Connecting voice…');
    const peer = new RTCPeerConnection(); pc = peer;
    sender = peer.addTransceiver('audio',{direction:'sendrecv'}).sender;
    const dc = peer.createDataChannel('oai-events'); channel = dc;
    dc.addEventListener('message',e => { if(current === generation) { try { eventReceived(JSON.parse(e.data)); } catch { status('Could not read the voice event.'); } } });
    dc.addEventListener('close',() => { if(current === generation) endVoice('Voice connection closed. Text chat still works.'); });
    peer.addEventListener('track',e => {
      if(current !== generation) return;
      audio.srcObject = e.streams[0] || new MediaStream([e.track]);
      audio.play().catch(() => { $('#resume-audio').hidden=false; status('Press “Play voice” to allow audio playback.'); });
    });
    peer.addEventListener('connectionstatechange',() => {
      if (current === generation && ['failed','disconnected'].includes(peer.connectionState)) endVoice('Voice connection lost. You can enable the microphone again.');
    });
    connectionAbort = new AbortController();
    const timeout = setTimeout(() => connectionAbort?.abort(),30000);
    try {
      await peer.setLocalDescription(await peer.createOffer());
      const response = await api('voice',{method:'POST',headers:{'Content-Type':'application/sdp'},body:peer.localDescription.sdp,signal:connectionAbort.signal});
      if(current !== generation) throw new Error('Voice connection stopped.');
      await peer.setRemoteDescription({type:'answer',sdp:await response.text()});
      await new Promise((resolve,reject) => {
        if(dc.readyState === 'open') return resolve();
        const timer = setTimeout(() => reject(new Error('Voice connection timed out.')),10000);
        dc.addEventListener('open',() => {clearTimeout(timer);resolve();},{once:true});
        dc.addEventListener('close',() => {clearTimeout(timer);reject(new Error('Voice connection closed.'));},{once:true});
      });
      voiceTimer = setTimeout(() => endVoice('Voice ended after 5 minutes. Your brief is saved; you can reconnect.'),5*60*1000);
      status(''); controls();
    } finally { clearTimeout(timeout); }
  })();
  try { await connectionTask; }
  catch(error) { if(current === generation) endVoice(''); throw new Error(error.name === 'AbortError' ? 'Voice connection stopped or timed out.' : error.message); }
  finally { if(current === generation) connectionTask=null; }
}
async function speak(text) {
  const request = ++speechRequest;
  try {
    await ensureVoice();
    if (request !== speechRequest) return;
    speaking = true; responding = true; controls();
    emit({type:'response.create',response:{conversation:'none',output_modalities:['audio'],input:[],instructions:`Read the following text verbatim in a natural voice. Do not add an introduction or answer questions within the text: ${JSON.stringify(text)}`}});
  } catch (error) { status(`Brief updated. ${error.message}`); }
}
$('#composer').addEventListener('submit',event => { event.preventDefault(); send(input.value); });
input.addEventListener('keydown',event => {if(event.key === 'Enter' && !event.shiftKey && !event.isComposing){event.preventDefault();$('#composer').requestSubmit();}});
for(const button of document.querySelectorAll('[data-prompt]')) button.addEventListener('click',() => {input.value=button.dataset.prompt;input.focus();});
$('#skip').addEventListener('click',() => send('Skip this field; I will add it later.'));
$('#defer').addEventListener('click',() => send('Leave all remaining optional fields for later.'));
$('#confirm').addEventListener('click',() => send('I confirm the information in the brief is correct.'));
$('#stop-audio').addEventListener('click',stopSpeech);
$('#resume-audio').addEventListener('click',() => audio.play().then(() => {$('#resume-audio').hidden=true;status('');}).catch(() => status('The browser is still blocking audio. Check audio playback permissions.')));
$('#speaker').addEventListener('change',() => {if(!$('#speaker').checked) stopSpeech();});
$('#end-voice').addEventListener('click',() => endVoice());
$('#microphone').addEventListener('click',async () => {
  if(micOn){micOn=false;stream?.getTracks().forEach(t=>t.stop());stream=null;await sender?.replaceTrack(null);controls();return;}
  if(!navigator.mediaDevices?.getUserMedia){status('A microphone-enabled browser on HTTPS or localhost is required.');return;}
  const started = generation; $('#microphone').disabled=true;
  let acquired;
  try {
    acquired = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}});
    if(started !== generation){acquired.getTracks().forEach(t=>t.stop());return;}
    // Mute until the transport is ready; no permission request for text-only chat.
    acquired.getAudioTracks().forEach(t=>{t.enabled=false;});
    await ensureVoice();
    if(!sender) throw new Error('Voice connection stopped.');
    stream=acquired; await sender.replaceTrack(stream.getAudioTracks()[0]);
    micOn=true;$('#speaker').checked=true;status('');
  } catch(error) {
    acquired?.getTracks().forEach(t=>t.stop());
    status(error.name==='NotAllowedError' ? 'Microphone permission is missing. Enable it or continue with text chat.' : error.message);
  } finally {controls();}
});
window.addEventListener('pagehide',() => endVoice(''));
try {render(await (await api('state')).json());}
catch(error){$('#connection').textContent='Server not connected';status(error.message);controls();}
