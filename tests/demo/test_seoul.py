import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from server.demos import SEOUL_ID, SEOUL_SHA, install_demos, read_catalog
from tests.demo.test_catalog import setup


def test_seoul_exports_are_explicit_and_zind_stays_excluded(tmp_path):
    _, sdk, _, original = setup(tmp_path)
    entries = {}
    for name, item in original['assets'].items():
        key = item['key'].replace('zind-house-000', SEOUL_ID)
        entries[name] = dict(item, key=key)
        sdk.objects[key] = sdk.objects[item['key']]
    package = {'locale': 'en', 'scope': 'seoul_sample_only', 'voice_source': 'openai_generated',
               'voice_model': 'gpt-4o-mini-tts', 'duration_seconds': 8,
               'chapters': [{'capture_id': capture, 'title': 'Synthetic', 'text': 'Synthetic narration.',
                             'start': i, 'duration': 1} for i, capture in enumerate(
                   ['00000000', '00000030', '00000070', '00000110', '00000150', '00000180', '00000250', '00000310'])]}
    for kind, ext, mime in [('video', 'mp4', 'video/mp4'), ('audio', 'wav', 'audio/wav'),
                           ('transcript', 'txt', 'text/plain'), ('captions', 'vtt', 'text/vtt')]:
        name = f'house/exports/seoul-tour-en.{ext}'
        content = ('synthetic '+kind).encode(); digest = hashlib.sha256(content).hexdigest()
        key = f'demos/{SEOUL_ID}/{digest}/{name}'
        entries[name] = {'key': key, 'sha256': digest, 'bytes': len(content), 'content_type': mime}
        sdk.objects[key] = content; package[kind] = name
    doc = dict(original, id=SEOUL_ID, source_bundle_sha256=SEOUL_SHA, assets=entries, exports=package)
    path = tmp_path/'exports.json';path.write_text(json.dumps(doc))
    app = FastAPI();app.state.object_storage = SimpleNamespace(client=sdk, bucket='private-test')
    install_demos(app, {'SEOUL_CATALOG_PATH': str(path)}, Path(__file__).resolve().parents[2]/'web')
    client = TestClient(app)
    public = client.get('/api/demos/seoul-apartment/exports').json()
    assert public['scope'] == 'seoul_sample_only' and len(public['chapters']) == 8
    assert client.get('/api/demos/zind-house-000/exports').status_code == 404
    assert client.get('/api/demos/seoul-apartment/exports', params={'locale': 'vi'}).json()['locale'] == 'en'
    for kind in ['video', 'audio', 'transcript', 'captions']:
        response = client.get(public[kind]['download_url'], headers={'Range': 'bytes=0-3'})
        assert response.status_code == 206 and response.content == b'synt'
        assert response.headers['content-disposition'].startswith('attachment; filename="seoul-tour-en.')
    assert client.get('/api/demos/seoul-apartment/assets/house/exports/other.mp4').status_code == 404
    package['scope'] = 'all_samples';path.write_text(json.dumps(doc))
    with pytest.raises(ValueError):read_catalog(path, SEOUL_ID, SEOUL_SHA)
    original['exports'] = package;path.write_text(json.dumps(original))
    with pytest.raises(ValueError):read_catalog(path)


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
