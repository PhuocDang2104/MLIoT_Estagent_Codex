import base64
import json
import subprocess
import sys
import threading
import time
import httpx
import pytest
from fastapi.testclient import TestClient
from server.creator.runtime import RuntimeLock, DurableQueue
from server.creator.worker import HTTPGeometryWorker, WorkerPending
from tests.ai.creator_fixtures import Provider, Worker
from tests.ai.test_creator import app, draft, post, settled, spatial, COOKIE, HEADERS


class Editor(Provider):
    def __init__(self):
        super().__init__()
        self.plan = {'reply':'Đề xuất đã chuẩn bị.', 'rooms':[], 'scripts':[],
                     'introduction':None, 'order':None, 'connections':None}

    def edit(self, state, text):
        self.calls.append('edit')
        return self.plan


def ready(client):
    pid = draft(client, music=True)
    gid = post(client, f'/projects/{pid}/generations', {'request_id':'start-project'}).json()['id']
    g = settled(client,gid)
    assert post(client,f'/generations/{gid}/review',spatial(g)).status_code == 202
    g = settled(client,gid)
    assert post(client,f'/generations/{gid}/review',{'request_id':'approve-final','kind':'final','decision':'approve'}).status_code == 202
    return pid, settled(client,gid)


def proposal(client, g, request='edit-request'):
    return post(client,f"/generations/{g['id']}/edits",{'text':'Yêu cầu chỉnh sửa fixture.',
        'revision':g['revision'], 'request_id':request})


def apply(client, g, edit, request='apply-request'):
    return post(client,f"/generations/{g['id']}/edits/{edit['id']}/apply",{
        'revision':g['revision'], 'request_id':request})


