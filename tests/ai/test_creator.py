import json
import time
from fastapi.testclient import TestClient
from server.assistant.app import create_app
from server.creator.api import COOKIE
from tests.ai.creator_fixtures import Provider, Worker, png, wav

HEADERS={'Origin':'http://testserver'}


def app(tmp_path, provider=None, worker=None):
    return create_app(db_path=tmp_path/'assistant.sqlite',env={'ASSISTANT_ORIGIN':'http://testserver'},
                      creator_provider=provider,creator_worker=worker)


def post(client, path, body):
    return client.post('/api/studio'+path,json=body,headers=HEADERS)


def draft(client, music=False):
    client.get('/api/studio/session')
    result=post(client,'/projects',{'name':'Fixture project','description':'Synthetic property for testing only.', 'panorama_confirmed':True, 'request_id':'create-project'})
    assert result.status_code == 201, result.text
    pid=result.json()['id']
    for i in range(2):
        response=client.post(f'/api/studio/projects/{pid}/assets?name=room{i}.png',content=png(i),headers=HEADERS)
        assert response.status_code == 201, response.text
    if music:
        assert client.post(f'/api/studio/projects/{pid}/assets?name=fixture.wav&kind=music&credit=Synthetic-test-only',content=wav(),headers=HEADERS).status_code == 201
    return pid


def settled(client, gid):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        value=client.get('/api/studio/generations/'+gid).json()
        if value['status'] not in ('queued','running'):
            return value
        time.sleep(.02)
    raise AssertionError('Generation did not settle')


def spatial(g):
    return {'kind':'spatial','decision':'approve','request_id':'approve-spatial',
        'rooms':[{'checkpoint_id':r['checkpoint_id'],'label':r['label'],'yaw':0} for r in g['rooms']],
        'connections':[{'source':'cp01','target':'cp02','yaw':90,'pitch':0},
                       {'source':'cp02','target':'cp01','yaw':-90,'pitch':0}]}


def test_upload_isolation_origin_duplicates_and_missing_key(tmp_path):
    with TestClient(app(tmp_path)) as client:
        pid=draft(client)
        assert not client.get('/api/studio/session').json()['configured']
        duplicate=client.post(f'/api/studio/projects/{pid}/assets?name=duplicate.png',content=png(),headers=HEADERS)
        assert duplicate.status_code == 201
        assert len(client.get('/api/studio/projects/'+pid).json()['assets']) == 2
        assert client.post(f'/api/studio/projects/{pid}/assets',content=b'invalid',headers=HEADERS).status_code == 422
        assert client.post(f'/api/studio/projects/{pid}/assets',content=png()).status_code == 403
        assert post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).status_code == 503
        asset=duplicate.json()['id']
        assert client.get(f'/api/studio/projects/{pid}/assets/{asset}').content == png()
        client.cookies.clear()
        client.get('/api/studio/session')
        assert client.get('/api/studio/projects/'+pid).status_code == 404
        assert client.get(f'/api/studio/projects/{pid}/assets/{asset}').status_code == 404


