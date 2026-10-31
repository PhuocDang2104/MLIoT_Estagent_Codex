"""HTTP/LangGraph/SQLite + actual MinIO adapter against an in-memory SDK fixture."""
import importlib
import json
import sqlite3
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest

from server.object_storage import MinioStorage
from tests.ai.test_object_storage import Client, s3error
from tests.ai.creator_fixtures import Provider, Worker, png, wav
from tests.ai.test_creator import draft as studio_draft, post, settled, spatial

HEADERS={'Origin':'http://testserver'}
PROVENANCE={'source_label':'Synthetic tone','rights':'owned','rights_note':'Generated fixture, no actual music.'}


@pytest.fixture
def sdk(monkeypatch):
    client=Client()
    adapter=MinioStorage(client,'private-fixture-bucket')
    module=importlib.import_module('server.assistant.app')
    monkeypatch.setattr(module,'create_object_storage',lambda env:adapter if env.get('MEDIA_STORAGE_BACKEND')=='minio' else None)
    return client


def app(root,backend='minio',provider=None,worker=None):
    module=importlib.import_module('server.assistant.app')
    return module.create_app(db_path=root/'assistant.sqlite',env={
        'ASSISTANT_ORIGIN':'http://testserver','MEDIA_STORAGE_BACKEND':backend,
        'STORAGE_LIMITS_ENABLED':'1','STORAGE_LIMITS_ROOT':str(root),
        'STORAGE_LIMITS_MAX_BYTES':str(32*1024*1024),'STORAGE_LIMITS_MIN_FREE_BYTES':'1'},
        creator_provider=provider,creator_worker=worker)


def image(client,variant=0):
    return client.post('/api/tours/assets',headers=HEADERS,content=png(variant))


def audio(client,provenance=None):
    return client.post('/api/tours/audio-assets',headers=HEADERS|{
        'X-Audio-Metadata':quote(json.dumps(provenance or PROVENANCE))},content=wav())


def legacy_draft(client,asset):
    response=client.post('/api/tours/drafts',headers=HEADERS,json={
        'asset_ids':[asset['id']],'locale':'en','request_id':'minio-draft-fixture'})
    assert response.status_code==200,response.text
    return response.json()


def test_tour_media_remote_only_publish_uses_stat_ranges_and_restart(tmp_path,sdk):
    with TestClient(app(tmp_path)) as client:
        client.get('/api/tours/session')
        im=image(client).json();track=audio(client).json()
        assert image(client).json()==im and audio(client).json()==track
        assert len(sdk.objects)==3 and sdk.puts==3
        assert not list(tmp_path.rglob('*.jpg')) and not list(tmp_path.rglob('*.wav'))
        doc=legacy_draft(client,im)
        response=client.put(f'/api/tours/drafts/{doc["id"]}/audio',headers=HEADERS,json={
            'revision':doc['revision'],'music_asset_id':track['asset_id'],'narration':[]})
        assert response.status_code==200,response.text
        doc=response.json()
        assert sdk.responses==[]  # Attach verification must not create unconsumed streams.
        assert client.post(f'/api/tours/drafts/{doc["id"]}/review',headers=HEADERS,json={'revision':doc['revision']}).status_code==200
        response=client.post(f'/api/tours/drafts/{doc["id"]}/publish',headers=HEADERS,json={'revision':doc['revision']})
        assert response.status_code==200,response.text
        published=response.json()
        assert sdk.responses==[]  # Publish uses stat, not a response/get stream.
        assert 'minio' not in json.dumps(published) and 'tours/images/' not in json.dumps(published)
        client.cookies.clear()
        assert client.get(im['image_url']).status_code==401
        client.get('/api/tours/session')
        assert client.get(im['image_url']).status_code==404
        assert client.get(track['url']).status_code==404
        assert client.get(published['scenes'][0]['image_url']).status_code==200
        assert client.get(published['scenes'][0]['thumbnail_url']).status_code==200
        url=published['audio']['music']['url']
        response=client.get(url,headers={'Range':'bytes=0-43'})
        assert response.status_code==206 and len(response.content)==44
        assert response.headers['Content-Range'].startswith('bytes 0-43/')
        assert client.get(url,headers={'Range':'bytes=999999-'}).status_code==416
        assert client.get(f'/api/tours/published/{published["id"]}/audio/'+('f'*32)).status_code==404
        assert all(source.closes==source.releases==1 for source in sdk.responses)
    with TestClient(app(tmp_path)) as client:
        assert client.get(url).content==wav()
        sdk.failure=s3error('AccessDenied')
        assert client.get(url).status_code==503
        assert client.get(published['scenes'][0]['image_url']).status_code==503
        sdk.failure=None
        assert client.get(url).status_code==200


def test_explicit_legacy_file_and_blob_fallback_only_for_unmarked_assets(tmp_path,sdk):
    with TestClient(app(tmp_path,'local')) as client:
        client.get('/api/tours/session');im=image(client).json();track=audio(client).json()
        legacy_cookie=client.cookies.get('estagent_tours')
        pid=studio_draft(client)
        studio_cookie=client.cookies.get('estagent_studio')
        old_studio=client.get('/api/studio/projects/'+pid).json()['assets'][0]
        assert list(tmp_path.rglob('*.jpg')) and list(tmp_path.rglob('*.wav'))
    with TestClient(app(tmp_path)) as client:
        client.cookies.set('estagent_tours',legacy_cookie,path='/api/tours/')
        client.cookies.set('estagent_studio',studio_cookie,path='/api/studio/')
        assert client.get(im['image_url']).status_code==200
        assert client.get(track['url'],headers={'Range':'bytes=0-43'}).status_code==206
        assert client.get(f'/api/studio/projects/{pid}/assets/{old_studio["id"]}').content==png()
        new_image=image(client,3).json()
        assert len(sdk.objects)==2
    # A registered remote object never falls back, even if a coincident local file exists.
    (tmp_path/'tours'/'assets'/f'{new_image["id"]}.jpg').write_bytes(b'wrong-local-copy')
    with TestClient(app(tmp_path,'local')) as client:
        client.cookies.set('estagent_tours',legacy_cookie,path='/api/tours/')
        assert client.get(im['image_url']).status_code==200
        assert client.get(new_image['image_url']).status_code==503


