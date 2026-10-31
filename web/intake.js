import { fields, extract, display, describe, normalize, validate } from './property.js';
const t = (en, vi) => window.estagentI18n.t(en, vi);
const language = () => window.estagentI18n.language;
const form = document.querySelector('#metadata-form');
const summary = document.querySelector('#property-summary');
const log = document.querySelector('#chat-log');
const input = document.querySelector('#chat-input');
const draft = document.querySelector('#description');
const draftMessage = document.querySelector('#draft-message');
const data = {};
let proposal = null;
let messages = [{kind:'intro'}];
function renderSummary() {
  summary.replaceChildren();
  for (const key of Object.keys(fields)) {
    if (!data[key]) continue;
    const dt = document.createElement('dt'); dt.textContent = t(...fields[key]);
    const dd = document.createElement('dd'); dd.textContent = display(key, data[key], language());
    summary.append(dt, dd);
  }
  const count = Object.values(data).filter(Boolean).length;
  document.querySelector('#detail-count').textContent = t(`${count} details`, `${count} thông tin`);
  if (!count) { const empty = document.createElement('p'); empty.className = 'empty-brief'; empty.textContent = t('Your story starts here. Tell us one thing about your apartment.', 'Bắt đầu câu chuyện bằng một thông tin về căn hộ.'); summary.append(empty); }
}
function renderChat() {
  log.replaceChildren();
  for (const message of messages) {
    const bubble = document.createElement('div'); bubble.className = `chat-bubble ${message.kind === 'user' ? 'user' : 'assistant'}`;
    let text = message.text;
    if (message.kind === 'intro') text = t('Tell me about your apartment: its address, size, rooms, facing direction or windows. I can suggest details for your brief, tell you what is missing, and help draft a description.', 'Hãy kể về căn hộ: địa chỉ, diện tích, các phòng, hướng hoặc cửa sổ. Mình có thể gợi ý thông tin để bạn xác nhận, cho biết mục còn thiếu và tạo bản nháp mô tả.');
    if (message.kind === 'reply') text = t(message.en, message.vi);
    if (message.kind === 'facts') text = describe(message.data, language());
    bubble.textContent = text; log.append(bubble);
  }
  if (proposal) {
    const card = document.createElement('div'); card.className = 'proposal';
    const title = document.createElement('strong'); title.textContent = t('Review suggested details', 'Kiểm tra thông tin gợi ý');
    const text = document.createElement('p'); text.textContent = describe(proposal, language());
    const note = document.createElement('small'); note.textContent = t('Applying replaces matching fields. Other details stay unchanged.', 'Xác nhận sẽ thay thế các mục tương ứng. Các thông tin khác được giữ nguyên.');
    const apply = document.createElement('button'); apply.className = 'button light'; apply.type = 'button'; apply.textContent = t('Use these details', 'Dùng thông tin này');
    apply.addEventListener('click', () => {
      const next = {...data, ...proposal};
      if (!validate(next)) { reply('The room counts conflict. Please correct them in the optional form.', 'Số phòng chưa nhất quán. Hãy chỉnh lại trong form tùy chọn.'); proposal = null; renderChat(); return; }
      Object.assign(data, proposal);
      for (const key of Object.keys(proposal)) form.elements[key].value = data[key] || '';
      proposal = null;
      changed(); reply('Details added to your brief. You can add more, ask what is missing, or create a draft.', 'Đã cập nhật thông tin. Bạn có thể bổ sung, hỏi thông tin còn thiếu hoặc tạo bản nháp.');
    });
    const dismiss = document.createElement('button'); dismiss.type='button'; dismiss.className='dismiss-proposal'; dismiss.textContent=t('Dismiss','Bỏ qua'); dismiss.addEventListener('click',()=>{proposal=null;renderChat();input.focus();});
    card.append(title,text,note,apply,dismiss); log.append(card);
  }
  log.scrollTop = log.scrollHeight;
}
function reply(en, vi) { messages.push({kind:'reply',en,vi}); renderChat(); }
function changed() {
  renderSummary();
  if (!draft.hidden) draftMessage.textContent = t('Details changed. Create a new draft to refresh it; your edits have been kept.', 'Thông tin đã thay đổi. Tạo bản nháp mới để cập nhật; nội dung bạn sửa vẫn được giữ lại.');
}
function generate() {
  if (!Object.values(data).some(Boolean)) { draftMessage.textContent = t('Add or confirm at least one detail first.', 'Hãy thêm hoặc xác nhận ít nhất một thông tin trước.'); return; }
  draft.hidden = false; draft.value = describe(data, language());
  draftMessage.textContent = t('Drafted from confirmed details only. Review before sharing.', 'Bản nháp chỉ dùng thông tin đã xác nhận. Kiểm tra trước khi chia sẻ.');
}
function send(text) {
  messages.push({kind:'user',text}); proposal = null;
  const n = normalize(text);
  if (/\b(missing|con thieu|thieu thong tin)\b/.test(n)) {
    const missing = Object.keys(fields).filter(key => !data[key]);
    reply(missing.length ? `Optional details still missing: ${missing.map(k => fields[k][0]).join(', ')}. Share only what you know.` : 'All fields are filled. You can create a draft.', missing.length ? `Thông tin tùy chọn còn thiếu: ${missing.map(k => fields[k][1]).join(', ')}. Chỉ cung cấp điều bạn biết.` : 'Đã có đủ các mục. Bạn có thể tạo bản nháp.'); return;
  }
  if (/\b(draft|description|tao mo ta|viet mo ta|tao ban nhap)\b/.test(n)) { generate(); reply('Check the description draft in your property brief. It uses confirmed details only.', 'Xem bản nháp mô tả ở bảng thông tin căn hộ. Bản nháp chỉ dùng thông tin đã xác nhận.'); return; }
  const found = extract(text);
  if (Object.keys(found).length) { proposal = found; reply('I found these possible details. Please check and confirm them.', 'Mình nhận diện được các thông tin dưới đây. Hãy kiểm tra và xác nhận.'); return; }
  if (/[?？]/.test(text) || /\b(what|how many|does|bao nhieu|huong nao)\b/.test(n)) {
    const topic = /bedroom|phong ngu/.test(n) ? 'bedrooms' : /bathroom|phong tam/.test(n) ? 'bathrooms' : /window|cua so/.test(n) ? 'windows' : /direction|facing|huong/.test(n) ? 'direction' : /address|dia chi/.test(n) ? 'address' : /area|size|dien tich/.test(n) ? 'area' : /room|phong/.test(n) ? 'rooms' : null;
    if (topic && data[topic]) { messages.push({kind:'facts',data:{[topic]:data[topic]}}); renderChat(); return; }
    reply('I do not have confirmed information for that question. Add it in the optional form or describe what you know. This local preview cannot answer general property questions.', 'Mình chưa có thông tin đã xác nhận cho câu hỏi đó. Hãy bổ sung qua form hoặc mô tả điều bạn biết. Bản thử cục bộ chưa trả lời câu hỏi bất động sản tổng quát.'); return;
  }
  reply('I could not confidently identify those details. Try “2 bedrooms, 85 m², southeast-facing, with windows” or use the optional form. For an address, start with “Address:” and end with a semicolon.', 'Mình chưa nhận diện chắc chắn thông tin. Thử “2 phòng ngủ, 85 m², hướng Đông Nam, có cửa sổ” hoặc dùng form tùy chọn. Với địa chỉ, bắt đầu bằng “Địa chỉ:” và kết thúc bằng dấu chấm phẩy.');
}
document.querySelector('#chat-form').addEventListener('submit', event => { event.preventDefault(); const text = input.value.trim(); if (!text) return; input.value=''; send(text); input.focus(); });
document.querySelector('#example-prompt').addEventListener('click',()=>{input.value=t('2 bedrooms, 85 m², southeast-facing, with windows.','2 phòng ngủ, 85 m², hướng Đông Nam, có cửa sổ.');input.focus();});
document.querySelector('#missing-prompt').addEventListener('click',()=>send(t('What details are missing?','Còn thiếu thông tin gì?')));
form.addEventListener('submit', event => {
  event.preventDefault(); const next=Object.fromEntries(new FormData(form));
  if (!validate(next)) { document.querySelector('#form-message').textContent=t('Check room counts: bedrooms and bathrooms cannot exceed total rooms.', 'Kiểm tra số phòng: phòng ngủ và phòng tắm không thể vượt tổng số phòng.');return; }
  Object.assign(data,next); proposal=null; changed();renderChat();document.querySelector('#form-message').textContent=t('Details saved for this session.', 'Đã lưu thông tin trong phiên này.');
});
document.querySelector('#generate-description').addEventListener('click',generate);
document.addEventListener('languagechange',()=>{renderSummary();renderChat();document.querySelector('#form-message').textContent='';draftMessage.textContent=draft.hidden?'':t('Existing draft text is kept. Create a new draft to use this language.', 'Nội dung bản nháp được giữ lại. Tạo bản nháp mới để dùng ngôn ngữ này.');});
renderSummary();renderChat();
