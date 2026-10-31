async (page) => {
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  const check=(value,label)=>{if(!value)throw new Error(label);};
  const root='http://127.0.0.1:4173/web/';
  await page.goto(root);await page.evaluate(()=>localStorage.removeItem('estagent-language'));await page.reload();
  await page.setViewportSize({width:1440,height:1000});
  check(await page.locator('html').getAttribute('lang')==='en','English default');
  for (const img of await page.locator('img').all()) { await img.scrollIntoViewIfNeeded(); await img.evaluate(el => el.decode()); }
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await page.screenshot({path:'web/evidence/bilingual-home-en.png',fullPage:true});
  await page.locator('.nav-cta').click();await page.waitForLoadState('load');
  check(page.url().endsWith('experience.html'),'CTA workspace');
  await page.locator('#chat-input').fill('2 bedrooms, 85 m², southeast-facing, with windows.');
  await page.locator('#chat-form button[type=submit]').click();
  await page.getByRole('button',{name:'Use these details',exact:true}).waitFor();
  check(!(await page.locator('#property-summary').textContent()).includes('85'),'No silent mutation');
  await page.locator('.metadata-details summary').click();
  await page.locator('[name=name]').fill('My apartment draft');
  await page.locator('.metadata-details summary').click();
  await page.getByRole('button',{name:'Use these details',exact:true}).click();
  check(await page.locator('[name=name]').inputValue()==='My apartment draft','Chat preserves unrelated unsaved form input');
  check((await page.locator('#property-summary').textContent()).includes('85'),'Applied details');
  check(await page.locator('[name=direction]').inputValue()==='SE','Direction parsed');
  await page.locator('#chat-input').fill('How many bedrooms?');await page.locator('#chat-form button[type=submit]').click();
  check((await page.locator('#chat-log .chat-bubble').last().textContent()).includes('Bedrooms: 2'),'Grounded answer');
  await page.locator('#chat-input').fill('What is the price?');await page.locator('#chat-form button[type=submit]').click();
  check((await page.locator('#chat-log .chat-bubble').last().textContent()).includes('do not have confirmed'),'Unknown answer');
  await page.locator('[data-lang=vi]').click();
  check(await page.locator('html').getAttribute('lang')==='vi','Vietnamese active');
  check((await page.locator('#property-summary').textContent()).includes('Đông Nam'),'Summary translated');
  await page.locator('.metadata-details summary').click();
  await page.locator('[name=address]').fill('12 Nguyễn Huệ, Quận 1');
  await page.locator('[name=windows]').selectOption('no');
  await page.locator('[name=rooms]').fill('4');
  await page.locator('[name=bathrooms]').fill('1');
  await page.locator('#metadata-form button[type=submit]').click();
  await page.locator('#generate-description').click();
  check((await page.locator('#description').inputValue()).includes('Cửa sổ: Không'),'Draft from form');
  await page.locator('#description').fill('Bản nháp do người dùng chỉnh sửa.');
  await page.locator('[data-lang=en]').click();
  check(await page.locator('#description').inputValue()==='Bản nháp do người dùng chỉnh sửa.','User draft survives locale switch');
  check(await page.locator('[name=address]').inputValue()==='12 Nguyễn Huệ, Quận 1','Address survives locale switch');
  await page.locator('#chat-input').fill('Không có cửa sổ, 3 phòng ngủ.');await page.locator('#chat-form button[type=submit]').click();
  await page.getByRole('button',{name:'Use these details',exact:true}).click();
  check(await page.locator('[name=bedrooms]').inputValue()==='3','Vietnamese parsed while UI English');
  check(await page.locator('[name=windows]').inputValue()==='no','Negative windows preserved');
  await page.locator('#file-input').setInputFiles('web/assets/apartment-living.jpg');await page.getByText('Added 1 photo.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'View apartment-living.jpg',exact:true}).click();check(await page.locator('dialog').evaluate(el=>el.open),'Photo preview');await page.keyboard.press('Escape');
  await page.locator('.metadata-details summary').click();
  await page.screenshot({path:'web/evidence/intake-desktop.png',fullPage:true});
  await page.getByRole('button',{name:'Remove apartment-living.jpg',exact:true}).click();
  await page.locator('#file-input').setInputFiles('web/evidence/invalid.png');await page.getByText('Added 0 photos. Skipped 1 invalid or oversized files.',{exact:true}).waitFor();
  for(const width of [390,320]) {
    await page.setViewportSize({width,height:844});
    check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Workspace overflow '+width);
    await page.screenshot({path:`web/evidence/intake-mobile-${width}.png`,fullPage:true});
  }
  await page.locator('[data-lang=vi]').click();await page.reload();
  check(await page.locator('html').getAttribute('lang')==='vi','Locale persistence');
  check(await page.locator('#file-count').textContent()==='0 ảnh','Initial dynamic locale');
  await page.goto(root);check(await page.locator('html').getAttribute('lang')==='vi','Locale across pages');
  await page.locator('.menu-toggle').click();check(await page.locator('#nav-links').isVisible(),'Mobile menu');await page.locator('#nav-links a[href="#features"]').click();
  for(const locale of ['en','vi']) {
    await page.locator(`[data-lang=${locale}]`).click();
    for(const width of [320,390,768,1440]) {
      await page.setViewportSize({width,height:1000});
      check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Home overflow ${locale} ${width}`);
    }
  }
  for (const img of await page.locator('img').all()) { await img.scrollIntoViewIfNeeded(); await img.evaluate(el => el.decode()); }
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await page.screenshot({path:'web/evidence/bilingual-home-vi.png',fullPage:true});
  check(await page.locator('img').evaluateAll(images=>images.every(i=>i.complete&&i.naturalWidth>0)),'Photos loaded');
  check(errors.length===0,'Browser errors: '+errors.join(';'));
  return 'PASS: EN default, VI persistence; conversation proposals/confirmation; grounded Q&A; EN/VI extraction; optional form; editable draft preserved; upload/preview/remove/invalid; mobile menu; 320–1440px no overflow; all images loaded; no browser errors.';
}
