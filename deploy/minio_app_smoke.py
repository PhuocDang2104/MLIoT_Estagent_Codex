"""Actual SDK + app HTTP routes, synthetic media and isolated temporary SQLite.

Run in the candidate image with only the MinIO app env and tmpfs /data.
No provider mocks, generation calls, production DB or public site publication.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from urllib.parse import quote
import wave
from PIL import Image
from fastapi.testclient import TestClient
from server.assistant.app import create_app


def main():
    assert not os.environ.get('OPENAI_API_KEY'), 'API key must remain empty'
    headers={'Origin':'http://testserver'}
    image=io.BytesIO(); Image.new('RGB',(128,64),(29,143,181)).save(image,format='PNG')
    raw=image.getvalue()
    sound=io.BytesIO()
    with wave.open(sound,'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000)
        stream.writeframes(b'\0\0'*800)
    multipart=io.BytesIO()
    with wave.open(multipart,'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(16000)
        stream.writeframes(b'\0\0'*(16000*175))
    large=multipart.getvalue()
    assert 5*1024*1024 < len(large) < 20*1024*1024
    with tempfile.TemporaryDirectory(dir='/data') as directory:
        root=Path(directory)
        env={k:v for k,v in os.environ.items() if k.startswith('MINIO_')}
        env.update(MEDIA_STORAGE_BACKEND='minio',ASSISTANT_ORIGIN='http://testserver',OPENAI_API_KEY='',ESTAGENT_KEYLESS_PREVIEW='1')
        def app(backend='minio'):
            return create_app(db_path=root/'assistant.sqlite',env={**env,'MEDIA_STORAGE_BACKEND':backend})
        with TestClient(app()) as client:
            client.get('/api/tours/session')
            response=client.post('/api/tours/assets',headers=headers,content=raw)
            assert response.status_code==200,'image upload'; im=response.json()
            assert client.post('/api/tours/assets',headers=headers,content=raw).json()==im,'dedupe'
            provenance={'source_label':'Synthetic silence','rights':'owned','rights_note':'Generated test bytes.'}
            response=client.post('/api/tours/audio-assets',headers=headers|{'X-Audio-Metadata':quote(json.dumps(provenance))},content=sound.getvalue())
            assert response.status_code==200,'audio upload'; audio=response.json()
            response=client.post('/api/tours/audio-assets',headers=headers|{'X-Audio-Metadata':quote(json.dumps(provenance))},content=large)
            assert response.status_code==200,'multipart audio upload'; big=response.json()
            store=client.app.state.object_storage
            info=store.client.stat_object(store.bucket,f'tours/audio/{big["asset_id"]}.wav')
            assert info.etag.endswith('-2'),'SDK must really use two-part multipart'
            assert hashlib.sha256(client.get(big['url']).content).hexdigest()==hashlib.sha256(large).hexdigest(),'multipart SHA'
            result=client.get(big['url'],headers={'Range':'bytes=5242800-5243000'})
            assert result.status_code==206 and result.content==large[5242800:5243001],'multipart boundary Range'
            tours_cookie=client.cookies.get('estagent_tours')
            # Large fixture stays unattached/private; only small fixture is published in isolated SQLite.
            draft=client.post('/api/tours/drafts',headers=headers,json={'asset_ids':[im['id']],'locale':'en','request_id':'minio-live-qa'}).json()
            response=client.put(f'/api/tours/drafts/{draft["id"]}/audio',headers=headers,json={'revision':draft['revision'],'music_asset_id':audio['asset_id'],'narration':[]})
            assert response.status_code==200,'attach audio'; draft=response.json()
            assert client.post(f'/api/tours/drafts/{draft["id"]}/review',headers=headers,json={'revision':draft['revision']}).status_code==200,'review'
            response=client.post(f'/api/tours/drafts/{draft["id"]}/publish',headers=headers,json={'revision':draft['revision']})
            assert response.status_code==200,'isolated publish'; published=response.json()
            url=published['audio']['music']['url']
            result=client.get(url,headers={'Range':'bytes=0-43'})
            assert result.status_code==206 and len(result.content)==44,'audio Range'
            assert client.get(url,headers={'Range':'bytes=999999-'}).status_code==416,'invalid Range'
            client.cookies.clear()
            assert client.get(im['image_url']).status_code==401,'private owner guard'
            assert client.get(big['url']).status_code==401,'multipart stays private'
            assert client.get(published['scenes'][0]['image_url']).status_code==200,'published image'
            client.get('/api/studio/session')
            response=client.post('/api/studio/projects',headers=headers,json={'name':'Synthetic MinIO QA','description':'No real property','panorama_confirmed':True,'request_id':'minio-live-studio'})
            assert response.status_code==201,'Studio project'; pid=response.json()['id']
            response=client.post(f'/api/studio/projects/{pid}/assets?name=synthetic.png',headers=headers,content=raw)
            assert response.status_code==201,'Studio upload'; asset=response.json()
            path=f'/api/studio/projects/{pid}/assets/{asset["id"]}'
            assert client.get(path).content==raw,'Studio bytes'
            assert client.get(path,headers={'Range':'bytes=0-7'}).status_code==206,'Studio Range'
            assert not client.get('/api/studio/session').json()['configured'],'keyless'
        assert not list(root.rglob('*.jpg')) and not list(root.rglob('*.wav')),'remote-only files'
        with sqlite3.connect(root/'studio'/'creator.sqlite') as db:
            assert db.execute('SELECT COUNT(*) FROM media_refs WHERE backend="minio"').fetchone()[0]==1
            assert db.execute('SELECT SUM(length(content)) FROM assets').fetchone()[0]==0,'no BLOB duplication'
        with TestClient(app()) as client:
            client.cookies.set('estagent_tours',tours_cookie,path='/api/tours/')
            assert hashlib.sha256(client.get(big['url']).content).hexdigest()==hashlib.sha256(large).hexdigest(),'multipart restart SHA'
            digest=hashlib.sha256(client.get(url).content).hexdigest()
            assert digest==hashlib.sha256(sound.getvalue()).hexdigest(),'restart audio bytes'
        with TestClient(app('local')) as client:
            assert client.get(url).status_code==503,'no fallback for remote marker'
    print('PASS private multipart PCM WAV: 5600044 bytes, 175 seconds, two-part ETag, cross-part Range and SHA/restart; no publication')
    print('PASS real MinIO app upload/dedupe/private401/isolated publish/Range206+416/Studio empty BLOB/restart/no fallback; no AI calls')


if __name__=='__main__':
    main()
