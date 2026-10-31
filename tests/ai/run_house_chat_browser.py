"""Real local HTTP/SQLite/LangGraph + browser; mock model and PCM tone, not live speech.
Uses public approved guide + source manifest supplied as CLI paths, never private keys.
"""
import argparse,json,subprocess,threading,socket,tempfile,sys,os
# Isolate import-time default app from other local QA processes.
os.environ["ASSISTANT_DB"]=tempfile.mkdtemp(prefix="house-chat-import-")+"/checkpoints.sqlite"
from pathlib import Path
import uvicorn
from fastapi.responses import HTMLResponse,Response,FileResponse
from server.assistant.app import create_app
from server.demo_chat.snapshots import build_snapshot,scene_id
from tests.ai.test_house_chat import FixtureProvider,wav

p=argparse.ArgumentParser();p.add_argument('--house',required=True);p.add_argument('--guide',required=True);p.add_argument('--output',required=True);p.add_argument('--live-wav');args=p.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
house=json.loads(Path(args.house).read_text());guide=json.loads(Path(args.guide).read_text());doc=build_snapshot(house,guide)
for track in guide:track['url']='/qa/tone'
class Provider(FixtureProvider):
    def answer(self,c):
        self.calls.append(('text',c));target=next(s for s in c['tour']['scenes'] if 'garage' in s['name'].lower())
        return {'reply':'Fixture: '+c['current_scene']['name'] if c['current_scene'] else 'Fixture: whole home','changes':[],'order':None,'start_scene_id':target['id'] if 'garage' in c['text'] else None}
class Ready(uvicorn.Server):
    async def startup(self,sockets=None):
        await super().startup(sockets);ready.set()
