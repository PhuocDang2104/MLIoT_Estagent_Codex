// Product shell around the audited user-provided cached renderer. No model/audio generation.
const observer=new MutationObserver(()=>{
  const header=document.querySelector('#app aside header');
  if(!header||header.dataset.estagent)return;
  header.dataset.estagent='1';
  header.innerHTML='<div><a class="demo-back" href="/viewer.html">← Xem tour · Estagent.</a><strong>NHÀ DEMO</strong><small>Model + ảnh mẫu có sẵn · không dựng mới</small></div>';
  const pano=document.querySelector('#panoMode'),house=document.querySelector('#houseMode');
  if(pano)pano.textContent='Khám phá phòng';if(house)house.textContent='Tổng thể 3D';
  document.querySelector('#app main').insertAdjacentHTML('beforeend','<div id="demo-cache-label">MODEL / ẢNH MẪU CÓ SẴN · Chưa có audio</div>');
  document.documentElement.dataset.demoSource='cached-zind-house-000';
});
observer.observe(document.querySelector('#app'),{childList:true,subtree:true});
window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
