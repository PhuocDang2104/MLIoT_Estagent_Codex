import json
import math
import os
from pathlib import Path
import struct
import subprocess
import pytest
from pipelines.core.blender_worker import BlenderWorker, configured_worker
from tests.core.house_fixture import house_plan


def inputs():
    plan=house_plan()
    return {'generation_id':'synthetic-qa','modeling_plan':plan},[
        {'checkpoint_id':c['checkpoint_id'],'room_id':c['room_id']} for c in plan['captures']]


def test_disabled_and_missing_worker(tmp_path):
    assert configured_worker({'STUDIO_GEOMETRY':'off'},tmp_path) is None
    with pytest.raises(ValueError):
        BlenderWorker(tmp_path/'missing',tmp_path)


def test_worker_failure_and_timeout_never_mark_complete(tmp_path,monkeypatch):
    worker=BlenderWorker(__file__,tmp_path)
    project,rooms=inputs()
    def fail(*args,**kwargs):
        assert '--disable-autoexec' in args[0] and '--factory-startup' in args[0]
        assert kwargs['timeout'] == 180
        raise subprocess.TimeoutExpired(args[0],180)
    monkeypatch.setattr(subprocess,'run',fail)
    with pytest.raises(subprocess.TimeoutExpired): worker.build(project,rooms,[],[])
    assert not list(tmp_path.rglob('complete.json'))


def test_actual_blender_export_and_cache(tmp_path,monkeypatch):
    worker=configured_worker(dict(os.environ),tmp_path)
    if worker is None:
        pytest.skip('Install Blender or set STUDIO_BLENDER_EXECUTABLE for real CLI acceptance')
    project,rooms=inputs()
    for index in range(3,7):
        capture={'checkpoint_id':f'cp{index:02}','room_id':'r01','position':{'x':1+index*.25,'y':1.6,'z':2.5},
                 'heading':30,'accuracy':'approximate'}
        project['modeling_plan']['captures'].append(capture)
        rooms.append({'checkpoint_id':capture['checkpoint_id'],'room_id':'r01'})
    result=worker.build(project,rooms,[],[])
    glb=result['glb']
    assert glb[:4]==b'glTF' and struct.unpack('<I',glb[8:12])[0]==len(glb)
    length=struct.unpack('<I',glb[12:16])[0]
    doc=json.loads(glb[20:20+length])
    assert len(doc['meshes'])>30 and len(doc['images'])>=2
    binary=glb[28+length:]
    for mesh in doc['meshes']:
        for primitive in mesh['primitives']:
            accessor=doc['accessors'][primitive['attributes']['POSITION']]
            assert accessor['type']=='VEC3' and accessor['componentType']==5126
            view=doc['bufferViews'][accessor['bufferView']]
            start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
            stride=view.get('byteStride',12)
            for index in range(accessor['count']):
                assert all(math.isfinite(v) for v in struct.unpack_from('<3f',binary,start+index*stride))
    assert all('uri' not in x for key in ('buffers','images') for x in doc[key])
    floors=[n for n in doc['nodes'] if n.get('extras',{}).get('kind')=='floor']
    assert len(floors)==2
    assert any('sink' in n.get('name','') for n in doc['nodes'])
    assert set(result['anchors'])=={r['checkpoint_id'] for r in rooms}
    assert sum(a['dollhouse_visible'] for a in result['anchors'].values() if a['room_id']=='r01')==2
    assert result['anchors']['cp02']['position']==[6,1.6,2]
    assert list(tmp_path.rglob('house.blend'))
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:pytest.fail('Cache ran Blender again'))
    assert worker.build(project,rooms,[],[])['glb']==glb