with tempfile.TemporaryDirectory(prefix='house-chat-browser-') as temp:
    root=Path(temp);snap=root/'snapshots';snap.mkdir();(snap/(doc['id']+'.json')).write_text(json.dumps(doc))
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}';provider=Provider()
    env={'ASSISTANT_ORIGIN':base,'TOUR_PUBLIC_SNAPSHOTS_DIR':str(snap),'TOUR_CHAT_ENABLED':'1','TOUR_CHAT_TEXT_ATTEMPTS':'20','TOUR_CHAT_STT_ATTEMPTS':'2','TOUR_CHAT_TTS_ATTEMPTS':'2'}
    app=create_app(db_path=root/'checkpoints.sqlite',env=env,tour_chat_provider=provider)
    @app.get('/qa/house')
    def page():return HTMLResponse('''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>House chat fixture QA</title><link rel="stylesheet" href="/demos/static/chat-panel.css"><h1>Local QA — fixture room controls, fixture model</h1><div id="app"><button id="houseMode" class="active">House</button><button id="panoMode">Panorama</button><div id="rooms"></div><div id="captures"></div><div id="notice"></div><div id="viewport"></div></div><details id="demo-source"><div></div></details><script type="module">
const house=await fetch('/api/demos/zind-house-000/assets/house/manifest.json').then(r=>r.json());
for(const room of house.rooms){const b=document.createElement('button');b.dataset.room=room.id;b.textContent=room.label;b.onclick=()=>{document.querySelectorAll('#rooms button').forEach(x=>x.classList.toggle('active',x===b));const captures=document.querySelector('#captures');captures.replaceChildren();for(const id of room.dollhouseCaptureIds){const c=document.createElement('button');c.dataset.id=id;c.textContent=id;c.onclick=()=>{captures.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===c));};captures.append(c);}captures.firstChild.click();};document.querySelector('#rooms').append(b);}
document.querySelector('#rooms button').click();document.querySelector('#panoMode').onclick=()=>document.querySelector('#panoMode').classList.add('active');
await import('/demos/static/house.js');await import('/demos/static/chat-bootstrap.js');</script>''')
    # Production demo catalog routes intentionally 404 without MinIO catalog; remove only these QA replacements.
    app.router.routes=[r for r in app.router.routes if getattr(r,'path','') not in {'/api/demos/{demo_id}/intro','/api/demos/{demo_id}/guide','/api/demos/{demo_id}/assets/{name:path}'}]
    @app.get('/api/demos/zind-house-000/guide')
    def guides():return guide
    @app.get('/api/demos/zind-house-000/assets/house/manifest.json')
    def manifest():return house
    @app.get('/api/demos/zind-house-000/intro')
    def intro():return []
    @app.get('/qa/live')
    def live():return FileResponse(args.live_wav,media_type='audio/wav')
    @app.get('/qa/tone')
    def tone():return Response(wav(24000,10),media_type='audio/wav')
    ready=threading.Event();server=Ready(uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
    if not ready.wait(15):raise RuntimeError('Local server failed')
    name='house-chat-'+str(port)
    def browser(*argv):
        result=subprocess.run(['playwright-cli','-s='+name,'--raw',*argv],capture_output=True,text=True,timeout=90)
        if result.returncode or '### Error' in result.stdout:
            debug=subprocess.run(['playwright-cli','-s='+name,'snapshot'],capture_output=True,text=True,timeout=15)
            (out/'failure-snapshot.log').write_text(debug.stdout+debug.stderr)
            raise RuntimeError(result.stdout+result.stderr)
        return result.stdout
    try:
        browser('open','about:blank')
        source='''async page=>{
const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('__BASE__/qa/house');await page.locator('#chat-toggle').waitFor();await page.waitForFunction(()=>document.querySelector('#demo-guide .guide-toggle')&&!document.querySelector('#demo-guide .guide-toggle').disabled);if(await page.locator('#demo-guide audio').evaluate(a=>a.paused))await page.locator('#demo-guide .guide-toggle').click();await page.waitForFunction(()=>!document.querySelector('#demo-guide audio').paused);await page.locator('#chat-toggle').click();await page.waitForFunction(()=>!document.querySelector('#demo-chat button[type=submit]').disabled);if(!await page.locator('#demo-guide audio').evaluate(a=>a.paused))throw Error('Tour voice overlaps');
await page.locator('#demo-chat textarea').fill('Describe this room');await page.locator('#demo-chat button[type=submit]').click();await page.waitForFunction(()=>document.querySelectorAll('.demo-chat-message.assistant').length===1);if(!await page.locator('.demo-chat-message.assistant').innerText().then(t=>t.includes('pano_15')))throw Error('Missing current room');
await page.reload();await page.locator('#chat-toggle').click();await page.waitForFunction(()=>document.querySelectorAll('.demo-chat-message.assistant').length===1);
await page.locator('.demo-chat-message.assistant button').last().click();await page.waitForFunction(()=>{const a=document.querySelector('#demo-chat audio');return a&&!a.paused&&a.duration>0;});
await page.locator('#demo-chat textarea').fill('Take me to garage');await page.locator('#demo-chat button[type=submit]').click();await page.waitForFunction(()=>document.querySelector('#captures button.active')?.dataset.id==='pano_34');
await page.setViewportSize({width:390,height:844});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Horizontal overflow');const panel=await page.locator('#demo-chat').boundingBox();if(panel.x<0||panel.x+panel.width>390)throw Error('Chat clipped on mobile');await page.screenshot({path:'__OUTPUT__/browser.png'});
await page.evaluate(()=>{const Original=AudioContext;navigator.mediaDevices.getUserMedia=async()=>{const c=new Original(),o=c.createOscillator(),dest=c.createMediaStreamDestination();o.connect(dest);o.start();const stream=dest.stream;stream.getTracks().forEach(t=>{const stop=t.stop.bind(t);t.stop=()=>{stop();o.stop();c.close();};});return stream;};});
await page.getByRole('button',{name:'Nói / Speak',exact:true}).click();await page.getByRole('button',{name:'Dừng ghi / Stop recording',exact:true}).waitFor();await page.waitForFunction(()=>document.querySelector('#demo-chat button[type=submit]').disabled);await page.evaluate(()=>new Promise(resolve=>setTimeout(resolve,600)));await page.getByRole('button',{name:'Dừng ghi / Stop recording',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#demo-chat textarea').value==='Describe this room.');
if(errors.length)throw Error(JSON.stringify(errors));return JSON.stringify({pass:true,currentRoom:true,reloadHistory:true,navigation:true,voicePlayback:true,microphoneFixture:true,tourPause:true,mobile:true,errors});}'''.replace('__BASE__',base).replace('__OUTPUT__',str(out))
        result=browser('run-code',source);(out/'browser.log').write_text(result);print(result)
        parsed=json.loads(result)
        if isinstance(parsed,str):parsed=json.loads(parsed)
        assert parsed['pass']
        assert [c[0] for c in provider.calls]==['text','tts','text','stt'],provider.calls
        if args.live_wav:
            live=browser('run-code', '''async page=>{await page.evaluate(()=>{window.liveQA=new Audio('/qa/live');return liveQA.play();});await page.waitForFunction(()=>liveQA.duration>0&&!liveQA.paused);const result=await page.evaluate(()=>({liveDuration:liveQA.duration,playing:!liveQA.paused}));await page.evaluate(()=>liveQA.pause());return result;}''');(out/'live-playback.log').write_text(live);print(live)
        app.state.visitor_chat.configured=False;app.state.visitor_chat.voice_configured=False
        keyless=browser('run-code', '''async page=>{await page.reload();await page.locator('#chat-toggle').click();await page.getByRole('status').filter({hasText:'Chat chưa được kết nối'}).waitFor();if(!await page.locator('#demo-chat button[type=submit]').isDisabled())throw Error('Keyless send enabled');if(!await page.getByRole('button',{name:'Nói / Speak',exact:true}).isDisabled())throw Error('Keyless mic enabled');return JSON.stringify({pass:true,keyless:true});}''')
        (out/'keyless.log').write_text(keyless);print(keyless)
    finally:
        browser('close');server.should_exit=True;thread.join(10)
