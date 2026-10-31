const t = (en, vi) => window.estagentI18n.t(en, vi);
const toggle = document.querySelector('.menu-toggle');
const nav = document.querySelector('#nav-links');
toggle?.addEventListener('click', () => {
  const open = toggle.getAttribute('aria-expanded') !== 'true';
  toggle.setAttribute('aria-expanded', String(open));
  toggle.setAttribute('aria-label', open ? t('Close menu', 'Đóng menu') : t('Open menu', 'Mở menu'));
  nav.classList.toggle('open', open);
});
nav?.addEventListener('click', (event) => {
  if (event.target.closest('a')) { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); toggle.setAttribute('aria-label', t('Open menu', 'Mở menu')); }
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && nav?.classList.contains('open')) { nav.classList.remove('open'); toggle.setAttribute('aria-expanded', 'false'); toggle.focus(); }
});

const input = document.querySelector('#file-input');
if (input) {
  const drop = document.querySelector('#drop-zone');
  const grid = document.querySelector('#photo-grid');
  const message = document.querySelector('#upload-message');
  const clear = document.querySelector('#clear-images');
  const dialog = document.querySelector('#image-dialog');
  let photos = [];
  document.addEventListener('languagechange', () => { render(); message.textContent = ''; });
  function render() {
    grid.replaceChildren();
    document.querySelector('#file-count').textContent = `${photos.length} ${t(photos.length === 1 ? 'photo' : 'photos', 'ảnh')}`;
    clear.hidden = !photos.length;
    photos.forEach((photo) => {
      const card = document.createElement('article');
      const view = document.createElement('button');
      view.className = 'photo-preview';
      view.setAttribute('aria-label', `${t('View', 'Xem')} ${photo.file.name}`);
      const img = document.createElement('img');
      img.src = photo.url; img.alt = photo.file.name;
      view.append(img);
      view.addEventListener('click', () => {
        const preview = document.querySelector('#preview-image');
        preview.src = photo.url; preview.alt = photo.file.name;
        document.querySelector('#preview-caption').textContent = photo.file.name;
        dialog.showModal();
      });
      const label = document.createElement('p'); label.textContent = photo.file.name;
      const remove = document.createElement('button'); remove.textContent = '×'; remove.className = 'remove-photo';
      remove.setAttribute('aria-label', `${t('Remove', 'Xóa')} ${photo.file.name}`);
      remove.addEventListener('click', () => { URL.revokeObjectURL(photo.url); photos = photos.filter(p => p !== photo); render(); message.textContent = t('Photo removed.', 'Đã xóa ảnh.'); input.focus(); });
      card.append(view, label, remove); grid.append(card);
    });
  }
  async function addFiles(files) {
    let added = 0; let rejected = 0;
    for (const file of files) {
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 20 * 1024 * 1024 || photos.length >= 20) { rejected++; continue; }
      const url = URL.createObjectURL(file);
      try {
        const image = new Image(); image.src = url; await image.decode();
        if (photos.length >= 20) { URL.revokeObjectURL(url); rejected++; continue; }
        photos.push({ file, url }); added++;
      } catch { URL.revokeObjectURL(url); rejected++; }
    }
    render(); input.value = '';
    message.textContent = t(`Added ${added} ${added === 1 ? 'photo' : 'photos'}.${rejected ? ` Skipped ${rejected} invalid or oversized files.` : ''}`, `Đã thêm ${added} ảnh.${rejected ? ` Bỏ qua ${rejected} tệp không hợp lệ hoặc vượt giới hạn.` : ''}`);
  }
  input.addEventListener('change', () => addFiles([...input.files]));
  for (const event of ['dragenter', 'dragover']) drop.addEventListener(event, e => { e.preventDefault(); drop.classList.add('dragging'); });
  for (const event of ['dragleave', 'drop']) drop.addEventListener(event, e => { e.preventDefault(); drop.classList.remove('dragging'); });
  drop.addEventListener('drop', e => addFiles([...e.dataTransfer.files]));
  clear.addEventListener('click', () => { photos.forEach(p => URL.revokeObjectURL(p.url)); photos = []; render(); message.textContent = t('Photos cleared.', 'Đã xóa bộ ảnh.'); input.focus(); });
  dialog.querySelector('button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
  render();
}

document.addEventListener('languagechange', () => { toggle?.setAttribute('aria-label', toggle.getAttribute('aria-expanded') === 'true' ? t('Close menu', 'Đóng menu') : t('Open menu', 'Mở menu')); });
if (toggle) toggle.setAttribute('aria-label', t('Open menu', 'Mở menu'));

