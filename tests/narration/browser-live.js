async page => {
  const base='__BASE_URL__';
  await page.route('**/*',route=>route.request().url().startsWith(base+'/')?route.continue():route.abort());
  await page.goto(base+'/qa/narration');
  const samples=[];
  for(const locale of ['en','vi']){
    const sample=await page.evaluate(async locale=>{
      const audio=document.createElement('audio');audio.controls=true;document.body.append(audio);audio.src='/qa/live/'+locale;
      await new Promise((resolve,reject)=>{audio.onloadedmetadata=resolve;audio.onerror=reject;});
      await audio.play();await new Promise(resolve=>audio.ontimeupdate=()=>{if(audio.currentTime>0.1)resolve();});
      const result={locale,duration:audio.duration,played:audio.currentTime};audio.pause();audio.remove();return result;
    },locale);samples.push(sample);
  }
  return {pass:true,actual_openai_audio_playback:samples,note:'Existing authorized outputs only; zero new API calls; no human quality assessment'};
}
