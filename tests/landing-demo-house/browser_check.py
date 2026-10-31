"""Real Chrome checks using installed Python Playwright, no CLI daemon."""
import hashlib,json
from urllib.parse import urlparse
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
ORIGIN='https://estagent.duckdns.org'
SIGNATURE='''c=>{const g=c.getContext('webgl'),p=new Uint8Array(c.width*c.height*4);g.readPixels(0,0,c.width,c.height,g.RGBA,g.UNSIGNED_BYTE,p);let h=2166136261;for(let i=0;i<p.length;i+=37)h=Math.imul(h^p[i],16777619);return h>>>0;}'''
def routes(page):
 def serve(route):
  path=urlparse(route.request.url).path
  if path=='/api/demos/zind-house-000/assets/house/manifest.json':return route.fulfill(path='/private/tmp/landing-manifest.json',content_type='application/json')
  if path=='/api/demos/zind-house-000/assets/house/dollhouse-studio.glb':return route.fulfill(path='/private/tmp/landing-demo-house.glb',content_type='model/gltf-binary')
  file=ROOT/'web'/('index.html' if path=='/' else path.lstrip('/'))
  if file.is_file():return route.fulfill(path=str(file))
  return route.fulfill(status=404,body='QA asset unavailable')
 page.route('**/*',serve)
def signature(page,selector): return page.locator(selector).evaluate(SIGNATURE)
def frames(page,n=8):page.evaluate('n=>new Promise(resolve=>{let i=0;function f(){if(++i>=n)resolve();else requestAnimationFrame(f);}requestAnimationFrame(f);})',n)
def changed(page,selector):
 before=signature(page,selector)
 for _ in range(30):
  frames(page)
  if signature(page,selector)!=before:return
 raise AssertionError('No rendered motion '+selector)
def still(page):
 a=signature(page,'#hero-building');b=signature(page,'#hero-panorama');frames(page)
 assert a==signature(page,'#hero-building') and b==signature(page,'#hero-panorama')
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless=False)
 try:
  context=browser.new_context(viewport={'width':1440,'height':1000});page=context.new_page();routes(page);errors=[];requests=[]
  page.on('console',lambda m:print('BROWSER',m.text,flush=True) if m.type=='error' else None);page.on('requestfailed',lambda r:print('REQUEST_FAILED',r.url,r.failure,flush=True));page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
  print('Opening page',flush=True);page.goto(ORIGIN+'/',wait_until='domcontentloaded');print('Page loaded',flush=True);page.wait_for_function("document.querySelector('#hero-building')?.dataset.ready==='true'||document.querySelector('#building-state')?.textContent.includes('unavailable')",timeout=120000);assert page.locator('#hero-building').get_attribute('data-ready')=='true', {'state':page.locator('#building-state').inner_text(),'errors':errors};page.wait_for_function("!document.querySelector('#hero-panorama').hidden")
  print('Actual model ready',flush=True)
  changed(page,'#hero-building');changed(page,'#hero-panorama');page.locator('#hero-rotation').click();still(page)
  before=signature(page,'#hero-building');page.locator('#hero-building').focus();page.keyboard.press('ArrowRight');assert before!=signature(page,'#hero-building')
  before=signature(page,'#hero-building');box=page.locator('#hero-building').bounding_box();x=box['x']+box['width']/2;y=box['y']+box['height']/2
  page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+75,y,steps=8);page.mouse.up();assert before!=signature(page,'#hero-building')
  print('Rotation, common pause, keyboard, drag PASS',flush=True)
  page.locator('[data-lang=vi]').click();assert 'Khung nhà mẫu' in page.locator('.hero-building figcaption').inner_text();page.locator('[data-lang=en]').click()
  layouts=[]
  for width in [1440,390,320]:
   page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844});frames(page)
   copy=page.locator('.pitch-copy').bounding_box();model=page.locator('.hero-building').bounding_box()
   assert model['x']>=copy['x']+copy['width'] if width==1440 else model['y']>=copy['y']+copy['height']
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.screenshot(path=f'/private/tmp/landing-demo-house-{width}.png');layouts.append({'width':width,'model':model})
  page.locator('#hero-rotation').click();changed(page,'#hero-building');page.emulate_media(reduced_motion='reduce');page.wait_for_function("document.querySelector('#hero-rotation').disabled");still(page)
  assert ORIGIN+'/api/demos/zind-house-000/assets/house/manifest.json' in requests
  assert ORIGIN+'/api/demos/zind-house-000/assets/house/dollhouse-studio.glb' in requests
  assert not any('sunrise-office' in url for url in requests)
  print('Responsive1440/390/320, EN/VI, reduced motion, source URLs PASS',flush=True)
  page.close()
  failure=context.new_page();routes(failure)
  failure.route('**/assets/panoramas/lythwood-lounge-8k.jpg',lambda r:r.fulfill(status=404,body='test image unavailable'))
  failure.goto(ORIGIN+'/',wait_until='domcontentloaded');failure.wait_for_selector('#hero-building[data-ready=true]',timeout=60000);failure.locator('#hero-rotation').click();assert failure.locator('#hero-rotation').get_attribute('aria-pressed')=='true'
  failure.close();failure=context.new_page();routes(failure)
  failure.route('**/api/demos/zind-house-000/assets/house/dollhouse-studio.glb',lambda r:r.fulfill(status=404,body='test model unavailable'))
  failure.goto(ORIGIN+'/',wait_until='domcontentloaded');failure.wait_for_function("document.querySelector('#building-state').textContent.includes('unavailable')");failure.wait_for_function("!document.querySelector('#hero-panorama').hidden");failure.close()
  assert not errors,errors
  print(json.dumps({'pass':True,'actualDemoDollhouse':True,'sourceMode':'Unmodified public GET cache, headed Chrome native WebGL','modelSha256':hashlib.sha256(Path('/private/tmp/landing-demo-house.glb').read_bytes()).hexdigest(),'rotationBoth':True,'pauseBoth':True,'keyboard':True,'drag':True,'ENVI':True,'reducedMotion':True,'independentAssetFailure':True,'layouts':layouts,'errors':errors}),flush=True)
 finally:browser.close()
