async page => {
  const base = '__BASE_URL__';
  await page.goto(`${base}/assistant.html`);
  await page.waitForFunction(() => document.querySelector('#connection')?.textContent === 'Sẵn sàng trò chuyện');
  const state = await page.evaluate(async () => (await fetch('/api/assistant/state')).json());
  if (state.profile.address !== 'Quận 7, TP.HCM' || state.profile.area !== 90 ||
      state.profile.bedrooms !== 2 || state.history.length !== 8 ||
      state.stage !== 'review' || state.confirmed || !state.deferred.length) {
    throw new Error('SQLite state was not restored after backend process restart');
  }
  if (!(await page.locator('#required-fields').innerText()).includes('90 m²')) {
    throw new Error('Restored profile not visible');
  }
  await page.screenshot({path: 'tests/ai/evidence/local-after-restart.png', fullPage: true});
  return {pass: true, backendProcessRestart: true, sqliteRestored: true, acceptedMessages: state.history.length};
}
