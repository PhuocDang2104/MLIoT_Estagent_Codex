async page=>{
  const base='__BASE__',url=base+'/api/tours/exports/__JOB__/download';
  const check=(ok,message)=>{if(!ok)throw new Error(message);};
  await page.context().addCookies([{name:'estagent_tours',value:'__COOKIE__',url:base+'/api/tours/',httpOnly:true,sameSite:'Strict'}]);
  await page.goto(base+'/export.html?tour=__TOUR__');await page.locator('#preview').waitFor();
  const proof=await page.evaluate(async url=>{
    const response=await fetch(url);if(!response.ok)throw new Error('Private export missing');
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await response.arrayBuffer()))).map(v=>v.toString(16).padStart(2,'0')).join('');
    const before=localStorage.getItem('restart-export-hash');localStorage.setItem('restart-export-hash',digest);
    const video=document.querySelector('#video');document.querySelector('#job').hidden=false;video.hidden=false;video.src=url;await video.play();
    return {hash:digest,previousHash:before};
  },url);
  await page.waitForFunction(()=>document.querySelector('#video').currentTime>.3);
  await page.locator('#video').evaluate(video=>video.pause());
  check(!proof.previousHash||proof.previousHash===proof.hash,'Restart changed MP4 bytes');
  const status=await page.request.get(base+'/api/tours/exports/__JOB__');check((await status.json()).state==='ready','Restart lost ready metadata');
  return {pass:true,actualServerProcess:true,actualPlayback:true,privateBytesStable:proof.previousHash===proof.hash,phase:proof.previousHash?'after-restart':'before-restart'};
}
