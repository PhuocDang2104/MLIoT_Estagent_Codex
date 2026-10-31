// Transport is injected so this component does not invent a second tour API contract.
export function mountDemoChat({loadSession,send,transcribe,speak,getContext,navigate}) {
  const make=(tag,text)=>{const el=document.createElement(tag);if(text)el.textContent=text;return el;};
  const trigger=make('button','Hỏi về căn nhà · Ask AI');trigger.id='chat-toggle';trigger.type='button';trigger.setAttribute('aria-expanded','false');
  const panel=make('section');panel.id='demo-chat';panel.hidden=true;panel.setAttribute('aria-label','Trợ lý xem nhà / Home tour assistant');
  const header=make('header'),title=make('strong','Trợ lý căn nhà · Home assistant'),close=make('button','×');close.type='button';close.setAttribute('aria-label','Đóng chat / Close chat');header.append(title,close);
  const current=make('p'),locale=make('select');locale.setAttribute('aria-label','Ngôn ngữ chat / Chat language');
  for(const [value,label] of [['vi','Tiếng Việt'],['en','English']]){const o=make('option',label);o.value=value;locale.append(o);}
  const messages=make('div');messages.className='demo-chat-messages';messages.setAttribute('role','log');messages.setAttribute('aria-live','polite');
  const form=make('form'),input=make('textarea');input.rows=2;input.maxLength=2000;input.placeholder='Hỏi về phòng đang xem… / Ask about this room…';input.setAttribute('aria-label','Câu hỏi / Question');
  const submit=make('button','Gửi / Send'),mic=make('button','Nói / Speak');submit.type='submit';mic.type='button';
  const status=make('p');status.setAttribute('role','status');const audio=make('audio');audio.controls=true;audio.hidden=true;
  const note=make('small','AI trả lời từ nội dung tour. Giọng phản hồi là giọng AI. / Answers use tour descriptions. Voice responses are AI-generated.');
  form.append(input,submit,mic);panel.append(header,current,locale,messages,form,status,audio,note);document.body.append(trigger,panel);
  let session=null,busy=false,disposed=false,opened=false,version=0,request=null,recording=null,audioURL=null,voiceVersion=0;
  const alert=()=>document.dispatchEvent(new Event('chat-start'));
  function pause(){voiceVersion++;audio.pause();}
  function controls(){submit.disabled=busy||!!recording||!session?.configured;mic.disabled=busy||!session?.voice_configured;}
  function contextLabel(){const c=getContext();current.textContent=c?.label?`Đang xem / Viewing: ${c.label}`:'Toàn bộ căn nhà / Whole home';}
  function append(role,text,answer=null){
    const bubble=make('div');bubble.className='demo-chat-message '+role;bubble.append(make('strong',role==='user'?'Bạn / You':'Trợ lý / Assistant'),make('p',text));
    if(answer){
      const listen=make('button','Nghe / Listen');listen.type='button';listen.disabled=!session?.voice_configured;
      listen.onclick=async()=>{if(busy)return;alert();pause();const currentVoice=voiceVersion;listen.disabled=true;status.textContent='Đang tạo giọng / Preparing audio…';try{const blob=await speak(answer.request_id);if(disposed||!opened||currentVoice!==voiceVersion)return;if(audioURL)URL.revokeObjectURL(audioURL);audioURL=URL.createObjectURL(blob);audio.src=audioURL;audio.hidden=false;await audio.play();status.textContent='';}catch(e){status.textContent=e.message;}finally{listen.disabled=!session?.voice_configured;}};bubble.append(listen);
    }
    messages.append(bubble);messages.scrollTop=messages.scrollHeight;
  }
  async function open(){opened=true;panel.hidden=false;trigger.setAttribute('aria-expanded','true');alert();contextLabel();input.focus();try{if(!session){session=await loadSession();messages.replaceChildren();for(const turn of session.history||[]){append('user',turn.text);append('assistant',turn.reply,turn);}}status.textContent=session.configured?'':'Chat chưa được kết nối / Chat is not configured.';}catch(e){status.textContent=e.message;}controls();}
  function stopRecording(submitAudio=false){
    const r=recording;if(!r)return;recording=null;clearTimeout(r.timer);r.stream.getTracks().forEach(t=>t.stop());r.node.disconnect();r.source.disconnect();r.context.close();mic.textContent='Nói / Speak';
    if(!submitAudio||!r.parts.length){busy=false;controls();return;}
    const samples=new Float32Array(r.frames);let pos=0;for(const part of r.parts){samples.set(part,pos);pos+=part.length;}
    const wav=encodeWav(samples,r.rate);busy=true;controls();status.textContent='Đang nhận lời nói / Transcribing…';
    transcribe(wav,locale.value,crypto.randomUUID()).then(result=>{if(!disposed&&opened){input.value=result.text;status.textContent='Kiểm tra lời nhận được rồi bấm Gửi / Review the transcript, then Send.';input.focus();}}).catch(e=>{status.textContent=e.message;}).finally(()=>{busy=false;controls();});
  }
  function hide(){opened=false;version++;panel.hidden=true;trigger.setAttribute('aria-expanded','false');pause();stopRecording(false);trigger.focus();}
  trigger.onclick=()=>opened?hide():open();close.onclick=hide;
  locale.onchange=()=>{version++;request=null;pause();stopRecording(false);};input.onfocus=()=>{alert();pause();contextLabel();};
  form.onsubmit=async event=>{
    event.preventDefault();const text=input.value.trim();if(!text||busy||recording||!session?.configured)return;
    alert();pause();busy=true;controls();const context=getContext()||{};const body={text,locale:locale.value,capture_id:context.capture_id||null};const fingerprint=JSON.stringify(body);
    if(request?.fingerprint!==fingerprint)request={fingerprint,id:crypto.randomUUID(),shown:false};const pending=request;const active=++version;
    if(!pending.shown){append('user',text);pending.shown=true;}status.textContent='Đang trả lời / Thinking…';
    try{const answer=await send({...body,request_id:pending.id});if(disposed)return;append('assistant',answer.reply,{...answer,request_id:pending.id});session.history??=[];session.history.push({text,...answer,request_id:pending.id});input.value='';request=null;status.textContent='';
      if(active===version&&opened&&(getContext()?.capture_id||null)===body.capture_id&&answer.target_capture_id){navigate(answer.target_capture_id);contextLabel();}
    }catch(e){status.textContent=e.message;}finally{busy=false;controls();}
  };
  mic.onclick=async()=>{
    if(recording){stopRecording(true);return;}if(busy||!session?.voice_configured)return;
    if(!navigator.mediaDevices?.getUserMedia){status.textContent='Trình duyệt chưa hỗ trợ micro / Microphone unavailable.';return;}
    alert();pause();busy=true;controls();const recordVersion=version;try{const stream=await navigator.mediaDevices.getUserMedia({audio:true});if(!opened||recordVersion!==version){stream.getTracks().forEach(t=>t.stop());return;}
      const context=new AudioContext(),source=context.createMediaStreamSource(stream),node=context.createScriptProcessor(4096,1,1),r={stream,context,source,node,parts:[],frames:0,rate:context.sampleRate,timer:null};recording=r;
      node.onaudioprocess=event=>{if(recording!==r)return;const part=event.inputBuffer.getChannelData(0);const remain=Math.floor(r.rate*20)-r.frames;const take=part.slice(0,Math.max(0,remain));r.parts.push(take);r.frames+=take.length;if(r.frames>=r.rate*20)stopRecording(true);};
      source.connect(node);node.connect(context.destination);r.timer=setTimeout(()=>stopRecording(true),20000);mic.textContent='Dừng ghi / Stop recording';status.textContent='Đang ghi, tối đa 20 giây / Recording, up to 20 seconds.';
    }catch(e){status.textContent='Không mở được micro. Bạn có thể nhập chữ. / Microphone unavailable; type instead.';}finally{busy=false;controls();}
  };
  const otherPlayback=event=>{if(event.target instanceof HTMLMediaElement&&event.target!==audio)pause();};document.addEventListener('play',otherPlayback,true);
  const hidePage=()=>{pause();stopRecording(false);};const hidden=()=>{if(document.hidden)hidePage();};document.addEventListener('visibilitychange',hidden);window.addEventListener('pagehide',hidePage);const escape=e=>{if(e.key==='Escape'&&opened){e.stopPropagation();hide();}};document.addEventListener('keydown',escape,true);
  const observer=new MutationObserver(contextLabel);const app=document.querySelector('#app');if(app)observer.observe(app,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});controls();
  return {pause,destroy(){disposed=true;hidePage();observer.disconnect();document.removeEventListener('play',otherPlayback,true);document.removeEventListener('visibilitychange',hidden);window.removeEventListener('pagehide',hidePage);document.removeEventListener('keydown',escape,true);if(audioURL)URL.revokeObjectURL(audioURL);trigger.remove();panel.remove();}};
}

export function encodeWav(input,sourceRate){
  const rate=16000,count=Math.min(20*rate,Math.floor(input.length*rate/sourceRate)),buffer=new ArrayBuffer(44+count*2),view=new DataView(buffer);
  const text=(offset,value)=>{for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));};text(0,'RIFF');view.setUint32(4,36+count*2,true);text(8,'WAVE');text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,rate,true);view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);text(36,'data');view.setUint32(40,count*2,true);
  for(let i=0;i<count;i++){const position=i*sourceRate/rate,left=Math.floor(position),mix=position-left,sample=Math.max(-1,Math.min(1,(input[left]||0)*(1-mix)+(input[left+1]||0)*mix));view.setInt16(44+i*2,sample<0?sample*32768:sample*32767,true);}
  return new Blob([buffer],{type:'audio/wav'});
}
