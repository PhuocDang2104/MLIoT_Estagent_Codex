"""Global storage limits with real local API/SQLite/files, synthetic media only."""
import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
from urllib.parse import quote
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from server.assistant.app import create_app
from server.storage import UploadStorage, validate_storage
from tests.ai.creator_fixtures import png, wav

HEADERS={'Origin':'http://testserver'}
PROVENANCE={'source_label':'Synthetic test','rights':'owned','rights_note':'Test generated tone.'}


def config(root):
    return {'ASSISTANT_ORIGIN':'http://testserver', 'ASSISTANT_DB':str(root/'assistant.sqlite'),
        'STORAGE_LIMITS_ENABLED':'1','STORAGE_LIMITS_ROOT':str(root),
        'STORAGE_LIMITS_MAX_BYTES':str(16*1024*1024),'STORAGE_LIMITS_MIN_FREE_BYTES':'1'}


def factory(root, env=None):
    return create_app(db_path=root/'assistant.sqlite',env=config(root) if env is None else env)


def studio_project(client, request_id='storage-project'):
    client.get('/api/studio/session')
    response=client.post('/api/studio/projects',headers=HEADERS,json={
        'name':'Storage fixture','description':'Synthetic input','request_id':request_id})
    assert response.status_code==201,response.text
    return response.json()['id']


def upload(client, kind, project=None, variant=0):
    if kind=='image':return client.post('/api/tours/assets',content=png(variant),headers=HEADERS)
    if kind=='wav':return client.post('/api/tours/audio-assets',content=wav(),headers=HEADERS|{
        'X-Audio-Metadata':quote(json.dumps(PROVENANCE))})
    suffix='?kind=music&credit=Test-owned-tone' if kind=='studio-music' else ''
    return client.post(f'/api/studio/projects/{project}/assets'+suffix,
        content=wav() if kind=='studio-music' else png(variant),headers=HEADERS)


@pytest.mark.parametrize('kind',['image','wav','studio-image','studio-music'])
def test_all_uploads_reject_full_storage_and_replay_keeps_existing_asset(tmp_path,kind):
    app=factory(tmp_path)
    with TestClient(app) as client:
        client.get('/api/tours/session')
        project=studio_project(client)
        first=upload(client,kind,project)
        assert first.status_code in (200,201),first.text
        original=first.json()
        # Tightened operator cap below current total: no new payload is admissible.
        app.state.storage_limits.max_bytes=1
        repeat=upload(client,kind,project)
        assert repeat.status_code in (200,201) and repeat.json()==original
        if kind=='image':url=original['image_url']
        elif kind=='wav':url=original['url']
        else:url=f'/api/studio/projects/{project}/assets/{original["id"]}'
        assert client.get(url).status_code==200
        client.cookies.clear()  # A fresh cookie/project cannot reset global capacity.
        client.get('/api/tours/session')
        second_project=studio_project(client,'second-storage-project')
        denied=upload(client,kind,second_project,variant=1)
        assert denied.status_code==507,denied.text
        assert str(tmp_path) not in denied.text
        if kind.startswith('studio'):
            assert client.get('/api/studio/projects/'+second_project).json()['assets']==[]


def test_restart_scans_existing_files_wal_and_backups_and_keeps_published_tour(tmp_path):
    app=factory(tmp_path)
    with TestClient(app) as client:
        client.get('/api/tours/session')
        image=upload(client,'image').json()
        doc=client.post('/api/tours/drafts',headers=HEADERS,json={
            'asset_ids':[image['id']],'locale':'en','request_id':'storage-published'}).json()
        assert client.post(f'/api/tours/drafts/{doc["id"]}/review',headers=HEADERS,json={'revision':doc['revision']}).status_code==200
        published=client.post(f'/api/tours/drafts/{doc["id"]}/publish',headers=HEADERS,json={'revision':doc['revision']}).json()
        (tmp_path/'release-backups').mkdir()
        (tmp_path/'release-backups'/'backup.sqlite-wal').write_bytes(b'X'*8192)
        assert app.state.storage_limits.usage()==sum(p.stat().st_size for p in tmp_path.rglob('*') if p.is_file())
    env=config(tmp_path)|{'STORAGE_LIMITS_MAX_BYTES':'1'}
    with TestClient(factory(tmp_path,env)) as client:
        client.get('/api/tours/session')
        assert upload(client,'image',variant=1).status_code==507
        assert client.get('/api/tours/published/'+published['id']).json()==published
        assert client.get(published['scenes'][0]['image_url']).status_code==200


