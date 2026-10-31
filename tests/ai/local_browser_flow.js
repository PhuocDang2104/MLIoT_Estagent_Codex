async page => {
  // No app API is intercepted: only off-host browser resources are blocked.
  const base = '__BASE_URL__';
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.context().clearCookies();
  await page.context().route('**/*', route => {
    return route.request().url().startsWith(`${base}/`) ? route.continue() : route.abort();
  });
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  const ready = () => page.waitForFunction(() => document.querySelector('#connection')?.textContent === 'Sẵn sàng trò chuyện');
  const read = () => page.evaluate(async () => (await fetch('/api/assistant/state')).json());
  const turn = async (text, button = '#send', expectedStatus = 200) => {
    if (button === '#send') await page.locator('#message').fill(text);
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === `${base}/api/assistant/turn` && r.request().method() === 'POST'),
      page.locator(button).click(),
    ]);
    check(response.status() === expectedStatus, `turn status ${response.status()}`);
    await page.waitForFunction(() => !document.querySelector('#send').disabled);
    return response.json();
  };

  await page.setViewportSize({width: 1440, height: 1000});
  await page.goto(`${base}/assistant.html`);
  await ready();
  check(Object.keys((await read()).profile).length === 0, 'Expected isolated empty database');
  let result = await turn('Căn hộ ở Quận 7, TP.HCM, diện tích 85 m², có 2 phòng ngủ.');
  check(result.profile.address === 'Quận 7, TP.HCM' && result.profile.area === 85 && result.profile.bedrooms === 2, 'Facts not persisted');
  check(result.stage === 'optional', 'Expected optional step for this explicit fixture policy');
  check((await page.locator('#required-fields').innerText()).includes('85 m²'), 'Profile not rendered');
  result = await turn('', '#defer');
  check(result.stage === 'review' && result.deferred.length > 0, 'Optional fields not deferred');
  result = await turn('', '#confirm');
  check(result.confirmed && result.stage === 'complete', 'Confirmation not stored');
  result = await turn('Sửa diện tích thành 90 m².');
  check(result.profile.area === 90 && !result.confirmed && result.stage === 'review', 'Correction did not reset confirmation');
  const snapshot = result;
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear(); });
  await page.reload();
  await ready();
  const restored = await read();
  for (const key of ['profile', 'history', 'deferred', 'confirmed', 'stage']) {
    check(JSON.stringify(restored[key]) === JSON.stringify(snapshot[key]), `Reload lost ${key}`);
  }
  check((await page.locator('#required-fields').innerText()).includes('90 m²'), 'Reload did not render saved area');
  await page.screenshot({path: 'tests/ai/evidence/local-desktop.png', fullPage: true});
  for (const width of [390, 320]) {
    await page.setViewportSize({width, height: 844});
    check(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow at ${width}`);
  }
  await page.screenshot({path: 'tests/ai/evidence/local-mobile-320.png', fullPage: true});
  await page.setViewportSize({width: 1440, height: 1000});

  const rejected = 'Câu ngoài fixture để kiểm đường lỗi.';
  await turn(rejected, '#send', 502);
  check((await page.locator('#status').innerText()).includes('Chưa hiểu chắc chắn'), 'Model failure not shown');
  check(await page.locator('#message').inputValue() === rejected, 'Failed message not available for retry');
  const afterError = await read();
  check(JSON.stringify(afterError.profile) === JSON.stringify(snapshot.profile), 'Failure changed profile');
  check(JSON.stringify(afterError.history) === JSON.stringify(snapshot.history), 'Failure changed accepted history');
  check(errors.length === 0, `Browser JS errors: ${errors.join('; ')}`);
  return {pass: true, realHTTP: true, realLangGraph: true, model: 'finite fixture',
    reloadPreserved: ['profile', 'history', 'deferred', 'confirmed', 'stage'],
    modelFailure: 502, mobileWidths: [390, 320], pageErrors: errors.length};
}
