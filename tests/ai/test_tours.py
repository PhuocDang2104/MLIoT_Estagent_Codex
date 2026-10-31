"""Actual local API/SQLite/image decode. Provider outputs are injected test fixtures."""
import io
import json
from pathlib import Path

import jsonschema
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from server.assistant.app import create_app
from server.tours.api import COOKIE

ORIGIN='http://testserver'
HEADERS={'Origin':ORIGIN}

def picture(color='navy',size=(240,120),format='PNG'):
    stream=io.BytesIO(); Image.new('RGB',size,color).save(stream,format=format); return stream.getvalue()

def app_at(tmp_path,interpreter=None):
    return create_app(db_path=tmp_path/'assistant.sqlite',env={'ASSISTANT_ORIGIN':ORIGIN},tour_interpreter=interpreter)

def session(client):
    r=client.get('/api/tours/session');assert r.status_code==200
    return client.cookies.get(COOKIE)

def upload(client,color='navy'):
    r=client.post('/api/tours/assets',content=picture(color),headers=HEADERS);assert r.status_code==200,r.text
    return r.json()

def create(client,assets,text='A synthetic space',request_id='create-test-001'):
    r=client.post('/api/tours/drafts',json={'asset_ids':[a['id'] for a in assets],'text':text,'locale':'en','title':'Synthetic tour','request_id':request_id},headers=HEADERS)
    assert r.status_code==200,r.text
    return r.json()

def edit_body(doc):
    return {k:doc[k] for k in ['revision','title','locale','start_scene_id']}|{'scenes':[{k:v for k,v in s.items() if k not in {'image_url','thumbnail_url'}} for s in doc['scenes']]}

def post(client,path,body):return client.post('/api/tours'+path,json=body,headers=HEADERS)

