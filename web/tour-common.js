export const $ = selector => document.querySelector(selector);
export const t = (en, vi) => window.estagentI18n?.t(en, vi) ?? en;
export const language = () => window.estagentI18n?.language ?? 'en';
export function apiErrorMessage(data, status) {
  const detail=Array.isArray(data?.detail)?data.detail.map(issue=>`${(issue.loc||[]).slice(1).join('.')}: ${issue.msg}`).join('; '):data?.detail;
  let message=typeof detail==='string'?detail:typeof data?.error==='string'?data.error:'';
  // Older releases and optional provider modules may still return operator-only
  // config messages. Keep those out of both Creator and Viewer surfaces.
  if(/OPENAI_[A-Z_]+|API[_ -]?KEY|model access|quota|configuration|configure/i.test(message)) {
    return t('This feature is currently unavailable. Please try again later.','Tính năng này hiện chưa sẵn sàng. Vui lòng thử lại sau.');
  }
  // Compatibility with the existing bilingual error envelope; new handlers
  // already return one locale. Keep field-level validation detail intact.
  const translations=message.split(' / ');
  const vietnamese=/[ăâđêôơưĂÂĐÊÔƠƯ\u1ea0-\u1ef9]/;
  if(translations.length===2&&!vietnamese.test(translations[0])&&vietnamese.test(translations[1]))message=translations[language()==='vi'?1:0];
  return message||t(`Request failed (${status}). Please try again.`,`Yêu cầu thất bại (${status}). Vui lòng thử lại.`);
}
export async function api(path, {method='GET', body, binary=false}={}) {
  let response;
  try {
    response = await fetch(`/api/tours${path}`, {method, headers: body ? {'Content-Type':binary?'application/octet-stream':'application/json'} : {}, body:body ? (binary?body:JSON.stringify(body)) : undefined});
  } catch {
    throw new Error(t('Could not connect. Check your connection and try again.','Chưa kết nối được. Kiểm tra mạng rồi thử lại.'));
  }
  const data = await response.json().catch(() => ({detail:t('Server returned an unreadable response.','Máy chủ trả phản hồi không đọc được.')}));
  if (!response.ok) {
    throw new Error(apiErrorMessage(data,response.status));
  }
  return data;
}
export function node(tag, text, className) {
  const el=document.createElement(tag); if(text!==undefined)el.textContent=text; if(className)el.className=className; return el;
}
export function notice(message, error=false) {
  const target=$('#status'); target.textContent=message; target.classList.toggle('error',error);
}
export function link(text,href,className='button light') {const el=node('a',text,className);el.href=href;return el;}
export function requestID(){return crypto.randomUUID();}
