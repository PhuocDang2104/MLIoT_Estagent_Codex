from fastapi.testclient import TestClient
from server.assistant.app import create_app
from server.creator.worker import HTTPGeometryWorker
from tests.ai.test_creator import app


def test_ai_entry_and_photo_editor_both_remain_reachable(tmp_path):
    with TestClient(app(tmp_path)) as client:
        assert 'id="create-form"' in client.get('/business/create').text
        for route in ('/business/photos', '/creator.html'):
            assert 'id="composer"' in client.get(route).text
        assert '/business/photos' in client.get('/business/create').text
        assert '/api/studio-tours' in client.get('/viewer.js').text
        assert '/api/demos' in client.get('/viewer.js').text


def test_explicit_http_worker_keeps_precedence_over_local_blender(tmp_path):
    application=create_app(db_path=tmp_path/'assistant.sqlite',env={
        'ASSISTANT_ORIGIN':'http://testserver','STUDIO_GEOMETRY':'blender',
        'STUDIO_BLENDER_EXECUTABLE':str(tmp_path/'not-installed'),
        'STUDIO_GEOMETRY_URL':'http://worker.internal'})
    with TestClient(application) as client:
        assert isinstance(client.app.state.creator.worker,HTTPGeometryWorker)
        assert client.get('/api/studio/health').json()['geometry_configured']
