import json
from pathlib import Path
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from server.demos import SEOUL_ID, SEOUL_SHA, install_demos, read_catalog
from tests.demo.test_catalog import setup


def test_separate_sample_preserves_original_and_scopes_objects(tmp_path):
    original, sdk, path, doc = setup(tmp_path)
    before = original.get('/api/demos').json()[0]
    entries = {}
    for name, item in doc['assets'].items():
        key = item['key'].replace('zind-house-000', SEOUL_ID)
        entries[name] = dict(item, key=key)
        sdk.objects[key] = sdk.objects[item['key']]
    seoul = dict(doc, id=SEOUL_ID, source_bundle_sha256=SEOUL_SHA, assets=entries)
    seoul_path = tmp_path/'seoul.json'
    seoul_path.write_text(json.dumps(seoul))
    app = FastAPI()
    app.state.object_storage = SimpleNamespace(client=sdk, bucket='private-test')
    install_demos(app, {'DEMO_CATALOG_PATH': str(path), 'SEOUL_CATALOG_PATH': str(seoul_path)}, Path(__file__).resolve().parents[2]/'web')
    client = TestClient(app)
    cards = client.get('/api/demos').json()
    assert cards[0] == before and cards[1]['captures'] == 8
    page = client.get('/demos/'+SEOUL_ID)
    assert page.status_code == 200 and 'seoul.js' in page.text
    assert "'wasm-unsafe-eval'" in page.headers['content-security-policy']
    response = client.get(f'/api/demos/{SEOUL_ID}/assets/house/dollhouse-studio.glb', headers={'Range': 'bytes=0-3'})
    assert response.status_code == 206 and response.content == b'glTF'
    assert client.get(f'/api/demos/{SEOUL_ID}/assets/source.zip').status_code == 404
    assert client.get(f'/api/demos/{SEOUL_ID}/intro').status_code == 404
    seoul['assets']['house/manifest.json']['key'] = doc['assets']['house/manifest.json']['key']
    seoul_path.write_text(json.dumps(seoul))
    with pytest.raises(ValueError):
        read_catalog(seoul_path, SEOUL_ID, SEOUL_SHA)
