async page => {
  const base='__BASE_URL__';
  await page.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
  await page.goto(base+'/qa/narration');
  await page.getByText('Narration unavailable / Chưa bật TTS:',{exact:false}).waitFor();
  await page.getByLabel('Approved script / Lời giới thiệu').fill('Welcome to the tour.');
  await page.getByRole('checkbox').check();
  if(!await page.getByRole('button',{name:'Generate voice / Sinh giọng',exact:true}).isDisabled())throw Error('Missing key generation not disabled');
  return {pass:true,missing_key:'visible reason and disabled generation'};
}
