"""Import one pinned user-provided cache into private MinIO, verify every byte.

Run on the existing VM with app-only MinIO env. No extraction, model generation,
public bucket, original-data deletion, or paid API. Catalog stays outside Git.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile
from minio import Minio
from minio.error import S3Error
import urllib3

SHA='734f7053604b67c24701acff3a044e2d33241272149e9596b0eefdca5fc592e3'
MANIFEST_SHA='36a04f9d83615fc35809a36b1a6189bd1514523e5e2b56e6ccb2172ab753fe3c'
DEMO='zind-house-000'
PREFIX='/api/demos/'+DEMO+'/assets/'
ROOT='zind-house-000/'


def run(bundle, output):
    if hashlib.file_digest(bundle.open('rb'),'sha256').hexdigest()!=SHA:
        raise ValueError('Wrong or incomplete source bundle')
    env=os.environ
    if env['MINIO_BUCKET']!='estagent-media' or env['MINIO_SECURE']!='0':
        raise ValueError('Require dedicated private Estagent bucket')
    client=Minio(env['MINIO_ENDPOINT'],access_key=env['MINIO_ACCESS_KEY'],secret_key=env['MINIO_SECRET_KEY'],secure=False,
                 http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5,read=30),retries=False))
    bucket=env['MINIO_BUCKET']; assets={}; total=0
    def put(name, data, mime, original_sha=None):
        nonlocal total
        sha=hashlib.sha256(data).hexdigest();key=f'demos/{DEMO}/{sha}/{name}'
        try:
            existing=client.stat_object(bucket,key)
        except S3Error as error:
            if error.code not in {'NoSuchKey','NoSuchObject'}:raise
            client.put_object(bucket,key,io.BytesIO(data),len(data),content_type=mime,metadata={'sha256':sha},num_parallel_uploads=1)
        else:
            if existing.size!=len(data):raise ValueError('Existing immutable object size mismatch')
        response=client.get_object(bucket,key)
        try:
            digest=hashlib.sha256()
            for chunk in response.stream(1024*1024):digest.update(chunk)
            if digest.hexdigest()!=sha:raise ValueError('MinIO readback hash mismatch')
        finally:response.close();response.release_conn()
        assets[name]={'key':key,'sha256':sha,'bytes':len(data),'content_type':mime}
        if original_sha:assets[name]['source_sha256']=original_sha
        total+=len(data)
    with zipfile.ZipFile(bundle) as archive:
        raw=archive.read(ROOT+'viewer/public/house/manifest.json')
        if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA:raise ValueError('Source manifest mismatch')
        manifest=json.loads(raw)
        if len(manifest['rooms'])!=15 or len(manifest['captures'])!=32:raise ValueError('Unexpected source counts')
        if sum(len(r['dollhouseCaptureIds']) for r in manifest['rooms'])!=16:raise ValueError('Unexpected marker count')
        for capture in manifest['captures']:
            name=capture['url'].removeprefix('/'); data=archive.read(ROOT+'viewer/public/'+name)
            if hashlib.sha256(data).hexdigest()!=capture['sha256']:raise ValueError('Source panorama hash mismatch')
            put(name,data,'image/jpeg',capture['sha256'])
            capture['url']=PREFIX+name
        model=archive.read(ROOT+'viewer/public/house/dollhouse-studio.glb')
        if len(model)!=9682280 or model[:4]!=b'glTF':raise ValueError('Wrong current GLB')
        put('house/dollhouse-studio.glb',model,'model/gltf-binary',hashlib.sha256(model).hexdigest())
        for room in manifest['rooms']:room['videos']=[]
        manifest['dollhouse']['url']=PREFIX+'house/dollhouse-studio.glb'
        manifest['dollhouse'].pop('editableSource',None);manifest['dollhouse'].pop('savedVersionUrl',None)
        manifest['provenance']={'mode':'user_provided_cached','new_reconstruction':False,'audio_available':False,
            'source_bundle_sha256':SHA,'source_manifest_sha256':MANIFEST_SHA,'license_independently_verified':False}
        put('house/manifest.json',json.dumps(manifest,ensure_ascii=False,separators=(',',':')).encode(),'application/json',MANIFEST_SHA)
        for filename in ['tour-6WriKqfJ.js','OrbitControls-CoFX98BI.js','tour-B_2u0cuc.css']:
            raw=archive.read(ROOT+'viewer/dist/assets/'+filename)
            data=raw
            if filename.startswith('tour-') and filename.endswith('.js'):
                # Fixed, audited bundle: namespace requests; never expose root /house.
                data=data.replace(b'/house/',(PREFIX+'house/').encode())
                data=data.replace(b'PanSplat rendering pending',b'Cached source captures')
                anchor=b'ArrowRight:[5,0]'
                if data.count(anchor)!=1:raise ValueError('Audited renderer keyboard adapter anchor changed')
                data=data.replace(anchor,anchor+b',EstagentRotate:[.05,0]')
            put('runtime/'+filename,data,'text/css' if filename.endswith('.css') else 'application/javascript',hashlib.sha256(raw).hexdigest())
    doc={'id':DEMO,'source_bundle_sha256':SHA,'source_manifest_sha256':MANIFEST_SHA,'assets':assets,
         'thumbnail':manifest['captures'][0]['url'].removeprefix(PREFIX),'total_bytes':total}
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.pending')
    with os.fdopen(os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(doc,f,ensure_ascii=False)
    os.replace(temporary,output)
    print(json.dumps({'imported':DEMO,'objects':len(assets),'bytes':total,'panoramas':32,'rooms':15,'markers':16,'all_minio_readback_sha256_verified':True,'bundle_sha256':SHA,'clips_imported':0,'paid_calls':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bundle',type=Path,required=True);parser.add_argument('--catalog',type=Path,required=True);args=parser.parse_args()
    try:run(args.bundle,args.catalog)
    except Exception as error:raise SystemExit('Demo import failed: '+type(error).__name__) from None
