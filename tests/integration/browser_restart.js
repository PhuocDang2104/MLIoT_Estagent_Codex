async page => {
  const base='__BASE_URL__',check=(ok,message)=>{if(!ok)throw new Error(message);};
  const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('integration-evidence')));
  await page.goto(saved.draftURL);await page.locator('.scene-card').nth(1).waitFor();
  check(await page.locator('#tour-title').inputValue()==='Unpublished change','Restart lost draft');
  await page.locator('#message').fill('Rename the first scene Lobby and reverse the order.');
  const response=page.waitForResponse(r=>r.url().endsWith('/chat'));await page.locator('#send').click();const result=await response;check(result.status()===200,'Injected provider chat failed');
  await page.waitForFunction(()=>!document.querySelector('#send').disabled);
  check(await page.locator('.scene-card').last().locator('input').first().inputValue()==='Lobby','Chat did not rename/reorder via real backend');
  await page.reload();await page.locator('.scene-card').nth(1).waitFor();
  check((await page.locator('#messages').innerText()).includes('Test provider fixture'),'Chat history not persisted');
  await page.goto(base+saved.publishedPath);await page.locator('#scene-title').waitFor();
  check(await page.locator('#tour-heading').innerText()==='Tour synthetic kiểm tích hợp','Restart or chat changed published snapshot');
  await page.locator('#viewer-chat summary').click();await page.locator('#question').fill('Is a sofa guaranteed to fit?');
  const qa=page.waitForResponse(r=>r.url().endsWith('/chat'));await page.locator('#ask').click();check((await qa).status()===200,'Viewer fixture Q&A failed');
  await page.waitForFunction(()=>document.querySelector('#answer').textContent.includes('No verified measurements'));
  const anonymous=await page.context().browser().newContext();const publicPage=await anonymous.newPage();await publicPage.goto(base+saved.publishedPath);await publicPage.locator('#scene-title').waitFor();
  check(await publicPage.locator('#tour-heading').innerText()==='Tour synthetic kiểm tích hợp','Published snapshot cannot be opened in a fresh browser');
  await anonymous.close();
  return {pass:true,restart:'same SQLite + assets; real process restart',creatorChat:'finite provider fixture, real HTTP and persistent edit/reorder',viewer:'immutable snapshot + finite read-only Q&A fixture; fresh browser opens public snapshot',liveOpenAI:false};
}
