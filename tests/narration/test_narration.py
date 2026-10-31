import hashlib
import io
import sqlite3
import threading
import wave
import pytest
from fastapi.testclient import TestClient
from tests.ai.test_tour_audio import start,draft,post,attach,HEADERS
from tests.narration.fixtures import build,SpeechSDK


def payload(doc,locale='en',text='Welcome to the tour.',request='request-en-001'):
    return {'draft_id':doc['id'],'scene_id':doc['scenes'][0]['id'],'revision':doc['revision'],
            'locale':locale,'voice':'marin','text':text,'approved':True,
            'script_sha256':hashlib.sha256(text.encode()).hexdigest(),'request_id':request}

def generate(c,s,p):
    r=post(c,'/narration/jobs',p);assert r.status_code==202,r.text
    s.queue.join();return c.get('/api/tours/narration/jobs/'+r.json()['id']).json()


def test_bilingual_sdk_minio_attach_review_publish_snapshot(tmp_path):
    app,s,sdk,objects=build(tmp_path)
    try:
        with TestClient(app) as c:
            start(c);doc=draft(c);original=doc
            p=payload(doc);job=generate(c,s,p)
            assert job['status']=='completed',job
            assert len(sdk.calls)==1 and sdk.calls[0]['model']=='gpt-4o-mini-tts'
            assert sdk.calls[0]['voice']=='marin' and sdk.calls[0]['response_format']=='pcm'
            assert 'English' in sdk.calls[0]['instructions']
            r=c.get(job['track']['url']);assert r.status_code==200
            with wave.open(io.BytesIO(r.content)) as wav:
                assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate(),wav.getnframes())==(1,2,24000,24000)
            assert job['track']['duration_seconds']==1
            doc=post(c,f'/narration/jobs/{job["id"]}/attach',{'revision':1}).json()
            assert doc['revision']==2 and doc['audio']['source']=='openai_generated'
            assert post(c,f'/narration/jobs/{job["id"]}/attach',{'revision':1}).json()==doc
            assert post(c,'/narration/jobs',p).json()['id']==job['id'] # replay after revision changed
            vi=generate(c,s,payload(doc,'vi','Chào mừng bạn đến với tour.','request-vi-001'))
            assert 'Vietnamese' in sdk.calls[1]['instructions']
            doc=post(c,f'/narration/jobs/{vi["id"]}/attach',{'revision':2}).json()
            assert len(doc['audio']['narration'])==2
            assert {n['locale'] for n in doc['audio']['narration']}=={'en','vi'}
            assert post(c,f'/drafts/{doc["id"]}/publish',{'revision':3}).status_code==409
            assert post(c,f'/drafts/{doc["id"]}/review',{'revision':3}).status_code==200
            response=post(c,f'/drafts/{doc["id"]}/publish',{'revision':3});assert response.status_code==200,response.text
            snapshot=response.json()
            assert attach(c,doc).status_code==200
            assert c.get('/api/tours/published/'+snapshot['id']).json()==snapshot
            assert not list(tmp_path.rglob('*.wav'))
            c.cookies.clear()
            for narration in snapshot['audio']['narration']:
                assert c.get(narration['track']['url'],headers={'Range':'bytes=0-43'}).status_code==206
            assert c.get(f'/api/tours/published/{snapshot["id"]}/audio/'+('a'*32)).status_code==404
            start(c)
            assert c.get('/api/tours/narration/jobs/'+job['id']).status_code==404
            assert post(c,f'/narration/jobs/{job["id"]}/attach',{'revision':1}).status_code==404
            assert post(c,'/narration/jobs',payload(original,request='other-owner-001')).status_code==404
    finally:s.close()


def test_review_hash_origin_stale_missing_key(tmp_path):
    app,s,_,_=build(tmp_path)
    try:
        with TestClient(app) as c:
            start(c);doc=draft(c);p=payload(doc)
            for change in [{'approved':False},{'script_sha256':'0'*64},{'voice':'custom'},{'locale':'fr'}]:
                assert post(c,'/narration/jobs',p|change).status_code==422
            assert c.post('/api/tours/narration/jobs',json=p).status_code==403
            assert post(c,'/narration/jobs',p|{'revision':99}).status_code==409
            assert post(c,'/narration/jobs',p|{'scene_id':'f'*32}).status_code==422
            job=generate(c,s,p)
            assert post(c,'/narration/jobs',p|{'voice':'coral'}).status_code==409
            changed=attach(c,doc).json()
            assert post(c,f'/narration/jobs/{job["id"]}/attach',{'revision':1}).status_code==409
    finally:s.close()
    app,s,_,_=build(tmp_path/'keyless',{'FIXTURE_PROVIDER':'0'})
    try:
        with TestClient(app) as c:
            start(c);doc=draft(c)
            assert c.get('/api/tours/narration/config').json()['configured'] is False
            r=post(c,'/narration/jobs',payload(doc));assert r.status_code==503 and 'OPENAI_TTS_API_KEY' in r.text
    finally:s.close()


