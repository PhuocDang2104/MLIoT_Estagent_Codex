import {test} from 'node:test';
import assert from 'node:assert/strict';
import {extract, describe, validate} from '../property.js';
test('extract English details without inventing missing fields',()=>assert.deepEqual(extract('2 bedrooms, 85 m², southeast-facing, with windows.'),{bedrooms:'2',area:'85',direction:'SE',windows:'yes'}));
test('Vietnamese, explicit address, and no windows',()=>assert.deepEqual(extract('Địa chỉ: 12 Nguyễn Huệ, Quận 1; 4 phòng, 2 phòng ngủ, 1 phòng tắm, 85,5 m², hướng Đông Bắc, không có cửa sổ.'),{bedrooms:'2',bathrooms:'1',rooms:'4',area:'85.5',direction:'NE',windows:'no',address:'12 Nguyễn Huệ, Quận 1'}));
test('questions and uncertainty do not become facts',()=>{assert.deepEqual(extract('Does it have 2 bedrooms?'),{});assert.deepEqual(extract('Có thể có 3 phòng ngủ'),{});assert.deepEqual(extract('Maybe 85 m²'),{});});
test('conflicting repeated fields require manual review',()=>assert.deepEqual(extract('2 bedrooms or 3 bedrooms'),{}));
test('studio can have zero bedrooms and unknown is omitted',()=>{assert.equal(extract('0 bedrooms').bedrooms,'0');assert.equal(describe({bedrooms:'0',windows:'no'},'en'),'Windows: No. Bedrooms: 0.');assert.equal(describe({},'vi'),'');});
test('invalid counts and conflicting totals rejected',()=>{assert.equal(validate({rooms:'2',bedrooms:'3'}),false);assert.equal(validate({bedrooms:'-1'}),false);assert.equal(validate({bedrooms:'2.5'}),false);assert.equal(validate({area:'NaN'}),false);assert.equal(validate({bedrooms:'0',windows:''}),true);});
