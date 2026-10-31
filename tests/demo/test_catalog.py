import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from server.demos import BUNDLE_SHA, DEMO_ID, install_demos, read_catalog


class Stream(io.BytesIO):
    def release_conn(self):
        self.released=True


class Client:
    def __init__(self):self.objects={};self.streams=[]
    def stat_object(self,bucket,key):
        data=self.objects[key]
        return SimpleNamespace(size=len(data),metadata={'x-amz-meta-sha256':hashlib.sha256(data).hexdigest()})
    def get_object(self,bucket,key,offset=0,length=None):
        stream=Stream(self.objects[key][offset:offset+length]);self.streams.append(stream);return stream


def setup(tmp_path):
    client=Client();entries={}
    for name,data,mime in [('house/manifest.json',b'{"fixture":true}','application/json'),('house/dollhouse-studio.glb',b'glTF'+bytes(range(32)),'model/gltf-binary'),('house/panos/fixture.jpg',b'synthetic-fixture','image/jpeg')]:
        digest=hashlib.sha256(data).hexdigest();key=f'demos/{DEMO_ID}/{digest}/{name}'
        entries[name]={'key':key,'sha256':digest,'bytes':len(data),'content_type':mime};client.objects[key]=data
    doc={'id':DEMO_ID,'source_bundle_sha256':BUNDLE_SHA,'thumbnail':'house/panos/fixture.jpg','assets':entries}
    path=tmp_path/'catalog.json';path.write_text(json.dumps(doc))
    app=FastAPI();app.state.object_storage=SimpleNamespace(client=client,bucket='private-test')
    install_demos(app,{'DEMO_CATALOG_PATH':str(path)},Path(__file__).resolve().parents[2]/'web')
    return TestClient(app),client,path,doc


def test_catalog_membership_range_stream_cleanup(tmp_path):
    app,sdk,_,_=setup(tmp_path)
    assert app.get('/api/demos').json()[0]['href']=='/demos/'+DEMO_ID
    assert app.get('/demos/'+DEMO_ID).status_code==200
    path=f'/api/demos/{DEMO_ID}/assets/house/dollhouse-studio.glb'
    response=app.get(path,headers={'Range':'bytes=2-8'})
    assert response.status_code==206 and response.content==(b'glTF'+bytes(range(32)))[2:9]
    assert response.headers['Content-Range']=='bytes 2-8/36'
    assert sdk.streams[-1].closed and sdk.streams[-1].released
    assert app.get(path,headers={'Range':'bytes=-4'}).content==bytes(range(28,32))
    for value in ['bytes=99-','bytes=-0','bytes=8-2','bytes=1-2,4-5']:
        assert app.get(path,headers={'Range':value}).status_code==416
    count=len(sdk.streams);assert app.head(path).status_code==200 and len(sdk.streams)==count
    for name in ['source.zip','house/../secret.env','house/model.blend','runtime/other.js','house/not-listed.jpg','%2e%2e/%2e%2e/.env.local']:
        assert app.get(f'/api/demos/{DEMO_ID}/assets/'+name).status_code==404
    assert app.get('/api/demos/other/assets/house/manifest.json').status_code==404


def test_fail_closed_config_and_storage(tmp_path):
    app,sdk,path,doc=setup(tmp_path)
    key=doc['assets']['house/manifest.json']['key'];sdk.objects[key]=b'wrong'
    assert app.get(f'/api/demos/{DEMO_ID}/assets/house/manifest.json').status_code==503
    doc['assets']['house/manifest.json']['key']='another-project/secret'
    path.write_text(json.dumps(doc))
    with pytest.raises(ValueError,match='DEMO_CATALOG_PATH'):read_catalog(path)
    with pytest.raises(ValueError,match='DEMO_CATALOG_PATH'):read_catalog(tmp_path/'absent')
    base=FastAPI();base.state.object_storage=None;install_demos(base,{},tmp_path)
    assert TestClient(base).get('/api/demos').json()==[]