def test_cancel_queue_stale_and_errors_no_retry(tmp_path):
    sdk=SpeechSDK();sdk.release=threading.Event()
    app,s,_,_=build(tmp_path,{'NARRATION_QUEUE_SIZE':'1'},sdk=sdk)
    try:
        with TestClient(app) as c:
            start(c);doc=draft(c);p=payload(doc)
            job=post(c,'/narration/jobs',p).json();assert sdk.entered.wait(5)
            assert post(c,'/narration/jobs',p|{'request_id':'second-request'}).status_code==429
            assert post(c,f'/narration/jobs/{job["id"]}/cancel',{}).status_code==200
            sdk.release.set();s.queue.join()
            assert c.get('/api/tours/narration/jobs/'+job['id']).json()['status']=='cancelled'
            assert post(c,f'/narration/jobs/{job["id"]}/attach',{'revision':1}).status_code==409
            sdk.entered.clear();sdk.release.clear()
            stale=post(c,'/narration/jobs',p|{'request_id':'stale-request'}).json();assert sdk.entered.wait(5)
            doc=attach(c,doc).json();sdk.release.set();s.queue.join()
            assert c.get('/api/tours/narration/jobs/'+stale['id']).json()['error']=='stale_revision'
            sdk.failure=True
            error=generate(c,s,payload(doc,request='error-request'))
            assert error['error']=='generation_failed' and 'PRIVATE' not in str(error)
            assert len(sdk.calls)==3
    finally:sdk.release.set();s.close()


def test_persisted_global_allowance_cache_expiry_clock_rollback(tmp_path):
    clock=[1000.0];app,s,sdk,_=build(tmp_path,{'NARRATION_ATTEMPTS':'3'},clock=lambda:clock[0])
    try:
        with TestClient(app) as c:
            cookie=start(c);doc=draft(c);p=payload(doc)
            first=generate(c,s,p)
            clock[0]=1050
            cached=generate(c,s,p|{'request_id':'cache-request'})
            assert cached['track']==first['track'] and len(sdk.calls)==1
            clock[0]=1061
            fresh=generate(c,s,p|{'request_id':'expired-request'})
            assert fresh['track']['asset_id']!=first['track']['asset_id'] and len(sdk.calls)==2
            clock[0]=900
            assert post(c,'/narration/jobs',p|{'request_id':'exhausted-request'}).status_code==429
    finally:s.close()
    app,s,_,_=build(tmp_path,{'NARRATION_ATTEMPTS':'3'},clock=lambda:1062)
    try:
        with TestClient(app) as c:
            c.cookies.set('estagent_tours',cookie,path='/api/tours/')
            assert post(c,'/narration/jobs',p|{'request_id':'restart-request'}).status_code==429
        with sqlite3.connect(tmp_path/'tours'/'narration.sqlite') as conn:
            assert conn.execute('SELECT attempts,characters FROM allowance').fetchone()==(3,len(p['text'])*3)
    finally:s.close()


def test_explicit_config_limits(tmp_path):
    for env in [{'NARRATION_ATTEMPTS':''},{'NARRATION_TIMEOUT_SECONDS':'61'},{'NARRATION_MAX_SCRIPT_CHARS':'2001'}]:
        with pytest.raises(ValueError):build(tmp_path,env)
    app,s,_,_=build(tmp_path/'small',{'NARRATION_CHARACTERS':'10'})
    try:
        with TestClient(app) as c:
            start(c);doc=draft(c)
            assert post(c,'/narration/jobs',payload(doc)).status_code==429
    finally:s.close()


def test_no_relabel_no_forged_provenance_and_single_worker(tmp_path):
    app,s,_,_=build(tmp_path)
    try:
        with pytest.raises(ValueError,match='one worker'):build(tmp_path)
        with TestClient(app) as c:
            start(c);doc=draft(c);job=generate(c,s,payload(doc))
            binding={'scene_id':doc['scenes'][0]['id'],'locale':'vi','asset_id':job['track']['asset_id'],'transcript':job['text']}
            assert attach(c,doc,narration=[binding]).status_code==422
            assert attach(c,doc,narration=[binding|{'locale':'en','transcript':'Different script'}]).status_code==422
            p=payload(doc,text=' Welcome ')
            assert post(c,'/narration/jobs',p).status_code==422
            # Clients never submit generation metadata in upload provenance.
            from tests.ai.test_tour_audio import upload,PROVENANCE
            assert upload(c,provenance=PROVENANCE|{'generation':job['track']['generation']}).status_code==422
    finally:s.close()


def test_registration_failure_cleans_new_object_and_consumes_attempt(tmp_path):
    app,s,sdk,objects=build(tmp_path)
    try:
        with TestClient(app) as c:
            start(c);doc=draft(c);before=dict(objects.objects)
            with sqlite3.connect(tmp_path/'tours'/'tours.sqlite') as conn:
                conn.execute('CREATE TABLE IF NOT EXISTS audio_assets(id TEXT PRIMARY KEY,owner TEXT,digest TEXT,metadata TEXT)')
                conn.execute("CREATE TRIGGER reject_audio BEFORE INSERT ON audio_assets BEGIN SELECT RAISE(ABORT,'synthetic registration error'); END")
            job=generate(c,s,payload(doc))
            assert job['status']=='error' and job['error']=='generation_failed'
            assert objects.objects==before and len(sdk.calls)==1
            with sqlite3.connect(tmp_path/'tours'/'narration.sqlite') as conn:
                assert conn.execute('SELECT attempts FROM allowance').fetchone()[0]==1
    finally:s.close()