def test_script_fork_reuses_audio_and_preserves_published_snapshot(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        pid, g = ready(client)
        public = post(client,f"/generations/{g['id']}/publish",{'request_id':'publish-parent'}).json()['id']
        before = client.get('/api/studio-tours/'+public).json()
        provider.plan['scripts'] = [{**g['script']['segments'][0], 'text':'Lời mới đã được Business yêu cầu.'}]
        edit = proposal(client,g).json()
        assert proposal(client,g).json() == edit and provider.calls.count('edit') == 1
        result = apply(client,g,edit)
        assert result.status_code == 202, result.text
        child = settled(client,result.json()['id'])
        assert child['parent_id'] == g['id'] and child['review']['kind'] == 'final'
        assert not child['package'] and child['script']['segments'][0]['text'] == provider.plan['scripts'][0]['text']
        assert provider.calls.count('brief') == 1 and provider.calls.count('observe') == 2 and provider.calls.count('script') == 1
        assert provider.calls.count('speech') == 3
        assert post(client,f"/generations/{child['id']}/publish",{'request_id':'publish-child-early'}).status_code == 409
        assert apply(client,g,edit).json() == result.json()
        assert apply(client,g,edit,'apply-again').status_code == 409
        response = post(client,f"/generations/{child['id']}/review",{
            'kind':'final','decision':'approve','request_id':'approve-child','revision':child['revision']})
        assert response.status_code == 202
        child = settled(client,child['id'])
        assert child['status'] == 'completed' and provider.calls.count('speech') == 4
        assert client.get('/api/studio-tours/'+public).json() == before
        assert len(client.get('/api/studio/projects/'+pid).json()['generations']) == 2


def test_spatial_edit_requires_new_review_and_invalidates_geometry(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        _, g = ready(client)
        provider.plan['rooms'] = [{'checkpoint_id':'cp01','label':None,'summary':None,'yaw':30}]
        edit = proposal(client,g).json()
        assert edit['route'] == 'spatial_review'
        child = settled(client,apply(client,g,edit).json()['id'])
        assert child['review']['kind'] == 'spatial' and child['rooms'][0]['yaw'] == 30
        assert child['model'] is None and not child['package']
        assert provider.calls.count('speech') == 3
        assert post(client,f"/generations/{child['id']}/review",{
            **spatial(child),'request_id':'stale-child-review','revision':999}).status_code == 409


def test_pre_geometry_chat_forks_without_bypassing_worker(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider)) as client:
        pid = draft(client)
        gid = post(client,f'/projects/{pid}/generations',{'request_id':'pre-geometry-start'}).json()['id']
        g = settled(client,gid)
        assert post(client,f'/generations/{gid}/review',spatial(g)).status_code == 202
        g = settled(client,gid)
        assert g['status'] == 'waiting_integration' and g['script'] is None
        provider.plan['rooms'] = [{'checkpoint_id':'cp01','label':'Phòng khách','summary':None,'yaw':None}]
        edit = proposal(client,g).json()
        assert edit['route'] == 'spatial_review'
        child = settled(client,apply(client,g,edit).json()['id'])
        assert child['review']['kind'] == 'spatial' and child['rooms'][0]['label'] == 'Phòng khách'
        assert post(client,f"/generations/{child['id']}/review",{**spatial(child),'request_id':'approve-spatial-child'}).status_code == 202
        assert settled(client,child['id'])['status'] == 'waiting_integration'
        assert provider.calls == ['brief','observe','observe','edit']


def test_navigation_and_semantic_routes_are_selective(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        _, g = ready(client)
        provider.plan['order'] = ['cp02','cp01']
        edit = proposal(client,g).json()
        assert edit['route'] == 'navigation'
        child = settled(client,apply(client,g,edit).json()['id'])
        assert child['rooms'][0]['checkpoint_id'] == 'cp02' and provider.calls.count('script') == 1
        provider.plan['order'] = None
        provider.plan['rooms'] = [{'checkpoint_id':'cp01','label':'Tên Business xác nhận','summary':None,'yaw':None}]
        edit = proposal(client,child,'rename-proposal').json()
        assert edit['route'] == 'semantic'
        grandchild = settled(client,apply(client,child,edit,'rename-apply').json()['id'])
        assert grandchild['review']['kind'] == 'final' and provider.calls.count('script') == 2
        assert provider.calls.count('observe') == 2


def test_untrusted_edits_stale_revision_origin_and_owner(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        _, g = ready(client)
        provider.plan['rooms'] = [{'checkpoint_id':'cp99','label':'Unknown','summary':None,'yaw':None}]
        assert proposal(client,g).status_code == 502
        provider.plan['rooms'] = []
        provider.plan['scripts'] = [{**g['script']['segments'][0], 'sources':['another-private-asset']}]
        assert proposal(client,g,'invalid-evidence').status_code == 502
        provider.plan['scripts'] = []
        provider.plan['order'] = ['cp01','cp01']
        assert proposal(client,g,'invalid-permutation').status_code == 502
        provider.plan['order'] = None
        empty = proposal(client,g,'unsupported-edit').json()
        assert not empty['can_apply'] and apply(client,g,empty).status_code == 422
        provider.plan['introduction'] = 'Mở đầu mới.'
        edit = proposal(client,g,'valid-edit').json()
        assert client.post(f"/api/studio/generations/{g['id']}/edits",json={'request_id':'bad-origin','revision':g['revision'],'text':'x'}).status_code == 403
        assert apply(client,g,edit).status_code == 202
        assert proposal(client,g,'stale-edit').status_code == 409
        client.cookies.clear(); client.get('/api/studio/session')
        assert client.get(f"/api/studio/generations/{g['id']}/edits").status_code == 404
        assert apply(client,g,edit,'foreign-owner').status_code == 404


def test_unchanged_model_fields_cannot_trigger_paid_regeneration(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        _, g = ready(client)
        provider.plan.update(rooms=[{k:g['rooms'][0][k] for k in ('checkpoint_id','label','summary','yaw')}],
            scripts=g['script']['segments'], introduction=g['script']['introduction'],
            order=[r['checkpoint_id'] for r in g['rooms']], connections=g['connections'])
        edit = proposal(client,g).json()
        assert not edit['can_apply'] and apply(client,g,edit).status_code == 422
        assert provider.calls.count('speech') == 3


def test_queued_outbox_survives_without_resubmission(tmp_path, monkeypatch):
    gate = threading.Event()
    original = DurableQueue.loop
    def paused(queue):
        gate.wait(5)
        if not queue.stop.is_set():
            original(queue)
    monkeypatch.setattr(DurableQueue,'loop',paused)
    provider = Editor()
    with TestClient(app(tmp_path,provider)) as client:
        pid = draft(client)
        response = post(client,f'/projects/{pid}/generations',{'request_id':'durable-start'})
        assert response.status_code == 202
        gid = response.json()['id']; cookie = client.cookies.get(COOKIE)
        assert client.get('/api/studio/generations/'+gid).json()['status'] == 'queued'
        assert not provider.calls
        client.app.state.creator.queue.stop.set(); gate.set()
    monkeypatch.setattr(DurableQueue,'loop',original)
    with TestClient(app(tmp_path,provider)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/studio/')
        assert settled(client,gid)['review']['kind'] == 'spatial'
        assert provider.calls == ['brief','observe','observe']
        assert post(client,f'/projects/{pid}/generations',{'request_id':'durable-start'}).json()['id'] == gid
        assert provider.calls.count('brief') == 1


def test_graceful_shutdown_checkpoints_completed_paid_node(tmp_path):
    provider = Editor()
    original = provider.brief
    with TestClient(app(tmp_path,provider)) as client:
        service = client.app.state.creator
        def stop_after_brief(project):
            result = original(project); service.queue.stop.set(); return result
        provider.brief = stop_after_brief
        pid = draft(client)
        gid = post(client,f'/projects/{pid}/generations',{'request_id':'graceful-start'}).json()['id']
        cookie = client.cookies.get(COOKIE)
        service.queue.thread.join(5)
        assert not service.queue.thread.is_alive()
    provider.brief = original
    with TestClient(app(tmp_path,provider)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/studio/')
        assert settled(client,gid)['review']['kind'] == 'spatial'
        assert provider.calls == ['brief','observe','observe']


def test_runtime_lock_is_cross_process(tmp_path):
    lock = RuntimeLock(tmp_path)
    command = [sys.executable,'-c',
        'from pathlib import Path; from server.creator.runtime import RuntimeLock; import sys; RuntimeLock(Path(sys.argv[1]))',str(tmp_path)]
    blocked = subprocess.run(command,capture_output=True,text=True,timeout=10)
    assert blocked.returncode != 0 and 'already has a runtime' in blocked.stderr
    lock.close()
    assert subprocess.run(command,capture_output=True,timeout=10).returncode == 0


def test_async_geometry_submit_once_poll_resume(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider)) as client:
        service = client.app.state.creator
        pid = draft(client)
        assets = service.store.assets(pid)
        rooms = [{'checkpoint_id':'cp01','room_id':'r01'}]
        fixture = Worker().build({},rooms,[],[])
        calls = []
        def transport(request):
            calls.append((request.method,request.url.path))
            if request.method == 'POST':
                payload = json.loads(request.content)
                assert payload['operation_id'] == request.headers['Idempotency-Key']
                assert all(a['content_base64'] for a in payload['assets'])
                return httpx.Response(202,json={'id':'job-1','status':'running'})
            return httpx.Response(200,json={'id':'job-1','status':'completed',
                'glb_base64':base64.b64encode(fixture['glb']).decode(), 'anchors':fixture['anchors']})
        worker = HTTPGeometryWorker({'STUDIO_GEOMETRY_URL':'http://worker.internal'},service.store,httpx.MockTransport(transport))
        project = service.store.project(client.cookies.get(COOKIE),pid)
        with pytest.raises(WorkerPending): worker.build(project,rooms,[],assets)
        result = worker.build(project,rooms,[],assets)
        assert result['glb'] == fixture['glb'] and calls == [('POST','/v1/builds'),('GET','/v1/builds/job-1')]
        assert service.store.write_model(project,result)['anchors'] == fixture['anchors']


def test_geometry_pending_requeues_without_repeating_paid_nodes(tmp_path):
    class AsyncWorker(Worker):
        calls = 0
        def build(self,*args):
            self.calls += 1
            if self.calls == 1:
                raise WorkerPending()
            return super().build(*args)
    worker, provider = AsyncWorker(), Editor()
    with TestClient(app(tmp_path,provider,worker)) as client:
        pid = draft(client)
        gid = post(client,f'/projects/{pid}/generations',{'request_id':'pending-worker-start'}).json()['id']
        g = settled(client,gid)
        assert post(client,f'/generations/{gid}/review',spatial(g)).status_code == 202
        service = client.app.state.creator
        deadline = time.monotonic()+10
        while time.monotonic()<deadline:
            row = service.store.rows('SELECT status,available_at FROM jobs WHERE generation=?',(gid,))[0]
            if worker.calls == 1 and row['status'] == 'queued' and row['available_at'] > 0:
                break
            time.sleep(.01)
        else:
            raise AssertionError('Pending geometry was not durably scheduled')
        assert row['available_at'] > service.queue.clock()
        # Advance only the scheduler clock; no five-second wall-clock sleep.
        future = row['available_at']+1
        service.queue.clock = lambda:future
        service.queue.wake.set()
        g = settled(client,gid)
        assert g['review']['kind'] == 'final' and worker.calls == 2
        assert provider.calls == ['brief','observe','observe','script']


def test_running_crash_requires_explicit_retry(tmp_path,monkeypatch):
    gate = threading.Event()
    original = DurableQueue.loop
    def paused(queue):
        gate.wait(5)
    monkeypatch.setattr(DurableQueue,'loop',paused)
    provider = Editor()
    with TestClient(app(tmp_path,provider)) as client:
        pid = draft(client)
        gid = post(client,f'/projects/{pid}/generations',{'request_id':'crash-start'}).json()['id']
        cookie = client.cookies.get(COOKIE)
        store = client.app.state.creator.store
        store.execute("UPDATE generations SET status='running' WHERE id=?",(gid,))
        store.execute("UPDATE jobs SET status='running' WHERE generation=?",(gid,))
        gate.set()
    monkeypatch.setattr(DurableQueue,'loop',original)
    with TestClient(app(tmp_path,provider)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/studio/')
        assert settled(client,gid)['status'] == 'failed' and not provider.calls
        assert post(client,f'/generations/{gid}/retry',{'request_id':'retry-crashed'}).status_code == 202
        assert settled(client,gid)['review']['kind'] == 'spatial'


def test_immediate_review_cannot_lose_outbox_wakeup(tmp_path):
    provider = Editor()
    returned, release = threading.Event(), threading.Event()
    with TestClient(app(tmp_path,provider,Worker())) as client:
        queue = client.app.state.creator.queue
        original = queue.run
        def hold_after_settled(*args):
            original(*args)
            returned.set(); release.wait(5)
        queue.run = hold_after_settled
        try:
            pid = draft(client)
            gid = post(client,f'/projects/{pid}/generations',{'request_id':'immediate-review-start'}).json()['id']
            assert returned.wait(5)
            g = settled(client,gid)
            assert post(client,f'/generations/{gid}/review',spatial(g)).status_code == 202
            job = client.app.state.creator.store.rows('SELECT status,payload FROM jobs WHERE generation=?',(gid,))[0]
            assert job['status'] == 'queued' and 'resume' in json.loads(job['payload'])
        finally:
            queue.run = original
            release.set()
        assert settled(client,gid)['review']['kind'] == 'final'


def test_crash_after_interrupt_checkpoint_reconciles_metadata(tmp_path):
    provider = Editor()
    with TestClient(app(tmp_path,provider)) as client:
        pid = draft(client)
        gid = post(client,f'/projects/{pid}/generations',{'request_id':'interrupt-crash-start'}).json()['id']
        g = settled(client,gid)
        cookie = client.cookies.get(COOKIE)
        store = client.app.state.creator.store
        store.execute("UPDATE generations SET status='running' WHERE id=?",(gid,))
        store.execute("UPDATE jobs SET status='running' WHERE generation=?",(gid,))
    with TestClient(app(tmp_path,provider)) as client:
        client.cookies.set(COOKIE,cookie,path='/api/studio/')
        recovered = settled(client,gid)
        assert recovered['status'] == 'needs_review' and recovered['revision'] > g['revision']
        assert post(client,f'/generations/{gid}/review',spatial(recovered)).status_code == 202
        assert settled(client,gid)['status'] == 'waiting_integration'
        assert provider.calls == ['brief','observe','observe']


def test_offline_backup_preserves_sqlite_media_and_excludes_previous_backups(tmp_path):
    import sqlite3
    from deploy.backup_data import backup
    root = tmp_path/'data'; root.mkdir()
    with sqlite3.connect(root/'creator.sqlite') as db:
        db.execute('CREATE TABLE records(value TEXT)')
        db.execute('INSERT INTO records VALUES(?)',('synthetic-record',))
    (root/'media').mkdir(); (root/'media'/'fixture.bin').write_bytes(b'synthetic')
    result = backup(root,'fixture')
    manifest = json.loads((result/'BACKUP.json').read_text())
    assert set(manifest['files']) == {'creator.sqlite',str(__import__('pathlib').Path('media/fixture.bin'))}
    with sqlite3.connect(result/'creator.sqlite') as db:
        assert db.execute('SELECT value FROM records').fetchone()[0] == 'synthetic-record'
    assert (root/'media'/'fixture.bin').read_bytes() == b'synthetic'
    second = backup(root,'another')
    assert len(json.loads((second/'BACKUP.json').read_text())['files']) == 2


def test_new_uploads_remove_private_exif_and_apply_orientation(tmp_path):
    import io
    from PIL import Image
    exif = Image.Exif(); exif[315] = 'synthetic-private-owner'; exif[274] = 6
    image = io.BytesIO()
    Image.new('RGB',(128,64),'blue').save(image,format='JPEG',exif=exif)
    with TestClient(app(tmp_path)) as client:
        pid = draft(client)
        response = client.post(f'/api/studio/projects/{pid}/assets?name=metadata.jpg',content=image.getvalue(),headers=HEADERS)
        assert response.status_code == 201,response.text
        asset = response.json()
        assert (asset['width'],asset['height']) == (64,128) and asset['projection'] == 'photo'
        data = client.get(f"/api/studio/projects/{pid}/assets/{asset['id']}").content
        assert b'synthetic-private-owner' not in data
        with Image.open(io.BytesIO(data)) as clean:
            assert not clean.getexif() and clean.size == (64,128)
