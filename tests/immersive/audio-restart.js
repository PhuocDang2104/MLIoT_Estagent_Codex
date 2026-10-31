async page=>{
  const base='__BASE_URL__',check=(ok,message)=>{if(!ok)throw new Error(message);};
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('audio-evidence')));
  await page.goto(`${base}/viewer.html?tour=${saved.publishedID}`);await page.locator('#scene-title').waitFor();
  await page.locator('#viewer-audio summary').click();await page.locator('#play').click();await page.waitForFunction(()=>document.querySelector('#narration-track').currentTime>.2);
  check(await page.locator('#narration-track').getAttribute('src')===saved.audioURL,'Restart changed immutable audio ref');
  const anon=await page.context().browser().newContext();const response=await anon.request.get(base+saved.audioURL);check(response.status()===200&&response.headers()['content-type']==='audio/wav','Published audio inaccessible without owner cookie');await anon.close();
  await page.locator('#pause').click();
  return {pass:true,serverRestart:true,publishedAudioImmutable:true,anonymousPublishedWav:true,actualPlaybackAfterRestart:true};
}
