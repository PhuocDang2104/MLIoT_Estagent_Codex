"""Real HTTP/SQLite chat boundaries; only model outputs are explicit fixtures."""
import io
import json
import sqlite3

from fastapi.testclient import TestClient
from PIL import Image

from server.assistant.app import create_app
from server.tours.api import COOKIE

ORIGIN='http://testserver'
HEADERS={'Origin':ORIGIN}


def app_at(path,interpreter):
    return create_app(db_path=path/'assistant.sqlite',env={'ASSISTANT_ORIGIN':ORIGIN},
                      tour_interpreter=interpreter)


def answer(text='Fixture answer',**changes):
    return {'reply':text,'changes':[],'order':None,'start_scene_id':None,**changes}


def post(client,path,body):
    return client.post('/api/tours'+path,json=body,headers=HEADERS)


def make_tour(client,request_id='create-context-001',text='Private creator brief'):
    client.get('/api/tours/session')
    assets=[]
    for color in ['navy','teal']:
        stream=io.BytesIO();Image.new('RGB',(80,40),color).save(stream,format='PNG')
        r=client.post('/api/tours/assets',content=stream.getvalue(),headers=HEADERS)
        assert r.status_code==200,r.text
        assets.append(r.json()['id'])
    response=post(client,'/drafts',{'asset_ids':assets,'request_id':request_id,'text':text,'locale':'en'})
    assert response.status_code==200,response.text
    return response.json()


def publish(client,doc):
    assert post(client,f'/drafts/{doc["id"]}/review',{'revision':doc['revision']}).status_code==200
    response=post(client,f'/drafts/{doc["id"]}/publish',{'revision':doc['revision']})
    assert response.status_code==200,response.text
    return response.json()


def turn(client,doc,text,request_id,scene_id=None,viewer=False,include_scene=True):
    body={'text':text,'request_id':request_id,'revision':doc['revision'],'locale':'en'}
    if include_scene:body['scene_id']=scene_id
    return post(client,f'/{"published" if viewer else "drafts"}/{doc["id"]}/chat',body)


def test_viewer_active_scene_followup_idempotency_and_snapshot_are_real(tmp_path):
    calls=[]
    def interpret(context):
        calls.append(context)
        return answer('Supplied description only; dimensions remain unknown.')
    with TestClient(app_at(tmp_path,interpret)) as client:
        draft=make_tour(client);doc=publish(client,draft);scene=doc['scenes'][1]
        first=turn(client,doc,'What is known about this room?','viewer-context-001',scene['id'],True)
        assert first.status_code==200,first.text
        assert calls[-1]['mode']=='viewer'
        assert calls[-1]['scene_id']==scene['id'] and calls[-1]['current_scene']==scene
        assert calls[-1]['history']==[]  # Never include the private Creator brief.
        assert turn(client,doc,'What is known about this room?','viewer-context-001',scene['id'],True).json()==first.json()
        assert len(calls)==1
        assert turn(client,doc,'What is known about this room?','viewer-context-001',doc['scenes'][0]['id'],True).status_code==409
        assert turn(client,doc,'And are the measurements verified?','viewer-context-002',scene['id'],True).status_code==200
        assert calls[-1]['history']==[
            {'role':'user','text':'What is known about this room?'},
            {'role':'assistant','text':'Supplied description only; dimensions remain unknown.'}]
        assert client.get(f'/api/tours/published/{doc["id"]}').json()==doc
        assert client.get(f'/api/tours/drafts/{draft["id"]}').json()==draft


