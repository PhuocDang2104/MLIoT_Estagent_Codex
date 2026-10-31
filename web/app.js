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

// Public demo descriptor owns the thumbnail; never substitute unrelated property photos.
if(document.querySelector('#demo-hero')){
 fetch('/api/demos').then(async response=>{if(!response.ok)throw new Error('Demo catalog unavailable');return response.json();}).then(catalog=>{
  const demo=catalog.find(item=>item.id==='zind-house-000');if(!demo?.thumbnail_url)return;
  const image=document.querySelector('#demo-hero');const url=new URL(demo.thumbnail_url,location.origin);
  if(url.origin!==location.origin)return;
  image.onload=()=>{image.hidden=false;document.querySelector('#demo-image-state').hidden=true;};image.src=url.href;
 }).catch(()=>{/* Keep the canonical sample link usable when catalog imagery is unavailable. */});
}
