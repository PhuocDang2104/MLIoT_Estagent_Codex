"""Actual stdlib WAV decode + local HTTP/SQLite. All tracks are synthetic PCM tones."""
import io
import json
import math
import struct
import wave
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from server.assistant.app import create_app
from server.tours.audio import decode_wav, MAX_AUDIO_BYTES
from server.tours.api import COOKIE

ORIGIN='http://testserver'
HEADERS={'Origin':ORIGIN}
PROVENANCE={'source_label':'Synthetic test tone','rights':'owned','rights_note':'Generated in this test; not human narration or licensed music.'}


def wav(seconds=1,rate=16000,channels=1,width=2):
    frames=int(seconds*rate);stream=io.BytesIO()
    sample=(b'\x00\x10' if width==2 else b'\x80' if width==1 else b'\x00'*width)
    with wave.open(stream,'wb') as target:
        target.setnchannels(channels);target.setsampwidth(width);target.setframerate(rate);target.writeframes(sample*channels*frames)
    return stream.getvalue()


def app_at(path):return create_app(db_path=path/'assistant.sqlite',env={'ASSISTANT_ORIGIN':ORIGIN})
def start(c):c.get('/api/tours/session');return c.cookies.get(COOKIE)
def post(c,path,body):return c.post('/api/tours'+path,json=body,headers=HEADERS)
def upload(c,body=None,provenance=None):
    return c.post('/api/tours/audio-assets',content=wav() if body is None else body,headers=HEADERS|{'Content-Type':'audio/wav','X-Audio-Metadata':quote(json.dumps(provenance or PROVENANCE))})
def draft(c):
    assets=[]
    for color in ['navy','green']:
        image=io.BytesIO();Image.new('RGB',(80,40),color).save(image,format='PNG')
        assets.append(c.post('/api/tours/assets',content=image.getvalue(),headers=HEADERS).json()['id'])
    return post(c,'/drafts',{'asset_ids':assets,'locale':'en','request_id':'audio-draft-test'}).json()
def attach(c,doc,music=None,narration=None):
    return c.put(f'/api/tours/drafts/{doc["id"]}/audio',json={'revision':doc['revision'],'music_asset_id':music,'narration':narration or []},headers=HEADERS)
def binding(doc,track,index=0):return {'scene_id':doc['scenes'][index]['id'],'locale':'en','asset_id':track['asset_id'],'transcript':'Synthetic tone; not speech.'}


@pytest.mark.parametrize('channels,rate',[(1,8000),(1,16000),(2,44100),(2,48000)])
def test_measures_real_pcm_and_serves_ranges(tmp_path,channels,rate):
    with TestClient(app_at(tmp_path)) as c:
        start(c);body=wav(1.25,rate,channels);r=upload(c,body);assert r.status_code==200,r.text
        track=r.json();assert track['duration_seconds']==1.25 and track['sample_rate']==rate and track['channels']==channels
        assert track['source_label']==PROVENANCE['source_label']
        downloaded=c.get(track['url']);assert downloaded.status_code==200 and downloaded.headers['content-type']=='audio/wav'
        with wave.open(io.BytesIO(downloaded.content),'rb') as parsed:assert parsed.getnframes()/parsed.getframerate()==1.25
        ranged=c.get(track['url'],headers={'Range':'bytes=0-43'});assert ranged.status_code==206 and len(ranged.content)==44
        assert upload(c,body).json()==track
        changed=upload(c,body,PROVENANCE|{'rights_note':'A second explicitly declared test source.'}).json()
        assert changed['asset_id']!=track['asset_id']
        assert c.get(track['url']).content==downloaded.content


def test_invalid_headers_and_truncated_or_unsupported_audio(tmp_path):
    valid=wav();wrong_encoding=bytearray(valid);struct.pack_into('<H',wrong_encoding,20,3)
    bad_rate=bytearray(valid);struct.pack_into('<I',bad_rate,28,100)
    samples=[b'ID3'+b'x'*100,b'<script>not audio</script>',valid[:-5],bytes(wrong_encoding),bytes(bad_rate),wav(width=1),wav(rate=96000),wav(seconds=0)]
    with TestClient(app_at(tmp_path)) as c:
        start(c)
        for body in samples:assert upload(c,body).status_code==415
        assert c.post('/api/tours/audio-assets',content=valid,headers=HEADERS).status_code==422
        assert c.post('/api/tours/audio-assets',content=valid,headers={'X-Audio-Metadata':quote(json.dumps(PROVENANCE))}).status_code==403
        assert upload(c,provenance=PROVENANCE|{'rights':'unknown'}).status_code==422
        assert upload(c,provenance=PROVENANCE|{'source_label':''}).status_code==422