def test_viewer_history_is_scoped_to_session_snapshot_and_survives_restart(tmp_path):
    calls=[]
    def interpret(context):calls.append(context);return answer()
    with TestClient(app_at(tmp_path,interpret)) as client:
        draft=make_tour(client);first=publish(client,draft)
        second=publish(client,make_tour(client,'create-context-002'))
        cookie=client.cookies.get(COOKIE)
        assert turn(client,first,'Only this session sees this question','viewer-scope-001',viewer=True).status_code==200
        client.cookies.clear();client.get('/api/tours/session')
        assert turn(client,first,'A separate browser','viewer-scope-001',viewer=True).status_code==200
        assert calls[-1]['history']==[]
        client.cookies.clear();client.cookies.set(COOKIE,cookie,path='/api/tours/')
        assert turn(client,second,'A separate tour','viewer-scope-001',viewer=True).status_code==200
        assert calls[-1]['history']==[]
    with TestClient(app_at(tmp_path,interpret)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/tours/')
        assert turn(client,first,'Continue after restart','viewer-scope-002',viewer=True).status_code==200
        assert calls[-1]['history'][0]['text']=='Only this session sees this question'
        assert all('separate' not in message['text'] for message in calls[-1]['history'])


def test_invalid_scene_is_rejected_before_provider_for_creator_and_viewer(tmp_path):
    calls=[]
    def interpret(context):calls.append(context);return answer()
    with TestClient(app_at(tmp_path,interpret)) as client:
        first=make_tour(client);second=make_tour(client,'create-context-002')
        foreign=second['scenes'][0]['id'];public=publish(client,first)
        assert turn(client,first,'Which room?','creator-bad-scene',foreign).status_code==422
        assert turn(client,public,'Which room?','viewer-bad-scene',foreign,True).status_code==422
        assert turn(client,public,'Which room?','viewer-bad-format','../../private',True).status_code==422
        assert calls==[]


def test_creator_history_context_and_edits_still_require_new_review(tmp_path):
    calls=[]
    def interpret(context):
        calls.append(context)
        if context['text']=='Rename this point':
            return answer('Renamed the selected point.',changes=[{'scene_id':context['scene_id'],
                'name':'User confirmed lobby','description':None}])
        return answer('Which detail would you like to change?')
    with TestClient(app_at(tmp_path,interpret)) as client:
        doc=make_tour(client);scene_id=doc['scenes'][1]['id']
        assert turn(client,doc,'Help with this point','creator-context-001',scene_id).status_code==200
        assert calls[-1]['current_scene']['id']==scene_id
        assert calls[-1]['history']==[{'role':'user','text':'Private creator brief'}]
        assert post(client,f'/drafts/{doc["id"]}/review',{'revision':1}).status_code==200
        response=turn(client,doc,'Rename this point','creator-context-002',scene_id)
        assert response.status_code==200,response.text
        edited=response.json()['manifest']
        assert edited['revision']==2 and edited['scenes'][1]['name']=='User confirmed lobby'
        assert calls[-1]['history'][-2:]==[
            {'role':'user','text':'Help with this point'},
            {'role':'assistant','text':'Which detail would you like to change?'}]
        assert post(client,f'/drafts/{doc["id"]}/publish',{'revision':2}).status_code==409
        other=make_tour(client,'create-context-002','Other private brief')
        assert turn(client,other,'New context','creator-context-003').status_code==200
        assert calls[-1]['history']==[{'role':'user','text':'Other private brief'}]
        client.cookies.clear();client.get('/api/tours/session')
        count=len(calls)
        assert turn(client,edited,'Read another owner','creator-context-004').status_code==404
        assert len(calls)==count


def test_history_is_bounded_without_passing_old_manifest_or_cookie_to_model(tmp_path):
    calls=[]
    def interpret(context):calls.append(context);return answer('A'*2000)
    with TestClient(app_at(tmp_path,interpret)) as client:
        doc=publish(client,make_tour(client))
        for index in range(9):
            assert turn(client,doc,str(index)*1500,f'viewer-bound-{index:03}',viewer=True).status_code==200
        history=calls[-1]['history']
        assert len(history)==12
        assert history[0]=={'role':'user','text':'2'*1000}
        assert all(len(item['text'])<=1000 and set(item)=={'role','text'} for item in history)
        assert client.cookies.get(COOKIE) not in json.dumps(calls[-1])


def test_legacy_request_without_scene_and_cached_pre_extension_input_work(tmp_path):
    calls=[]
    def interpret(context):calls.append(context);return answer()
    with TestClient(app_at(tmp_path,interpret)) as client:
        doc=make_tour(client)
        response=turn(client,doc,'Whole tour question','creator-legacy-001',include_scene=False)
        assert response.status_code==200,response.text
        assert calls[-1]['scene_id'] is None and calls[-1]['current_scene'] is None
        with sqlite3.connect(tmp_path/'tours'/'tours.sqlite') as db:
            row=db.execute('SELECT input FROM turns WHERE draft=?',(doc['id'],)).fetchone()
            old=json.loads(row[0]);old.pop('scene_id')
            db.execute('UPDATE turns SET input=? WHERE draft=?',(json.dumps(old),doc['id']))
        assert turn(client,doc,'Whole tour question','creator-legacy-001',include_scene=False).json()==response.json()
        assert len(calls)==1


def test_viewer_model_edits_never_persist_or_enter_conversation(tmp_path):
    calls=[]
    def interpret(context):
        calls.append(context)
        if context['text']=='Overwrite the tour':
            return answer('Unauthorized proposal',changes=[{'scene_id':context['tour']['scenes'][0]['id'],
                          'name':'Forbidden edit','description':None}])
        return answer('Read-only answer')
    with TestClient(app_at(tmp_path,interpret)) as client:
        draft=make_tour(client);doc=publish(client,draft)
        assert turn(client,doc,'Overwrite the tour','viewer-edit-001',viewer=True).status_code==502
        assert turn(client,doc,'Normal question','viewer-edit-002',viewer=True).status_code==200
        assert calls[-1]['history']==[]
        assert client.get(f'/api/tours/published/{doc["id"]}').json()==doc
        assert client.get(f'/api/tours/drafts/{draft["id"]}').json()==draft