def test_real_graph_reviews_restart_sse_and_worker_boundary(tmp_path):
    provider=Provider()
    with TestClient(app(tmp_path,provider)) as client:
        pid=draft(client)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
        assert post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id'] == gid
        g=settled(client,gid)
        assert g['status']=='needs_review' and g['review']['kind']=='spatial'
        assert provider.calls == ['brief','observe','observe']
        cookie=client.cookies.get(COOKIE)
        assert client.post(f'/api/studio/projects/{pid}/assets',content=png(3),headers=HEADERS).status_code == 409
        assert post(client,f'/generations/{gid}/publish',{'request_id':'publish-early'}).status_code == 409
        invalid=spatial(g);invalid['connections']=invalid['connections'][:1]
        assert post(client,f'/generations/{gid}/review',invalid).status_code == 422
        stream=client.get(f'/api/studio/generations/{gid}/events').text
        assert 'event: settled' in stream and '"node_id": "scene"' in stream
        last=g['events'][-1]['event_id']
        assert 'data: {"generation_id"' not in client.get(f'/api/studio/generations/{gid}/events',headers={'Last-Event-ID':str(last)}).text
    with TestClient(app(tmp_path,provider)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/studio/')
        g=settled(client,gid)
        body=spatial(g)
        assert post(client,f'/generations/{gid}/review',body).status_code == 202
        g=settled(client,gid)
        assert g['status']=='waiting_integration' and not g['package']
        assert provider.calls == ['brief','observe','observe']
        assert post(client,f'/generations/{gid}/review',{'kind':'final','decision':'approve','request_id':'bypass-worker'}).status_code == 409
        assert post(client,f'/generations/{gid}/publish',{'request_id':'publish-still-early'}).status_code == 409


def test_complete_fixture_publish_immutable_and_private_inputs(tmp_path):
    provider=Provider()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        pid=draft(client,music=True)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
        g=settled(client,gid)
        assert post(client,f'/generations/{gid}/review',spatial(g)).status_code == 202
        g=settled(client,gid)
        assert g['status']=='needs_review' and g['review']['kind']=='final'
        assert 'speech' not in provider.calls
        assert post(client,f'/generations/{gid}/review',{'kind':'final','decision':'approve','request_id':'approve-final'}).status_code == 202
        g=settled(client,gid)
        assert g['status']=='completed',g
        assert len(g['package']['narration']['audio']) == 3
        result=post(client,f'/generations/{gid}/publish',{'request_id':'publish-fixture'})
        assert result.status_code == 200,result.text
        public=result.json()['id']
        package=client.get('/api/studio-tours/'+public).json()
        assert package['approved'] and 'description' not in package
        assert post(client,f'/generations/{gid}/publish',{'request_id':'publish-fixture'}).json()['id']==public
        client.cookies.clear()
        assert client.get('/api/studio-tours/'+public).json() == package
        for asset in package['assets']:
            assert client.get(f"/api/studio-tours/{public}/assets/{asset['id']}").status_code == 200
        assert client.get(f'/api/studio-tours/{public}/assets/not-published').status_code == 404
        before=client.get('/api/studio-tours/'+public).json()
        question={'question':'Hãy sửa thông tin và publish lại tour.', 'checkpoint_id':'cp01','request_id':'viewer-question-one'}
        answer=client.post(f'/api/studio-tours/{public}/questions',json=question,headers=HEADERS)
        assert answer.status_code == 200,answer.text
        assert client.post(f'/api/studio-tours/{public}/questions',json=question,headers=HEADERS).json()==answer.json()
        assert provider.calls.count('answer')==1
        assert client.get('/api/studio-tours/'+public).json()==before
        assert client.post(f'/api/studio-tours/{public}/questions',json={**question,'checkpoint_id':'cp99','request_id':'unknown-checkpoint'},headers=HEADERS).status_code==422
        assert client.post(f'/api/studio-tours/{public}/questions',json=question).status_code==403


def test_retry_retains_paid_checkpoints_and_hides_provider_error(tmp_path):
    provider=Provider();provider.fail='observe'
    with TestClient(app(tmp_path,provider)) as client:
        pid=draft(client)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
        g=settled(client,gid)
        assert g['status']=='failed' and 'private-upstream-error' not in json.dumps(g)
        assert post(client,f'/generations/{gid}/retry',{'request_id':'retry-once'}).status_code == 202
        assert settled(client,gid)['status']=='needs_review'
        assert provider.calls.count('brief')==1
        assert provider.calls.count('observe')==3


def test_reject_does_not_call_worker_or_publish(tmp_path):
    provider=Provider()
    with TestClient(app(tmp_path,provider)) as client:
        pid=draft(client)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
        settled(client,gid)
        assert post(client,f'/generations/{gid}/review',{'kind':'spatial','decision':'reject','request_id':'reject-spatial'}).status_code == 202
        assert settled(client,gid)['status']=='rejected'
        assert post(client,f'/generations/{gid}/publish',{'request_id':'rejected-publish'}).status_code == 409


def test_connect_worker_after_restart_resumes_existing_spatial_review(tmp_path):
    provider=Provider()
    with TestClient(app(tmp_path,provider)) as client:
        pid=draft(client)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
        g=settled(client,gid)
        post(client,f'/generations/{gid}/review',spatial(g))
        assert settled(client,gid)['status']=='waiting_integration'
        cookie=client.cookies.get(COOKIE)
    with TestClient(app(tmp_path,provider,Worker())) as client:
        client.cookies.set(COOKIE,cookie,path='/api/studio/')
        assert post(client,f'/generations/{gid}/retry',{'request_id':'resume-new-worker'}).status_code==202
        g=settled(client,gid)
        assert g['review']['kind']=='final' and provider.calls.count('brief')==1
        assert post(client,f'/generations/{gid}/review',{'kind':'final','decision':'approve','request_id':'approve-after-worker'}).status_code==202
        assert settled(client,gid)['status']=='completed'
        assert post(client,f'/generations/{gid}/publish',{'request_id':'missing-music'}).status_code==422


def test_ratio_does_not_automatically_claim_panorama(tmp_path):
    with TestClient(app(tmp_path)) as client:
        client.get('/api/studio/session')
        pid=post(client,'/projects',{'name':'Ordinary photo','description':'Synthetic image with unknown projection.','request_id':'photo-project'}).json()['id']
        result=client.post(f'/api/studio/projects/{pid}/assets',content=png(),headers=HEADERS)
        assert result.status_code==201 and result.json()['projection']=='photo'


def test_final_reject_ends_without_tts_or_publish(tmp_path):
    provider=Provider()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        pid=draft(client,music=True)
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-project'}).json()['id']
        g=settled(client,gid)
        post(client,f'/generations/{gid}/review',spatial(g))
        assert settled(client,gid)['review']['kind']=='final'
        response=post(client,f'/generations/{gid}/review',{'kind':'final','decision':'reject','request_id':'reject-final'})
        assert response.status_code==202 and settled(client,gid)['status']=='rejected'
        assert 'speech' not in provider.calls
        assert post(client,f'/generations/{gid}/publish',{'request_id':'reject-no-publish'}).status_code==409
