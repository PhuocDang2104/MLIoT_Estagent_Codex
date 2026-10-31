import test from 'node:test';
import assert from 'node:assert/strict';
import {api,apiErrorMessage} from '../../web/tour-common.js';

let locale='en';
globalThis.window={estagentI18n:{get language(){return locale;},t:(en,vi)=>locale==='vi'?vi:en}};

test('legacy config errors are localized without exposing operator details',()=>{
  for(const current of ['en','vi']){
    locale=current;
    const message=apiErrorMessage({detail:'AI is not connected: configure OPENAI_API_KEY on the server / AI chưa kết nối.'},503);
    assert.ok(message.includes(current==='vi'?'Tính năng':'This feature'));
    assert.doesNotMatch(message,/OPENAI|API_KEY|configure| \/ /);
    assert.equal(apiErrorMessage({detail:'Invalid image / Ảnh không hợp lệ'},415),current==='vi'?'Ảnh không hợp lệ':'Invalid image');
  }
});

test('validation keeps the field and actionable limit',()=>{
  locale='en';
  assert.equal(apiErrorMessage({detail:[{loc:['body','title'],msg:'String should have at most 150 characters'}]},422),'title: String should have at most 150 characters');
  assert.equal(apiErrorMessage({detail:'The assistant is busy. Please try again shortly.'},429),'The assistant is busy. Please try again shortly.');
  assert.equal(apiErrorMessage({detail:'Use JPEG / PNG'},415),'Use JPEG / PNG');
});

test('network errors use the selected UI language',async()=>{
  const original=globalThis.fetch;
  globalThis.fetch=async()=>{throw new TypeError('Failed to fetch');};
  try{
    locale='vi';await assert.rejects(api('/session'),/Kiểm tra mạng/);
    locale='en';await assert.rejects(api('/session'),/Check your connection/);
  }finally{globalThis.fetch=original;}
});
