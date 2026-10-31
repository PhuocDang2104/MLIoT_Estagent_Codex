"""Actual ASGI requests + temporary SQLite. No credentials/provider calls or sleeps."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient
import httpx
import pytest

from server.assistant.app import create_app
from server.assistant.graph import Extraction, LABELS
from server.limits import install_limits


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


def config(tmp_path, **overrides):
    return {
        'API_LIMITS_ENABLED': '1', 'API_LIMITS_DB': str(tmp_path / 'limits.sqlite'),
        'API_LIMITS_AI_REQUESTS': '3', 'API_LIMITS_AI_WINDOW_SECONDS': '60',
        'API_LIMITS_AI_CONCURRENCY': '1', 'API_LIMITS_AI_ATTEMPTS': '5',
        'API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS': '300', **overrides,
    }


def stub(tmp_path, clock=None, endpoint=None, **overrides):
    app = FastAPI()
    calls = []

    async def default(request: Request):
        calls.append(True)
        return {'fixture': True}

    handler = endpoint or default
    for route in ['/api/assistant/turn', '/api/assistant/voice',
                  '/api/tours/drafts/{id}/chat', '/api/tours/published/{id}/chat',
                  '/api/tours/assets', '/api/tours/audio-assets',
                  '/api/studio/projects/{id}/assets',
                  '/api/studio/projects/{id}/generations',
                  '/api/studio/generations/{id}/review',
                  '/api/studio/generations/{id}/retry',
                  '/api/studio/generations/{id}/edits',
                  '/api/studio/generations/{id}/edits/{edit_id}/apply',
                  '/api/studio-tours/{id}/questions']:
        app.add_api_route(route, handler, methods=['POST'])
    app.add_api_route('/api/assistant/state', default, methods=['GET'])
    install_limits(app, config(tmp_path, **overrides), clock=clock or Clock())
    return app, calls


def test_burst_is_global_across_routes_headers_cookies_and_slashes(tmp_path):
    app, calls = stub(tmp_path)
    with TestClient(app) as client:
        for route in ['/api/assistant/turn', '/api/tours/drafts/a/chat', '/api/tours/published/b/chat']:
            assert client.post(route).status_code == 200
        for route in ['/api/assistant/voice', '/api/assistant/turn/']:
            response = client.post(route, headers={'X-Forwarded-For': '198.51.100.2',
                                  'X-Real-IP': '203.0.113.7', 'Cookie': 'new_identity=1'})
            assert response.status_code == 429
            assert response.json()['code'] == 'rate_limited'
            assert response.headers['Retry-After'] == '60'
            assert response.headers['Cache-Control'] == 'no-store'
        assert len(calls) == 3  # Rejected requests never reach the endpoint.
        assert client.get('/api/assistant/state').status_code == 200
        assert client.post('/api/tours/assets').status_code == 200  # Separate upload bucket.


def test_allowance_survives_app_recreation_and_expires_at_boundary(tmp_path):
    clock = Clock()
    overrides = {'API_LIMITS_AI_REQUESTS': '1', 'API_LIMITS_AI_ATTEMPTS': '2'}
    app, _ = stub(tmp_path, clock, **overrides)
    with TestClient(app) as client:
        assert client.post('/api/assistant/turn').status_code == 200
    clock.now += 60
    app, _ = stub(tmp_path, clock, **overrides)
    with TestClient(app) as client:
        assert client.post('/api/assistant/voice').status_code == 200
    clock.now += 60
    app, calls = stub(tmp_path, clock, **overrides)
    with TestClient(app) as client:
        response = client.post('/api/assistant/turn')
        assert response.status_code == 429 and not calls
        assert response.json()['code'] == 'attempt_allowance_exhausted'
        assert response.headers['Retry-After'] == '180'
        clock.now = 1299.9
        assert client.post('/api/assistant/turn').headers['Retry-After'] == '1'
        clock.now = 1300
        assert client.post('/api/assistant/turn').status_code == 200
        assert len(calls) == 1


def test_clock_backwards_does_not_reopen_window_and_rejections_do_not_extend_it(tmp_path):
    clock = Clock()
    app, calls = stub(tmp_path, clock, API_LIMITS_AI_REQUESTS='1')
    with TestClient(app) as client:
        assert client.post('/api/assistant/turn').status_code == 200
        clock.now = 1005
        assert client.post('/api/assistant/turn').headers['Retry-After'] == '55'
        clock.now = 900
        assert client.post('/api/assistant/turn').headers['Retry-After'] == '55'
        clock.now = 1060
        assert client.post('/api/assistant/turn').status_code == 200
        assert len(calls) == 2


@pytest.mark.parametrize('route,other', [
    ('/api/assistant/turn', '/api/assistant/voice'),
    ('/api/tours/assets', '/api/tours/assets'),
])
def test_concurrent_work_is_bounded_and_slot_released_on_success(tmp_path, route, other):
    entered, release = threading.Event(), threading.Event()

    def endpoint():
        entered.set()
        assert release.wait(5), 'Fixture release signal missing'
        return {'fixture': True}

    app, _ = stub(tmp_path, endpoint=endpoint)
    with TestClient(app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.post, route)
        try:
            assert entered.wait(5)
            response = client.post(other)
            assert response.status_code == 429
            assert response.json()['code'] == 'concurrency_limited'
            assert response.headers['Retry-After'] == '1'
        finally:
            release.set()
        assert future.result(5).status_code == 200
        assert client.post(route).status_code == 200


def test_stream_holds_slot_until_body_completion_and_cancel_releases(tmp_path):
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()

        async def body():
            entered.set()
            yield b'fixture-first-chunk'
            await release.wait()
            yield b'fixture-last-chunk'

        async def endpoint():
            return StreamingResponse(body())

        app, _ = stub(tmp_path, endpoint=endpoint, API_LIMITS_AI_ATTEMPTS='2')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://local') as client:
            first = asyncio.create_task(client.post('/api/assistant/turn'))
            try:
                await asyncio.wait_for(entered.wait(), 5)
                blocked = await client.post('/api/assistant/voice')
                assert blocked.status_code == 429 and blocked.json()['code'] == 'concurrency_limited'
            finally:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
                release.set()
            assert (await client.post('/api/assistant/turn')).status_code == 200
            assert (await client.post('/api/assistant/turn')).json()['code'] == 'attempt_allowance_exhausted'
    asyncio.run(exercise())


def test_exception_releases_concurrency_but_attempt_is_not_refunded(tmp_path):
    calls = []

    def endpoint():
        calls.append(True)
        raise RuntimeError('fixture endpoint error')

    app, _ = stub(tmp_path, endpoint=endpoint, API_LIMITS_AI_ATTEMPTS='2')
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.post('/api/assistant/turn').status_code == 500
        assert client.post('/api/assistant/turn').status_code == 500
        response = client.post('/api/assistant/turn')
        assert response.status_code == 429 and response.json()['code'] == 'attempt_allowance_exhausted'
        assert len(calls) == 2


def test_atomic_reservations_across_two_apps_on_the_same_sqlite(tmp_path):
    overrides = {'API_LIMITS_AI_CONCURRENCY': '10'}
    app1, calls1 = stub(tmp_path, **overrides)
    app2, calls2 = stub(tmp_path, **overrides)
    start = threading.Barrier(8)
    with TestClient(app1) as first, TestClient(app2) as second:
        def request(i):
            start.wait(timeout=5)
            return (first if i % 2 else second).post('/api/assistant/turn').status_code
        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(request, range(8)))
        assert statuses.count(200) == 3 and statuses.count(429) == 5
        assert len(calls1) + len(calls2) == 3


def test_upload_has_separate_burst_and_concurrency_bounds(tmp_path):
    app, calls = stub(tmp_path, API_LIMITS_UPLOAD_REQUESTS='1')
    with TestClient(app) as client:
        assert client.post('/api/tours/assets', content=b'fixture').status_code == 200
        assert client.post('/api/tours/assets', content=b'fixture').status_code == 429
        assert client.post('/api/assistant/turn').status_code == 200
        assert len(calls) == 2


def test_upload_allowance_fits_maximum_studio_batch_and_retains_bounds(tmp_path):
    app, calls = stub(tmp_path)
    with TestClient(app) as client:
        # 12 panoramas + a floorplan + music must fit a single submission.
        for _ in range(14):
            assert client.post('/api/studio/projects/project/assets').status_code == 200
        for _ in range(10):
            assert client.post('/api/tours/assets').status_code == 200
        denied = client.post('/api/tours/assets')
        assert denied.status_code == 429 and denied.json()['retry_after'] == 60
        # Upload traffic still cannot spend or exhaust the independent AI bucket.
        assert client.post('/api/assistant/turn').status_code == 200
        assert len(calls) == 25


@pytest.mark.parametrize('route', [
    '/api/studio/projects/project/generations',
    '/api/studio/generations/generation/review',
    '/api/studio/generations/generation/retry',
    '/api/studio/generations/generation/edits',
    '/api/studio/generations/generation/edits/proposal/apply',
    '/api/studio-tours/tour/questions',
])
def test_studio_work_shares_existing_ai_attempt_allowance(tmp_path, route):
    app, calls = stub(tmp_path, API_LIMITS_AI_REQUESTS='1')
    with TestClient(app) as client:
        assert client.post('/api/assistant/turn').status_code == 200
        response = client.post(route)
        assert response.status_code == 429 and response.json()['code'] == 'rate_limited'
        assert len(calls) == 1


@pytest.mark.parametrize('route', [
    '/api/tours/audio-assets', '/api/studio/projects/project/assets',
])
def test_audio_and_studio_uploads_share_image_upload_bucket(tmp_path, route):
    app, calls = stub(tmp_path, API_LIMITS_UPLOAD_REQUESTS='1')
    with TestClient(app) as client:
        assert client.post('/api/tours/assets').status_code == 200
        assert client.post(route).status_code == 429
        assert client.post('/api/assistant/turn').status_code == 200
        assert len(calls) == 2


def test_app_factory_requires_limits_for_configured_key(tmp_path):
    with pytest.raises(ValueError, match='API_LIMITS_ENABLED'):
        create_app(db_path=tmp_path/'assistant.sqlite',
                   env={'OPENAI_API_KEY':'fixture-not-a-real-key'})


@pytest.mark.parametrize('route', [
    '/api/studio/projects/project/generations',
    '/api/studio/generations/generation/review',
    '/api/studio/generations/generation/retry',
    '/api/studio/generations/generation/edits',
    '/api/studio/generations/generation/edits/proposal/apply',
    '/api/studio-tours/tour/questions',
    '/api/tours/audio-assets',
    '/api/studio/projects/project/assets',
])
def test_real_factory_guard_runs_before_studio_and_audio_boundaries(tmp_path, route):
    env = config(tmp_path, API_LIMITS_AI_REQUESTS='1', API_LIMITS_UPLOAD_REQUESTS='1')
    app = create_app(db_path=tmp_path/'assistant.sqlite', env=env)
    with TestClient(app) as client:
        # No Origin or credentials; first admission reaches existing boundary and is
        # rejected, second admission is rejected before route/body processing.
        assert client.post(route, content=b'fixture').status_code == 403
        response = client.post(route, content=b'fixture')
        assert response.status_code == 429 and response.json()['code'] == 'rate_limited'


def test_storage_failure_is_explicit_fail_closed_and_releases_slot(tmp_path, monkeypatch):
    app, calls = stub(tmp_path)
    ledger = app.state.api_limits
    reserve = ledger.reserve

    def unavailable(group):
        raise sqlite3.OperationalError('sensitive internal path')

    with TestClient(app) as client:
        monkeypatch.setattr(ledger, 'reserve', unavailable)
        response = client.post('/api/assistant/turn')
        assert response.status_code == 503 and response.json()['code'] == 'limits_unavailable'
        assert 'sensitive' not in response.text and not calls
        monkeypatch.setattr(ledger, 'reserve', reserve)
        assert client.post('/api/assistant/turn').status_code == 200


@pytest.mark.parametrize('name,value', [
    ('API_LIMITS_ENABLED', ''), ('API_LIMITS_ENABLED', 'true'),
    ('API_LIMITS_DB', ''), ('API_LIMITS_DB', 'relative.sqlite'),
    ('API_LIMITS_AI_REQUESTS', ''), ('API_LIMITS_AI_REQUESTS', '0'),
    ('API_LIMITS_AI_REQUESTS', '-1'), ('API_LIMITS_AI_REQUESTS', '1.2'),
    ('API_LIMITS_AI_CONCURRENCY', 'two'), ('API_LIMITS_AI_ATTEMPTS', None),
    ('API_LIMITS_AI_WINDOW_SECONDS', '0'), ('API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS', '2'),
    ('API_LIMITS_UPLOAD_CONCURRENCY', '0'),
])
def test_invalid_config_fails_clearly(tmp_path, name, value):
    with pytest.raises(ValueError, match=name):
        install_limits(FastAPI(), config(tmp_path, **{name: value}))


def test_disabled_keyless_compatibility_and_mandatory_config_for_live_key(tmp_path):
    assert install_limits(FastAPI(), {}) is None
    with pytest.raises(ValueError, match='API_LIMITS_ENABLED'):
        install_limits(FastAPI(), {'OPENAI_API_KEY': 'fixture-not-a-real-key'})
    missing = config(tmp_path)
    del missing['API_LIMITS_AI_REQUESTS']
    with pytest.raises(ValueError, match='API_LIMITS_AI_REQUESTS'):
        install_limits(FastAPI(), missing)


def test_dedicated_storage_and_window_config_cannot_be_reset_silently(tmp_path):
    env = config(tmp_path)
    with pytest.raises(ValueError, match='cannot reuse'):
        install_limits(FastAPI(), env | {'ASSISTANT_DB': env['API_LIMITS_DB']})
    foreign = tmp_path / 'foreign.sqlite'
    with sqlite3.connect(foreign) as db:
        db.execute('CREATE TABLE checkpoints (id TEXT)')
    with pytest.raises(ValueError, match='dedicated'):
        install_limits(FastAPI(), env | {'API_LIMITS_DB': str(foreign)})
    app, _ = stub(tmp_path)
    with TestClient(app) as client:
        assert client.post('/api/assistant/turn').status_code == 200
    with pytest.raises(ValueError, match='persisted window configuration differs'):
        install_limits(FastAPI(), env | {'API_LIMITS_AI_WINDOW_SECONDS': '61'})
    with pytest.raises(ValueError, match='only once'):
        install_limits(app, env)


def test_ledger_contains_only_aggregate_metadata(tmp_path, monkeypatch):
    import os
    from pathlib import Path
    permissions = []
    original_chmod = Path.chmod
    def chmod(path, mode, **kwargs):
        permissions.append((path, mode))
        return original_chmod(path, mode, **kwargs)
    monkeypatch.setattr(Path, 'chmod', chmod)
    app, _ = stub(tmp_path)
    with TestClient(app) as client:
        response = client.post('/api/tours/drafts/private-tour-id/chat?private-query=yes',
                               content=b'private-message-marker', headers={
                                   'Cookie': 'session=private-cookie-marker',
                                   'Authorization': 'Bearer private-key-marker'})
        assert response.status_code == 200
    with sqlite3.connect(tmp_path / 'limits.sqlite') as db:
        dump = '\n'.join(db.iterdump())
    assert 'private-' not in dump and '/api/' not in dump
    assert (tmp_path / 'limits.sqlite', 0o600) in permissions
    # NTFS does not expose POSIX owner/group mode bits via stat/chmod.
    if os.name != 'nt':
        assert (tmp_path / 'limits.sqlite').stat().st_mode & 0o777 == 0o600


def test_existing_assistant_success_error_and_missing_key_semantics(tmp_path):
    def extract(state):
        if state['text'] == 'fixture failure':
            raise ValueError('fixture failure')
        return Extraction.model_validate({'intent': 'answer',
            'patch': {key: ('Quận 7' if key == 'address' else None) for key in LABELS},
            'clear_fields': [], 'clarification': None})

    env = config(tmp_path) | {'ASSISTANT_ORIGIN': 'http://testserver'}
    app = create_app(db_path=tmp_path / 'assistant.sqlite', env=env, extractor=extract)
    with TestClient(app) as client:
        assert client.get('/api/assistant/state').status_code == 200
        headers = {'Origin': 'http://testserver'}
        response = client.post('/api/assistant/turn', headers=headers,
                               json={'text': 'Quận 7', 'request_id': 'fixture-success'})
        assert response.status_code == 200 and response.json()['profile']['address'] == 'Quận 7'
        response = client.post('/api/assistant/turn', headers=headers,
                               json={'text': 'fixture failure', 'request_id': 'fixture-failure'})
        assert response.status_code == 502 and 'error' in response.json()
        # Missing key on voice retains the existing 503 instead of inventing audio.
        assert client.post('/api/assistant/voice', headers=headers).status_code == 503
        response = client.post('/api/assistant/turn', headers=headers,
                               json={'text': 'Quận 7', 'request_id': 'fixture-blocked'})
        assert response.status_code == 429
        assert client.get('/api/assistant/state').json()['profile'] == {'address': 'Quận 7'}