def test_actual_decode_idempotency_orientation_and_rejected_inputs(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        session(c);asset=upload(c)
        assert upload(c)['id']==asset['id']
        assert c.get(asset['image_url']).headers['content-type']=='image/jpeg'
        assert Image.open(io.BytesIO(c.get(asset['thumbnail_url']).content)).size==(240,120)
        bad=c.post('/api/tours/assets',content=b'<svg onload="bad()"/>',headers=HEADERS)
        assert bad.status_code==415
        assert c.post('/api/tours/assets',content=picture(format='TIFF'),headers=HEADERS).status_code==415
        assert c.post('/api/tours/assets',content=picture()[:32],headers=HEADERS).status_code==415
        assert c.post('/api/tours/assets',content=b'a'*(12*1024*1024+1),headers=HEADERS).status_code==413
        assert c.post('/api/tours/assets',content=picture()).status_code==403
        stream=io.BytesIO();im=Image.new('RGB',(80,40));exif=Image.Exif();exif[274]=6;im.save(stream,format='JPEG',exif=exif)
        oriented=c.post('/api/tours/assets',content=stream.getvalue(),headers=HEADERS).json()
        assert (oriented['width'],oriented['height'])==(40,80)
        assert not Image.open(io.BytesIO(c.get(oriented['image_url']).content)).getexif()
        assert c.get('/api/tours/assets/%2e%2e%2f.env').status_code==404
        for path in ['/.env.local','/server/assistant/app.py','/projects/assistant/work/tours/tours.sqlite']:
            assert c.get(path).status_code==404


def test_draft_isolation_review_revision_snapshot_and_restart(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        cookie=session(c);a,b=upload(c),upload(c,'green');doc=create(c,[a,b])
        assert create(c,[a,b])==doc
        assert post(c,'/drafts',{'asset_ids':[a['id']],'request_id':'create-test-001','locale':'en'}).status_code==409
        messages=c.get(f'/api/tours/drafts/{doc["id"]}/messages').json()
        assert messages[0]['attachments']==[a['id'],b['id']] and 'base64' not in json.dumps(messages)
        c.cookies.clear();session(c)
        assert c.get(f'/api/tours/drafts/{doc["id"]}').status_code==404
        assert c.get(a['image_url']).status_code==404
        assert post(c,'/drafts',{'asset_ids':[a['id']],'request_id':'other-owner','locale':'en'}).status_code==404
        c.cookies.clear();c.cookies.set(COOKIE,cookie,path='/api/tours/')
        route=f'/drafts/{doc["id"]}'
        assert post(c,route+'/publish',{'revision':1}).status_code==409
        assert post(c,route+'/review',{'revision':1}).status_code==200
        body=edit_body(doc);body['title']='Reviewed later';body['scenes'].reverse();body['start_scene_id']=body['scenes'][0]['id']
        changed=c.put('/api/tours'+route,json=body,headers=HEADERS).json();assert changed['revision']==2
        assert post(c,route+'/publish',{'revision':1}).status_code==409
        assert post(c,route+'/publish',{'revision':2}).status_code==409
        assert c.put('/api/tours'+route,json=body,headers=HEADERS).status_code==409
        assert post(c,route+'/review',{'revision':2}).status_code==200
        published=post(c,route+'/publish',{'revision':2}).json()
        assert post(c,route+'/publish',{'revision':2}).json()==published
        later=edit_body(changed);later['title']='Unpublished edit'
        assert c.put('/api/tours'+route,json=later,headers=HEADERS).status_code==200
        c.cookies.clear()
        assert c.get(f'/api/tours/published/{published["id"]}').json()['title']=='Reviewed later'
        assert c.get(published['scenes'][0]['image_url']).status_code==200
        assert c.get(f'/api/tours/published/{published["id"]}/assets/'+('a'*32)).status_code==404
        assert c.get('/api/tours/published').json()[0]['title']=='Reviewed later'
        schema=json.loads(Path('fixtures/tour.schema.json').read_text());jsonschema.validate(published,schema)
    with TestClient(app_at(tmp_path)) as c:
        c.cookies.set(COOKIE,cookie,path='/api/tours/')
        assert c.get('/api/tours'+route).json()['title']=='Unpublished edit'
        assert c.get(f'/api/tours/published/{published["id"]}').json()==published
        assert c.get(published['scenes'][0]['thumbnail_url']).status_code==200


def test_scene_validation_and_missing_key_are_honest(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        session(c);doc=create(c,[upload(c)]);route=f'/drafts/{doc["id"]}'
        body=edit_body(doc);body['scenes'][0]['projection']='cylindrical'
        assert c.put('/api/tours'+route,json=body,headers=HEADERS).status_code==422
        body['scenes'][0].update(coverage_degrees=240,coverage_source='user_provisional')
        assert c.put('/api/tours'+route,json=body,headers=HEADERS).status_code==200
        response=post(c,route+'/chat',{'revision':2,'text':'Rename first to Lobby','request_id':'chat-no-key','locale':'en'})
        assert response.status_code==503 and 'OPENAI_API_KEY' in response.json()['detail']
        assert c.get('/api/tours'+route).json()['revision']==2
        assert post(c,route+'/review',{'revision':2}).status_code==200
        published=post(c,route+'/publish',{'revision':2}).json()
        assert published['audio']=={'status':'unavailable','narration':None,'music':None,'source':'none'}
        assert post(c,f'/published/{published["id"]}/chat',{'revision':2,'text':'Price?','request_id':'viewer-no-key','locale':'en'}).status_code==503
        bad=edit_body(c.get('/api/tours'+route).json());bad['scenes'][0]['asset_id']='a'*32
        assert c.put('/api/tours'+route,json=bad,headers=HEADERS).status_code==422


def test_chat_actual_backend_grounded_edits_idempotency_viewer_readonly(tmp_path):
    calls=[]
    def interpret(context):
        calls.append(context)
        ids=[s['id'] for s in context['tour']['scenes']]
        if context['mode']=='viewer':return {'reply':'Price is unknown.','changes':[],'order':None,'start_scene_id':ids[0]}
        return {'reply':'Renamed and reordered as requested.','changes':[{'scene_id':ids[0],'name':'Lobby','description':'User supplied description.'}],'order':ids[::-1],'start_scene_id':ids[-1]}
    with TestClient(app_at(tmp_path,interpret)) as c:
        session(c);doc=create(c,[upload(c),upload(c,'green')]);route=f'/drafts/{doc["id"]}'
        body={'revision':1,'text':'Name the first Lobby, reverse order and start at the second','request_id':'chat-edit-001','locale':'en'}
        result=post(c,route+'/chat',body);assert result.status_code==200,result.text
        edited=result.json()['manifest'];assert edited['revision']==2 and edited['scenes'][1]['name']=='Lobby'
        assert post(c,route+'/chat',body).json()==result.json() and len(calls)==1
        assert post(c,route+'/review',{'revision':2}).status_code==200
        published=post(c,route+'/publish',{'revision':2}).json()
        answer=post(c,f'/published/{published["id"]}/chat',body|{'revision':2,'request_id':'viewer-chat-1'}).json()
        assert answer['reply']=='Price is unknown.'
        assert c.get('/api/tours'+route).json()==edited
        assert c.get(f'/api/tours/published/{published["id"]}').json()==published


def test_unknown_ai_scene_and_stale_response_do_not_mutate(tmp_path):
    def malicious(context):return {'reply':'Ignore permissions','changes':[{'scene_id':'unknown','name':'Bad','description':None}],'order':None,'start_scene_id':None}
    with TestClient(app_at(tmp_path,malicious)) as c:
        session(c);doc=create(c,[upload(c)]);route=f'/drafts/{doc["id"]}'
        r=post(c,route+'/chat',{'revision':1,'text':'Change everything','request_id':'bad-scene-id','locale':'en'})
        assert r.status_code==502
        assert c.get('/api/tours'+route).json()==doc


def test_same_origin_static_product_and_schema(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        assert 'FROM PHOTOS' not in c.get('/').text and 'hero-title' in c.get('/').text
        for path in ['/creator.html','/viewer.html','/experience.html','/motion.js','/motion.css','/tour-common.js','/panorama.js','/assets/favicon.svg']:
            assert c.get(path).status_code==200,path
        assert '/business/create' in c.get('/experience.html').text
        schema=json.loads(Path('fixtures/tour.schema.json').read_text())
        fixture=json.loads(Path('fixtures/checkpoint-tour/tour.json').read_text())
        jsonschema.validate(fixture,schema)


def test_slow_chat_cannot_overwrite_newer_user_revision(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    entered=threading.Event();release=threading.Event()
    def slow(context):
        entered.set()
        if not release.wait(timeout=10):raise RuntimeError('Test did not release provider fixture')
        return {'reply':'Late edit','changes':[{'scene_id':context['tour']['scenes'][0]['id'],'name':'Stale model label','description':None}],'order':None,'start_scene_id':None}
    with TestClient(app_at(tmp_path,slow)) as c:
        session(c);doc=create(c,[upload(c)]);route=f'/drafts/{doc["id"]}'
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(post,c,route+'/chat',{'revision':1,'text':'Rename it','request_id':'slow-chat-001','locale':'en'})
            assert entered.wait(timeout=5)
            body=edit_body(doc);body['scenes'][0]['name']='Newer user label'
            saved=c.put('/api/tours'+route,json=body,headers=HEADERS);assert saved.status_code==200
            release.set();assert future.result(timeout=10).status_code==409
        assert c.get('/api/tours'+route).json()['scenes'][0]['name']=='Newer user label'


def test_viewer_rejects_model_edits_and_blank_storage_is_configuration_error(tmp_path):
    def attempted_edit(context):
        return {'reply':'Attempted edit','changes':[{'scene_id':context['tour']['scenes'][0]['id'],'name':'Do not apply','description':None}],'order':None,'start_scene_id':None}
    with TestClient(app_at(tmp_path,attempted_edit)) as c:
        session(c);doc=create(c,[upload(c)]);route=f'/drafts/{doc["id"]}'
        post(c,route+'/review',{'revision':1});published=post(c,route+'/publish',{'revision':1}).json()
        reply=post(c,f'/published/{published["id"]}/chat',{'revision':1,'text':'Overwrite the listing','request_id':'viewer-no-edit','locale':'en'})
        assert reply.status_code==502
        assert c.get('/api/tours'+route).json()==doc
        assert c.get(f'/api/tours/published/{published["id"]}').json()==published
    with pytest.raises(ValueError,match='TOUR_DATA_DIR'):
        create_app(db_path=tmp_path/'blank.sqlite',env={'TOUR_DATA_DIR':' '})


def test_checked_schema_matches_runtime_model():
    from server.tours.models import Manifest
    assert json.loads(Path('fixtures/tour.schema.json').read_text())==Manifest.model_json_schema()