def test_headroom_and_storage_errors_fail_closed_then_release(tmp_path,monkeypatch):
    import server.storage as storage
    guard=UploadStorage(tmp_path,10**7,1024)
    original=storage.shutil.disk_usage
    monkeypatch.setattr(storage.shutil,'disk_usage',lambda root:type('Usage',(),{'free':1024})())
    with pytest.raises(HTTPException) as error:
        with guard.reserve(100):pytest.fail('Must not admit payload')
    assert error.value.status_code==507
    monkeypatch.setattr(storage.shutil,'disk_usage',original)
    with pytest.raises(RuntimeError):
        with guard.reserve(100):raise RuntimeError('simulated writer failure')
    with guard.reserve(100):pass
    link = tmp_path/'link'
    if __import__('os').name == 'nt':
        # Windows symlink creation needs a privilege unavailable to normal CI.
        # Exercise the guard with the same filesystem flag; POSIX uses a real link.
        link.touch()
        original_symlink = Path.is_symlink
        monkeypatch.setattr(Path,'is_symlink',lambda path: path == link or original_symlink(path))
    else:
        link.symlink_to(tmp_path/'outside')
    with pytest.raises(HTTPException) as error:
        with guard.reserve(100):pytest.fail('Must fail closed')
    assert error.value.status_code==507


def test_shared_process_reservation_serializes_measurement_and_write(tmp_path):
    first=UploadStorage(tmp_path,100000,1)
    second=UploadStorage(tmp_path,100000,1)
    attempting=threading.Event()
    def contender():
        attempting.set()
        try:
            with second.reserve(100):return 'admitted'
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=1) as pool:
        with first.reserve(100):
            future=pool.submit(contender)
            assert attempting.wait(2)
            with pytest.raises(TimeoutError):future.result(timeout=.05)
            (tmp_path/'new-payload').write_bytes(b'x'*40000)
        # Capacity changed while contender waited. It must remeasure after release.
        assert future.result(timeout=2)==507


def test_actual_image_write_error_cleans_payload_and_retry_succeeds(tmp_path,monkeypatch):
    app=factory(tmp_path)
    original=Path.open
    fail=[True]
    def write_error(path,*args,**kwargs):
        if path.suffix=='.jpg' and args and args[0]=='xb' and fail[0]:
            fail[0]=False
            raise OSError('simulated full disk')
        return original(path,*args,**kwargs)
    with TestClient(app) as client:
        client.get('/api/tours/session')
        monkeypatch.setattr(Path,'open',write_error)
        response=upload(client,'image')
        assert response.status_code==507 and 'simulated full disk' not in response.text
        assert not list((tmp_path/'tours'/'assets').glob('*.jpg'))
        response=upload(client,'image')
        assert response.status_code==200,response.text
        assert client.get(response.json()['image_url']).status_code==200


def test_image_admission_measures_encoded_texture_and_thumbnail_not_compressed_input(tmp_path):
    app=factory(tmp_path)
    with TestClient(app) as client:
        client.get('/api/tours/session')
        # Solid PNG is much smaller than the resulting JPEG texture + thumbnail.
        # A capacity check against raw request length would incorrectly admit it.
        guard=app.state.storage_limits
        guard.max_bytes=guard.usage()+65536+3*len(png())+1
        response=upload(client,'image')
        assert response.status_code==507,response.text
        assert not list((tmp_path/'tours'/'assets').glob('*.jpg'))


@pytest.mark.parametrize('name,value',[
    ('STORAGE_LIMITS_ENABLED','true'),('STORAGE_LIMITS_ROOT','relative'),
    ('STORAGE_LIMITS_MAX_BYTES','0'),('STORAGE_LIMITS_MIN_FREE_BYTES','-1'),
])
def test_invalid_config_rejected(tmp_path,name,value):
    with pytest.raises(ValueError):validate_storage(config(tmp_path)|{name:value})


def test_root_must_cover_all_storage_and_keyless_default_stays_compatible(tmp_path):
    assert validate_storage({}) is None
    with pytest.raises(ValueError,match='contain all'):
        validate_storage(config(tmp_path)|{'STUDIO_DATA_DIR':str(tmp_path.parent/'outside')})
