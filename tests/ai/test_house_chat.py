"""Existing public-tour Chat/Manifest contract; provider audio below is a tone fixture."""
import io,json,wave,math,struct
import pytest
from fastapi.testclient import TestClient
from server.assistant.app import create_app
from server.demo_chat.snapshots import build_snapshot,scene_id

ORIGIN='http://127.0.0.1:5180'
ID='a'*32
SCENE='b'*32

def wav(rate=16000,duration=1):
    out=io.BytesIO()
    with wave.open(out,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        w.writeframes(b''.join(struct.pack('<h',int(1000*math.sin(i/20))) for i in range(rate*duration)))
    return out.getvalue()

class FixtureProvider:
    tts_model='fixture-tone-not-speech'
    def __init__(self):self.calls=[]
    def answer(self,c):
        self.calls.append(('text',c))
        return {'reply':'The supplied description shows a sliding door.','changes':[],'order':None,'start_scene_id':SCENE if c['text']=='navigate' else None}
    def transcribe(self,body,locale):self.calls.append(('stt',locale));return 'Describe this room.'
    def speech(self,text,locale):self.calls.append(('tts',locale));return wav(24000)

def setup(tmp_path,provider=None,**extra):
    snapshots=tmp_path/'snapshots';snapshots.mkdir(exist_ok=True)
    doc={'id':ID,'revision':1,'status':'published','title':'Approved demo','locale':'en','scenes':[{'id':SCENE,'asset_id':'c'*32,'name':'Living room','description':'A sliding door is visible.','projection':'photo','image_url':'/image.jpg','thumbnail_url':'/image.jpg'}],'start_scene_id':SCENE,'credits':['Test fixture']}
    (snapshots/(ID+'.json')).write_text(json.dumps(doc))
    env={'ASSISTANT_ORIGIN':ORIGIN,'TOUR_PUBLIC_SNAPSHOTS_DIR':str(snapshots),'TOUR_CHAT_ENABLED':'1','TOUR_CHAT_TEXT_ATTEMPTS':'4','TOUR_CHAT_STT_ATTEMPTS':'1','TOUR_CHAT_TTS_ATTEMPTS':'1',**extra}
    return create_app(db_path=tmp_path/'checkpoints.sqlite',env=env,tour_chat_provider=provider)

def send(c,id='request-0001',**extra):
    return c.post(f'/api/tours/published/{ID}/chat',json={'text':'Describe this room','locale':'en','request_id':id,'revision':1,'scene_id':SCENE,**extra},headers={'Origin':ORIGIN})

def test_context_persistence_replay_owner_voice(tmp_path):
    provider=FixtureProvider();app=setup(tmp_path,provider)
    with TestClient(app) as c:
        session=c.get('/api/tours/session').json()
        assert session['voice_configured'] and session['viewer_configured']
        assert session['configured'] is False  # Visitor-only key/provider never enables Creator.
        assert send(c).status_code==200
        assert send(c).status_code==200
        assert len(provider.calls)==1
        assert send(c,text='different').status_code==409
        assert send(c,'request-stale',revision=2).status_code==409
        assert send(c,'request-foreign',scene_id='d'*32).status_code==422
        headers={'Origin':ORIGIN,'X-Request-ID':'record-0001','X-Audio-Locale':'en'}
        url=f'/api/tours/published/{ID}'
        assert c.post(url+'/transcribe',content=wav(),headers=headers).json()['text']=='Describe this room.'
        assert c.post(url+'/transcribe',content=wav(),headers=headers).status_code==200
        headers['X-Request-ID']='request-0001'
        response=c.post(url+'/speech',headers=headers);assert response.status_code==200
        with wave.open(io.BytesIO(response.content)) as w:assert w.getnframes()/w.getframerate()==1
        assert c.post(url+'/speech',headers=headers).content==response.content
        assert [x[0] for x in provider.calls]==['text','stt','tts']
        assert len(c.get(url+'/messages').json())==1
        cookies=dict(c.cookies)
        c.cookies.clear();c.get('/api/tours/session')
        assert c.get(url+'/messages').json()==[]
        assert c.post(url+'/speech',headers=headers).status_code==404
        c.cookies.update(cookies)
    with TestClient(setup(tmp_path,provider)) as c:
        c.cookies.update(cookies)
        assert len(c.get(url+'/messages').json())==1
        assert send(c).status_code==200
        assert provider.calls[0][1]['current_scene']['id']==SCENE

def test_limits_persist_and_invalid_origin(tmp_path):
    provider=FixtureProvider()
    with TestClient(setup(tmp_path,provider,TOUR_CHAT_TEXT_ATTEMPTS='1')) as c:
        c.get('/api/tours/session');assert send(c).status_code==200
        assert send(c,'request-0002').status_code==429
        assert c.post(f'/api/tours/published/{ID}/speech').status_code==403
    with TestClient(setup(tmp_path,provider,TOUR_CHAT_TEXT_ATTEMPTS='1')) as c:
        c.get('/api/tours/session');assert send(c,'request-0003').status_code==429
    assert len(provider.calls)==1

def test_missing_key_and_required_limits(tmp_path):
    with TestClient(setup(tmp_path)) as c:
        assert c.get('/api/tours/session').json()['configured'] is False
        assert send(c).status_code==503
    with pytest.raises(ValueError,match='TOUR_CHAT_TEXT_ATTEMPTS'):
        setup(tmp_path,TOUR_CHAT_TEXT_ATTEMPTS='')

def test_readonly_graph(tmp_path):
    p=FixtureProvider();p.answer=lambda c:{'reply':'Changed','changes':[],'order':[SCENE],'start_scene_id':None}
    with TestClient(setup(tmp_path,p)) as c:
        c.get('/api/tours/session');assert send(c).status_code==502
        assert c.get(f'/api/tours/published/{ID}').json()['scenes'][0]['name']=='Living room'

def test_failure_not_rebilled_and_voice_validation(tmp_path):
    p=FixtureProvider()
    def fail(c):p.calls.append(('failed',c));raise ValueError('Model returned invalid content')
    p.answer=fail
    with TestClient(setup(tmp_path,p)) as c:
        c.get('/api/tours/session');assert send(c).status_code==502
        assert send(c).status_code==409
        assert len(p.calls)==1
        prefix=f'/api/tours/published/{ID}'
        headers={'Origin':ORIGIN,'X-Request-ID':'voice-0001','X-Audio-Locale':'en'}
        assert c.post(prefix+'/transcribe',content=wav(24000),headers=headers).status_code==422
        assert c.post(prefix+'/transcribe',content=b'x'*640045,headers=headers).status_code==413
        assert len(p.calls)==1

def test_concurrency_rejects_before_provider(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    p=FixtureProvider();started=threading.Event();finish=threading.Event();answer=p.answer
    def wait(c):started.set();assert finish.wait(5);return answer(c)
    p.answer=wait
    with TestClient(setup(tmp_path,p)) as c,ThreadPoolExecutor(max_workers=1) as pool:
        c.get('/api/tours/session');pending=pool.submit(send,c)
        try:
            assert started.wait(5)
            assert send(c,'request-concurrent').status_code==429
        finally:finish.set()
        assert pending.result().status_code==200
    assert len(p.calls)==1
