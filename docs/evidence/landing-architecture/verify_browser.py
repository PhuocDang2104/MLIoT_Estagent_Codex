import hashlib,json,subprocess,mimetypes,os
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'docs/evidence/landing-architecture';OUT.mkdir(parents=True,exist_ok=True)
BASE='4cec440'
HOST='http://127.0.0.1:4177'
def original(name):
    return subprocess.check_output(['git','show',BASE+':'+name],cwd=ROOT).decode('utf8').replace('\r\n','\n')
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
baseline={name:original('web/'+name) for name in ('index.html','app.js','styles.css')}
current={name:(ROOT/'web'/name).read_text(encoding='utf8') for name in baseline}
preserved={}
for name,selector in [('hero','<section class="pitch-hero">'),('how','<section class="section pitch-how"'),('footer','<footer>')]:
    end='</footer>' if name=='footer' else '</section>'
    a=baseline['index.html'].split(selector,1)[1].split(end,1)[0]
    b=current['index.html'].split(selector,1)[1].split(end,1)[0]
    assert a==b,name
    preserved[name]=digest(a)
assert current['app.js'].startswith(baseline['app.js'])
assert current['styles.css'].startswith(baseline['styles.css'])
images={}
for dest,source in [('tour-generation','Langgraph Tour Generation OpenAI Architecture'),('spatial-assistant','Langgraph Rag Spatial Context Assistant')]:
    payload=(ROOT/f'web/assets/architecture/{dest}.png').read_bytes()
    assert payload==(ROOT/f'docs/{source}.png').read_bytes()
    images[dest]=hashlib.sha256(payload).hexdigest()

errors=[];writes=[];layouts=[]
def routes(page,mode='current'):
    page.set_default_timeout(20000)
    page.add_init_script("document.addEventListener('DOMContentLoaded',()=>{const b=document.querySelector('#hero-rotation');if(b&&!b.disabled&&b.ariaPressed!=='true')b.click();},{once:true})")
    def route(request):
        req=request.request
        if req.method not in ('GET','HEAD'):
            writes.append(req.method+' '+urlsplit(req.url).path);request.abort();return
        path=urlsplit(req.url).path
        if urlsplit(req.url).netloc=='127.0.0.1:4177':
            if path in ('/','/index.html','/app.js','/styles.css'):
                name='index.html' if path in ('/','/index.html') else path[1:]
                value=(baseline if mode=='baseline' else current)[name]
                mime='text/html' if name.endswith('.html') else 'text/css' if name.endswith('.css') else 'text/javascript'
                request.fulfill(status=200,content_type=mime,body=value);return
            if path.startswith('/assets/architecture/'):
                target=ROOT/'web'/path.lstrip('/')
                if target.is_file():request.fulfill(status=200,content_type='image/png',body=target.read_bytes());return
        target=ROOT/'web'/path.lstrip('/')
        if target.is_file():
            request.fulfill(status=200,content_type=mimetypes.guess_type(target)[0] or 'application/octet-stream',body=target.read_bytes())
        else:
            request.fulfill(status=503,body='Local browser QA: sample API unavailable')
    page.route('**/*',route)
    page.on('pageerror',lambda error:errors.append(str(error)))

