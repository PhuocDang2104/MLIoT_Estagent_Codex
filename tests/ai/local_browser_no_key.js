async page => {
  const base = '__BASE_URL__';
  await page.goto(`${base}/assistant.html`);
  await page.waitForFunction(() => document.querySelector('#connection')?.textContent === 'Chưa kết nối OpenAI');
  const check = (ok, message) => { if (!ok) throw new Error(message); };
  check(await page.locator('#send').isDisabled(), 'Send enabled without a key');
  check(await page.locator('#microphone').isDisabled(), 'Microphone enabled without a key');
  // Keep the existing cookie: absence of a key must not hide a saved profile.
  const result = await page.evaluate(async () => {
    const before = await (await fetch('/api/assistant/state')).json();
    const turn = await fetch('/api/assistant/turn', {method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({text: 'Không có key', request_id: 'missing-key-browser'})});
    const voice = await fetch('/api/assistant/voice', {method: 'POST',
      headers: {'Content-Type': 'application/sdp'}, body: 'v=0\r\nm=audio 9 UDP/TLS/RTP/SAVPF 111\r\n'});
    const after = await (await fetch('/api/assistant/state')).json();
    return {before, after, turnStatus: turn.status, turnError: await turn.json(),
      voiceStatus: voice.status, voiceError: await voice.json()};
  });
  check(!result.before.configured && result.before.profile.area === 90, 'Saved profile unavailable without key');
  check(result.turnStatus === 503 && result.turnError.error.includes('OpenAI'), 'Missing-key text error not explicit');
  check(result.voiceStatus === 503 && result.voiceError.error.includes('OpenAI'), 'Missing-key voice error not explicit');
  check(JSON.stringify(result.before.profile) === JSON.stringify(result.after.profile), '503 changed profile');
  check(JSON.stringify(result.before.history) === JSON.stringify(result.after.history), '503 changed history');
  await page.screenshot({path: 'tests/ai/evidence/local-no-key.png', fullPage: true});
  return {pass: true, missingKey: true, turnStatus: 503, voiceStatus: 503,
    savedProfileReadable: true, sendDisabled: true, microphoneDisabled: true};
}