// Catalog zind-house-000 is an equirectangular source (see demos/house.html).
// Projection adapted from the existing studio-panorama.js; no new assets/dependencies.
function startHeroPanorama(image) {
  const canvas=document.querySelector('#hero-panorama'),button=document.querySelector('#hero-rotation');
  const gl=canvas.getContext('webgl',{alpha:false,antialias:false,preserveDrawingBuffer:true});
  if(!gl)return;
  const shader=(type,source)=>{const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw new Error('Panorama shader unavailable');return s;};
  const vertex=shader(gl.VERTEX_SHADER,'attribute vec2 p;varying vec2 uv;void main(){uv=p;gl_Position=vec4(p,0.,1.);}');
  const fragment=shader(gl.FRAGMENT_SHADER,`precision highp float;varying vec2 uv;uniform sampler2D tex;uniform vec3 camera;
  void main(){vec3 d=normalize(vec3(uv.x*camera.y,-uv.y*camera.z,1.));float c=cos(camera.x),s=sin(camera.x);d=vec3(c*d.x+s*d.z,d.y,-s*d.x+c*d.z);vec2 t=vec2(atan(d.x,d.z)/6.2831853+.5,asin(clamp(d.y,-1.,1.))/3.14159265+.5);gl_FragColor=texture2D(tex,t);}`);
  const program=gl.createProgram();gl.attachShader(program,vertex);gl.attachShader(program,fragment);gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('Panorama program unavailable');gl.useProgram(program);
  const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const p=gl.getAttribLocation(program,'p');gl.enableVertexAttribArray(p);gl.vertexAttribPointer(p,2,gl.FLOAT,false,0,0);
  const texture=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,texture);
  for(const key of [gl.TEXTURE_WRAP_S,gl.TEXTURE_WRAP_T])gl.texParameteri(gl.TEXTURE_2D,key,gl.CLAMP_TO_EDGE);
  for(const key of [gl.TEXTURE_MIN_FILTER,gl.TEXTURE_MAG_FILTER])gl.texParameteri(gl.TEXTURE_2D,key,gl.LINEAR);
  let source=image;const limit=Math.min(4096,gl.getParameter(gl.MAX_TEXTURE_SIZE));
  if(image.naturalWidth>limit){source=document.createElement('canvas');source.width=limit;source.height=Math.round(limit*image.naturalHeight/image.naturalWidth);source.getContext('2d').drawImage(image,0,0,source.width,source.height);}
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGB,gl.RGB,gl.UNSIGNED_BYTE,source);if(gl.getError()!==gl.NO_ERROR)throw new Error('Panorama texture unavailable');
  const location=gl.getUniformLocation(program,'camera'),motion=matchMedia('(prefers-reduced-motion: reduce)');
  let yaw=0,paused=false,visible=true,drag=null,frame=0,last=0;
  const draw=()=>{const dpr=Math.min(devicePixelRatio||1,1.5),w=Math.round(canvas.clientWidth*dpr),h=Math.round(canvas.clientHeight*dpr);if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}gl.viewport(0,0,w,h);const aspect=w/h,lens=Math.tan(Math.PI*70/360);gl.uniform3f(location,yaw,lens*Math.min(1,aspect),lens*Math.min(1,1/aspect));gl.drawArrays(gl.TRIANGLES,0,3);};
  const syncLabel=()=>{const stopped=paused||motion.matches;button.textContent=motion.matches?t('Still view','Góc nhìn tĩnh'):stopped?t('Resume rotation','Tiếp tục xoay'):t('Pause rotation','Dừng xoay');button.ariaPressed=String(stopped);button.disabled=motion.matches;};
  const tick=now=>{frame=0;if(paused||motion.matches||document.hidden||!visible){last=0;return;}if(last)yaw+=(Math.min(now-last,60)/1000)*.035;last=now;draw();frame=requestAnimationFrame(tick);};
  const sync=()=>{cancelAnimationFrame(frame);last=0;syncLabel();draw();if(!paused&&!motion.matches&&!document.hidden&&visible)frame=requestAnimationFrame(tick);};
  canvas.hidden=false;image.hidden=true;button.hidden=false;sync();
  button.onclick=()=>{paused=!paused;sync();};
  canvas.onpointerdown=e=>{paused=true;drag=e.clientX;canvas.setPointerCapture(e.pointerId);sync();};
  canvas.onpointermove=e=>{if(drag===null)return;yaw-=(e.clientX-drag)*.004;drag=e.clientX;draw();};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;
  motion.addEventListener('change',sync);window.addEventListener('resize',draw);document.addEventListener('visibilitychange',sync);document.addEventListener('languagechange',syncLabel);
  new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();}).observe(canvas);
  window.addEventListener('pagehide',()=>cancelAnimationFrame(frame));window.addEventListener('pageshow',sync);
}
if(document.querySelector('#demo-hero')){
 const state=document.querySelector('#demo-image-state');
 const unavailable=()=>{state.textContent=t('Open the sample home to explore.','Mở nhà mẫu để khám phá.');};
 fetch('/api/demos').then(async response=>{if(!response.ok)throw new Error('Demo catalog unavailable');return response.json();}).then(catalog=>{
  const demo=catalog.find(item=>item.id==='zind-house-000');if(!demo?.thumbnail_url){unavailable();return;}
  const image=document.querySelector('#demo-hero'),url=new URL(demo.thumbnail_url,location.origin);if(url.origin!==location.origin){unavailable();return;}
  image.onload=()=>{image.hidden=false;state.hidden=true;try{startHeroPanorama(image);}catch{image.hidden=false;document.querySelector('#hero-panorama').hidden=true;document.querySelector('#hero-rotation').hidden=true;}};
  image.onerror=unavailable;image.src=url.href;
 }).catch(unavailable);
}