with sync_playwright() as p:
    executable=os.environ.get('ESTAGENT_CHROMIUM')
    options={'executable_path':executable} if executable else {}
    browser=p.chromium.launch(headless=True,args=['--disable-webgl','--disable-gpu'],**options)
    page=browser.new_page(viewport={'width':1440,'height':1000});routes(page)
    page.goto(HOST+'/',wait_until='domcontentloaded',timeout=30000)
    page.wait_for_function("document.querySelector('.flow-tabs').hidden===false")
    print('local landing ready',flush=True)
    assert page.locator('#landing-diagram-image').get_attribute('src') is None
    assert page.locator('.hero-actions a').evaluate_all('(x)=>x.map(a=>a.getAttribute("href"))')==['/demos/seoul-apartment','/business/create']
    assert page.locator('#flow-tab-create').get_attribute('aria-selected')=='true'
    assert page.locator('#flow-visit').is_hidden()
    for width in (1440,1024,768,390,320):
        print('layout '+str(width),flush=True)
        page.set_viewport_size({'width':width,'height':1000 if width>768 else 844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('overflow',width)
        page.locator('#flow-tab-create').click()
        if width in (1440,390,320):
            page.locator('#inside').screenshot(path=str(OUT/f'creator-flow-{width}.png'))
        page.locator('#flow-tab-create').focus();page.keyboard.press('ArrowRight')
        assert page.locator('#flow-tab-visit').get_attribute('aria-selected')=='true'
        assert page.locator('#flow-create').is_hidden() and page.locator('#flow-visit').is_visible()
        if width in (1440,390):page.locator('#inside').screenshot(path=str(OUT/f'visitor-flow-{width}.png'))
        trigger=page.locator('#flow-visit .diagram-link');trigger.click()
        page.wait_for_function('document.querySelector("#landing-diagram-image").naturalWidth===1920')
        assert page.locator('#landing-diagram').is_visible()
        page.wait_for_function("getComputedStyle(document.querySelector('#landing-diagram')).opacity==='1'")
        assert page.locator('#landing-diagram-title').inner_text()=='Spatial context assistant'
        if width in (1440,390):page.screenshot(path=str(OUT/f'diagram-{width}.png'))
        page.keyboard.press('Escape')
        assert not page.locator('#landing-diagram').is_visible()
        assert trigger.evaluate('(el)=>document.activeElement===el')
        page.wait_for_function("!document.body.classList.contains('landing-diagram-open')")
        page.locator('#flow-tab-visit').focus();page.keyboard.press('Home')
        assert page.locator('#flow-tab-create').get_attribute('aria-selected')=='true'
        page.locator('#flow-create .diagram-link').click()
        page.wait_for_function('document.querySelector("#landing-diagram-image").naturalWidth===1920')
        assert page.locator('#landing-diagram-title').inner_text()=='Tour generation'
        page.get_by_role('button',name='Close diagram').click()
        assert not page.locator('#landing-diagram').is_visible()
        layouts.append({'width':width,'tabs':'PASS','diagrams':'PASS','keyboard':'PASS','no_overflow':True})

    page.set_viewport_size({'width':1440,'height':1000});page.evaluate('scrollTo(0,0)')
    page.emulate_media(reduced_motion='reduce')
    page.locator('#flow-tab-visit').click()
    assert page.locator('#flow-visit').evaluate('(el)=>getComputedStyle(el).animationName')=='none'
    page.set_viewport_size({'width':390,'height':844});page.evaluate('scrollTo(0,0)')
    page.locator('.menu-toggle').click();assert page.locator('#nav-links').is_visible()
    page.locator('#nav-links a[href="#how"]').click();assert page.locator('.menu-toggle').get_attribute('aria-expanded')=='false'
    fallback=browser.new_page(java_script_enabled=False,viewport={'width':390,'height':844});routes(fallback)
    fallback.goto(HOST+'/',wait_until='domcontentloaded',timeout=60000)
    assert fallback.locator('#flow-create').is_visible() and fallback.locator('#flow-visit').is_visible()
    assert fallback.locator('[role=tablist]').is_hidden()
    assert not errors,errors
    assert not writes,writes
    browser.close()

result={'status':'PASS','base':BASE,'source_overrides':'local file routes only; no server mutation; WebGL disabled for isolated landing UI QA',
    'preserved':preserved,'original_app_prefix':True,'original_css_prefix':True,
    'image_sha256':images,'layouts':layouts,'hero_preservation':'exact HTML, CSS prefix and JS prefix checks; real WebGL interaction not revalidated by this isolated UI check',
    'reduced_motion':True,'mobile_menu':True,'no_js_fallback':True,'page_errors':errors,'production_writes':writes,'provider_calls':0}
(OUT/'browser.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'PASS','layouts':len(layouts),'page_errors':errors,'production_writes':writes,'preserved':['hero','how','footer','app prefix','CSS prefix']},ensure_ascii=False))
