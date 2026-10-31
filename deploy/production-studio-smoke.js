async page => {
  const base = 'https://estagent.duckdns.org';
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(base + '/business/create');
  const session = await page.evaluate(async () => (await fetch('/api/studio/session')).json());
  if (session.configured) throw Error('Expected keyless preview; no generation request is authorized by this smoke');
  await page.getByText('Chưa kết nối OpenAI.', {exact: false}).waitFor();
  await page.evaluate(async () => {
    const canvas = document.createElement('canvas'); canvas.width = 128; canvas.height = 64;
    const context = canvas.getContext('2d'); context.fillStyle = '#49716b'; context.fillRect(0, 0, 128, 64);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    const transfer = new DataTransfer();
    transfer.items.add(new File([blob], 'deployment-synthetic-studio.png', {type: 'image/png'}));
    const input = document.querySelector('#panoramas'); input.files = transfer.files;
    input.dispatchEvent(new Event('change', {bubbles: true}));
  });
  await page.locator('#selected-images .image-tile').waitFor();
  await page.locator('[name=name]').fill('Unpublished deployment Studio QA — synthetic');
  await page.locator('[name=description]').fill('Synthetic deployment test only, not a property listing.');
  await page.locator('#save-project').click();
  await page.locator('#generate').waitFor({state: 'visible'});
  if (!await page.locator('#generate').isDisabled()) throw Error('Keyless generation should be disabled');
  await page.reload();
  await page.locator('#assets .image-tile').waitFor();
  if (!await page.locator('#generate').isDisabled()) throw Error('Keyless state lost on reload');
  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({width, height: 900});
    if (!await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)) throw Error('Studio overflow at ' + width);
  }
  if (errors.length) throw Error(errors.join(';'));
  return {pass: true, keyless: true, savedAndReloaded: true, mobile: [390, 320],
    published: false, generationCalls: 0, pageErrors: errors};
}
