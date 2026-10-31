async page=>{
 const base='__BASE__',errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/demos/zind-house-000');await page.locator('#demo-intro summary').click();
 const audio=page.locator('#demo-intro audio');const results=[];
 for(const [locale,duration] of [['vi',6.15],['en',4.95]]){
  await page.locator('#demo-intro select').selectOption(locale);
  await page.waitForFunction(()=>document.querySelector('#demo-intro audio').readyState>=1,null,{timeout:10000});
  if(!await audio.evaluate(a=>a.paused))throw Error('Audio autostarted');
  const measured=await audio.evaluate(a=>a.duration);if(Math.abs(measured-duration)>.01)throw Error('Wrong live WAV duration');
  await audio.evaluate(a=>a.play());await page.waitForFunction(()=>document.querySelector('#demo-intro audio').currentTime>.15,null,{timeout:5000});
  await audio.evaluate(a=>a.pause());results.push({locale,duration:measured,played:true});
 }
 if(!await page.locator('#demo-intro').getByText('AI-generated',{exact:false}).isVisible())throw Error('Missing AI disclosure');
 if(errors.length)throw Error(errors.join(';'));
 return {pass:true,base,actual_pre_generated_wavs:results,new_paid_calls:0,errors};
}
