export const $ = selector => document.querySelector(selector);
export const t = (en, vi) => window.estagentI18n?.t(en, vi) ?? en;
export const language = () => window.estagentI18n?.language ?? 'en';
export async function api(path, {method='GET', body, binary=false}={}) {
  const response = await fetch(`/api/tours${path}`, {method, headers: body ? {'Content-Type':binary?'application/octet-stream':'application/json'} : {}, body:body ? (binary?body:JSON.stringify(body)) : undefined});
  const data = await response.json().catch(() => ({detail:t('Server returned an unreadable response.','Máy chủ trả phản hồi không đọc được.')}));
  if (!response.ok) {
    const detail=Array.isArray(data.detail)?data.detail.map(issue=>`${(issue.loc||[]).slice(1).join('.')}: ${issue.msg}`).join('; '):data.detail;
    throw new Error(typeof detail==='string'?detail:data.error||t(`Request failed (${response.status}).`,`Yêu cầu thất bại (${response.status}).`));
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