def test_studio_images_music_tts_glb_remote_and_public_membership(tmp_path,sdk):
    with TestClient(app(tmp_path,provider=Provider(),worker=Worker())) as client:
        pid=studio_draft(client,music=True)
        cookie=client.cookies.get('estagent_studio')
        gid=post(client,f'/projects/{pid}/generations',{'request_id':'start-minio-project'}).json()['id']
        generation=settled(client,gid)
        assert post(client,f'/generations/{gid}/review',spatial(generation)).status_code==202
        assert settled(client,gid)['review']['kind']=='final'
        assert post(client,f'/generations/{gid}/review',{'kind':'final','decision':'approve','request_id':'approve-minio-final'}).status_code==202
        generation=settled(client,gid)
        assert generation['status']=='completed',generation
        store=client.app.state.creator.store
        assets=store.assets(pid)
        assert {'panorama','music','narration','model'} <= {a['kind'] for a in assets}
        assert len(store.rows('SELECT * FROM media_refs'))==len(assets)
        assert all(row['size']==0 for row in store.rows('SELECT length(content) AS size FROM assets'))
        assert all(key.startswith('studio/assets/') for key in sdk.objects)
        assert all(source.closes==source.releases==1 for source in sdk.responses)
        reads=len(sdk.responses)
        # A missing approved object prevents publish; no local/BLOB fallback exists.
        missing_key=store.object_key(assets[0]['id']);missing=sdk.objects.pop(missing_key)
        denied=post(client,f'/generations/{gid}/publish',{'request_id':'publish-missing-minio'})
        assert denied.status_code==404 and store.rows('SELECT id FROM published')==[]
        assert len(sdk.responses)==reads
        sdk.objects[missing_key]=missing
        response=post(client,f'/generations/{gid}/publish',{'request_id':'publish-minio-ready'})
        assert response.status_code==200,response.text
        public=response.json()['id']
        assert len(sdk.responses)==reads
        package=client.get('/api/studio-tours/'+public).json()
        client.cookies.clear()
        assert client.get('/api/studio/projects/'+pid).status_code==401
        client.get('/api/studio/session')
        assert client.get('/api/studio/projects/'+pid).status_code==404
        for asset in package['assets']:
            response=client.get(f'/api/studio-tours/{public}/assets/{asset["id"]}',headers={'Range':'bytes=0-7'})
            assert response.status_code==206 and len(response.content)==8
        assert client.get(f'/api/studio-tours/{public}/assets/'+('f'*32)).status_code==404
        assert all(source.closes==source.releases==1 for source in sdk.responses)
    with TestClient(app(tmp_path)) as client:
        assert client.get('/api/studio-tours/'+public).json()==package
        for asset in package['assets']:
            assert client.get(f'/api/studio-tours/{public}/assets/{asset["id"]}').status_code==200


@pytest.mark.parametrize('family',['image','audio','studio'])
def test_db_registration_failure_removes_only_new_remote_objects(tmp_path,sdk,family):
    with TestClient(app(tmp_path)) as client:
        client.get('/api/tours/session')
        baseline=image(client).json()
        saved=dict(sdk.objects)
        if family=='studio':
            pid=studio_draft(client);saved=dict(sdk.objects)
            db=client.app.state.creator.store.db
            db.execute("CREATE TRIGGER reject_reference BEFORE INSERT ON media_refs BEGIN SELECT RAISE(ABORT,'synthetic registration failure'); END")
            db.commit()
            response=client.post(f'/api/studio/projects/{pid}/assets',content=png(4),headers=HEADERS)
        else:
            with sqlite3.connect(tmp_path/'tours'/'tours.sqlite') as db:
                if family=='audio':db.execute('CREATE TABLE IF NOT EXISTS audio_assets(id TEXT PRIMARY KEY,owner TEXT NOT NULL,digest TEXT NOT NULL,metadata TEXT NOT NULL,UNIQUE(owner,digest))')
                table='assets' if family=='image' else 'audio_assets'
                db.execute(f"CREATE TRIGGER reject_asset BEFORE INSERT ON {table} BEGIN SELECT RAISE(ABORT,'synthetic registration failure'); END")
            response=image(client,4) if family=='image' else audio(client)
        assert response.status_code==507,response.text
        assert sdk.objects==saved
        assert client.get(baseline['image_url']).status_code==200


def test_second_image_object_failure_cleans_first_and_preserves_db(tmp_path,sdk,monkeypatch):
    original=sdk.put_object
    def fail_thumbnail(bucket,key,*args,**kwargs):
        if '/thumbnails/' in key:raise s3error('AccessDenied')
        return original(bucket,key,*args,**kwargs)
    monkeypatch.setattr(sdk,'put_object',fail_thumbnail)
    with TestClient(app(tmp_path)) as client:
        client.get('/api/tours/session')
        response=image(client)
        assert response.status_code==503 and sdk.objects=={}
        with sqlite3.connect(tmp_path/'tours'/'tours.sqlite') as db:
            assert db.execute('SELECT count(*) FROM assets').fetchone()[0]==0
            assert db.execute('SELECT count(*) FROM media_storage').fetchone()[0]==0
        assert not list(tmp_path.rglob('*.jpg'))