def test_duration_size_limits_and_normalized_metadata(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        start(c)
        assert upload(c,wav(180,8000)).status_code==200
        assert upload(c,wav(180.01,8000)).status_code==413
        assert upload(c,b'0'*(MAX_AUDIO_BYTES+1)).status_code==413
        # Valid unknown RIFF chunk is stripped, not distributed as uploaded metadata.
        body=wav();extra=b'LIST'+struct.pack('<I',8)+b'PRIVATE!';combined=bytearray(body+extra);struct.pack_into('<I',combined,4,len(combined)-8)
        result=upload(c,bytes(combined));assert result.status_code==200
        assert b'PRIVATE!' not in c.get(result.json()['url']).content


def test_owner_isolation_unknown_refs_and_path_boundary(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        first=start(c);doc=draft(c);track=upload(c).json()
        c.cookies.clear();start(c)
        assert c.get(track['url']).status_code==404
        assert attach(c,doc,music=track['asset_id']).status_code==404
        own=draft(c)
        assert attach(c,own,music=track['asset_id']).status_code==404
        assert c.get('/api/tours/audio-assets/%2e%2e%2fsecret').status_code==404
        assert attach(c,own,music='https://example.com/audio.wav').status_code==422
        c.cookies.clear();c.cookies.set(COOKIE,first,path='/api/tours/')
        assert c.get(track['url']).status_code==200
        assert attach(c,doc,narration=[binding(doc,track)|{'scene_id':'a'*32}]).status_code==422
        assert attach(c,doc,narration=[binding(doc,track)|{'locale':'vi'}]).status_code==422
        assert attach(c,doc,narration=[binding(doc,track)]*2).status_code==422


def test_revision_review_immutable_publish_and_restart(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        cookie=start(c);doc=draft(c);music=upload(c,wav(2)).json();voice=upload(c,wav(1)).json()
        route=f'/drafts/{doc["id"]}'
        post(c,route+'/review',{'revision':1})
        partial=attach(c,doc,music=music['asset_id'],narration=[binding(doc,voice)]).json()
        assert partial['revision']==2 and partial['audio']['status']=='partial'
        assert post(c,route+'/publish',{'revision':2}).status_code==409
        assert attach(c,doc,music=music['asset_id']).status_code==409
        complete=attach(c,partial,music=music['asset_id'],narration=[binding(doc,voice,0),binding(doc,voice,1)]).json()
        assert complete['revision']==3 and complete['audio']['status']=='ready'
        assert post(c,route+'/review',{'revision':3}).status_code==200
        published=post(c,route+'/publish',{'revision':3}).json()
        assert published['audio']['music']['url'].startswith(f'/api/tours/published/{published["id"]}/audio/')
        old_url=published['audio']['narration'][0]['track']['url'];old_bytes=c.get(old_url).content
        changed=attach(c,complete).json();assert changed['audio']=={'status':'unavailable','source':'none','narration':None,'music':None}
        assert c.get(f'/api/tours/published/{published["id"]}').json()==published
        c.cookies.clear();assert c.get(old_url).content==old_bytes
        assert c.get(f'/api/tours/published/{published["id"]}/audio/'+('b'*32)).status_code==404
        assert c.get(voice['url']).status_code==401
    with TestClient(app_at(tmp_path)) as c:
        assert c.get(old_url).content==old_bytes
        c.cookies.set(COOKIE,cookie,path='/api/tours/')
        assert c.get('/api/tours'+route).json()['audio']['status']=='unavailable'


def test_locale_edit_does_not_relabel_audio_and_missing_blob_blocks_publish(tmp_path):
    with TestClient(app_at(tmp_path)) as c:
        start(c);doc=draft(c);voice=upload(c).json()
        complete=attach(c,doc,narration=[binding(doc,voice,i) for i in range(2)]).json()
        body={k:complete[k] for k in ['title','revision','start_scene_id']};body['locale']='vi'
        body['scenes']=[{k:v for k,v in s.items() if k not in {'image_url','thumbnail_url'}} for s in complete['scenes']]
        updated=c.put(f'/api/tours/drafts/{doc["id"]}',json=body,headers=HEADERS).json()
        assert updated['audio']['status']=='partial' and updated['audio']['narration'][0]['locale']=='en'
        post(c,f'/drafts/{doc["id"]}/review',{'revision':updated['revision']})
        (tmp_path/'tours/audio'/f'{voice["asset_id"]}.wav').unlink()
        assert post(c,f'/drafts/{doc["id"]}/publish',{'revision':updated['revision']}).status_code==404


def test_old_manifest_shape_remains_valid_and_fixture_schema_is_current():
    from server.tours.models import Manifest
    import jsonschema
    fixture=json.loads(Path('fixtures/checkpoint-tour/tour.json').read_text())
    schema=json.loads(Path('fixtures/tour.schema.json').read_text())
    jsonschema.validate(fixture,schema);Manifest.model_validate(fixture)
    fixture['audio']={'status':'unavailable','source':'none','narration':None,'music':None}
    jsonschema.validate(fixture,schema);Manifest.model_validate(fixture)
    assert schema==Manifest.model_json_schema()
