// Product shell around the audited user-provided cached renderer. No model/audio generation.
const observer=new MutationObserver(()=>{
  const header=document.querySelector('#app aside header');
  if(!header||header.dataset.estagent)return;
  header.dataset.estagent='1';
  header.innerHTML='<div><a class="demo-back" href="/viewer.html">← Xem tour · Estagent.</a><strong>NHÀ DEMO</strong><small>Model + ảnh mẫu có sẵn · không dựng mới</small></div>';
  const pano=document.querySelector('#panoMode'),house=document.querySelector('#houseMode');
  if(pano)pano.textContent='Khám phá phòng';if(house)house.textContent='Tổng thể 3D';
  document.querySelector('#app main').insertAdjacentHTML('beforeend','<div id="demo-cache-label">MODEL / ẢNH MẪU CÓ SẴN</div>');
  document.documentElement.dataset.demoSource='cached-zind-house-000';
});
observer.observe(document.querySelector('#app'),{childList:true,subtree:true});
window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});

// Playback of two pre-generated neutral intros. No Speech API request or autoplay.
async function mountIntro(){
  const response=await fetch('/api/demos/zind-house-000/intro');
  if(!response.ok)throw new Error('Không tải được lời chào mẫu.');
  const tracks=await response.json();if(!tracks.length)return;
  const panel=document.createElement('details');panel.id='demo-intro';
  panel.innerHTML='<summary>Nghe lời chào · AI</summary><div><label>Ngôn ngữ <select aria-label="Ngôn ngữ lời chào"><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label><audio controls preload="metadata"></audio><p class="intro-script"></p><small>AI-generated · OpenAI. Chỉ lời chào chung, không mô tả từng phòng.</small><p role="status"></p></div>';
  document.body.append(panel);
  const select=panel.querySelector('select'),audio=panel.querySelector('audio');
  function choose(){audio.pause();const track=tracks.find(t=>t.locale===select.value);audio.removeAttribute('src');panel.querySelector('.intro-script').textContent=track?.script||'Chưa có lời chào ngôn ngữ này.';if(track)audio.src=track.url;audio.load();}
  select.addEventListener('change',choose);audio.addEventListener('error',()=>{panel.querySelector('[role=status]').textContent='Không phát được lời chào. Hãy thử lại.';});
  window.addEventListener('pagehide',()=>audio.pause(),{once:true});choose();
}
mountIntro().catch(error=>{const note=document.createElement('p');note.textContent=error.message;document.querySelector('#demo-source>div').append(note);});
