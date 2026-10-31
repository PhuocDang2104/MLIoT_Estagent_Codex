"""Import the authorized completed house-guide batch, never generate speech."""
import argparse,hashlib,io,json,os,wave
from pathlib import Path
from minio import Minio
import urllib3
PIN='0a7ca8a00bbc836bc56b55bc4f77f92d7a98a4a0c9ea87b83a64750e326de7b1'
V2='8d22cafbeff7c02ea685bf5f7080233d286079ab73b03537c2a220203af9f3b5'
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--manifest-sha',choices=[PIN,V2],default=PIN);a=p.parse_args()
 raw=(a.source/'manifest.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==a.manifest_sha
 batch=json.loads(raw);doc=json.loads(a.catalog.read_text());env=os.environ;assert env['MINIO_BUCKET']=='estagent-media'
 c=Minio(env['MINIO_ENDPOINT'],access_key=env['MINIO_ACCESS_KEY'],secret_key=env['MINIO_SECRET_KEY'],secure=env['MINIO_SECURE']=='1',http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5,read=30),retries=False));bucket=env['MINIO_BUCKET']
 response=c.get_object(bucket,doc['assets']['house/manifest.json']['key'])
 try:house=json.loads(response.read())
 finally:response.close();response.release_conn()
 expected={(room['id'],capture) for room in house['rooms'] for capture in room['dollhouseCaptureIds']}
 assert {(m['room_id'],m['capture_id']) for m in batch['markers']}==expected and len(expected)==16
 assert batch['source']['sha256']==doc['source_manifest_sha256']
 clips={}
 for item in batch['clips']:
  assert item['status']=='completed' and item['source']=='openai_generated' and item['file']=='clips/'+item['id']+'.wav'
  data=(a.source/item['file']).read_bytes();sha=hashlib.sha256(data).hexdigest();assert sha==item['sha256'] and len(data)==item['bytes']
  assert hashlib.sha256(item['text'].encode()).hexdigest()==item['script_sha256']
  with wave.open(io.BytesIO(data)) as w:assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,24000) and abs(w.getnframes()/24000-item['duration_seconds'])<.001
  name='house/guide/'+item['id']+'.wav';key=f'demos/zind-house-000/{sha}/{name}'
  c.put_object(bucket,key,io.BytesIO(data),len(data),content_type='audio/wav',metadata={'sha256':sha},num_parallel_uploads=1)
  response=c.get_object(bucket,key)
  try:assert hashlib.sha256(response.read()).hexdigest()==sha
  finally:response.close();response.release_conn()
  doc['assets'][name]={'key':key,'sha256':sha,'bytes':len(data),'content_type':'audio/wav'};clips[item['id']]=item|{'asset':name}
 assert len(clips)==(22 if a.manifest_sha==V2 else 16)
 rooms={r['room_id']:r for r in batch['rooms']};guide=[]
 for room in batch['rooms']:
  for visual in room.get('visual_sources',[]):
   capture=next(x for x in house['captures'] if x['id']==visual['capture_id']);assert capture['roomId']==room['room_id'] and capture['sha256']==visual['sha256']
 for marker in batch['markers']:
  room=rooms[marker['room_id']];source_room=next(r for r in house['rooms'] if r['id']==marker['room_id']);assert room['source_label']==source_room['label']
  for locale in ['en','vi']:
   clip=clips[marker['tracks'][locale]];assert clip['locale']==locale and clip['text']==room.get('narration',{}).get(locale,{}).get('transcript',room['description'][locale])
   guide.append({k:clip[k] for k in ['locale','sha256','duration_seconds','source','provider','model','voice','script_sha256','asset']}|{'capture_id':marker['capture_id'],'room_id':marker['room_id'],'script':clip['text'],'description':room['description'][locale],'source_id':room['source_id'],'description_version':room.get('description_version',1),'narration_version':room.get('narration_version',1)})
 doc['guide']=guide;doc['guide_manifest_sha256']=a.manifest_sha;doc['total_bytes']=sum(x['bytes'] for x in doc['assets'].values())
 a.output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(doc,f,ensure_ascii=False)
 print(json.dumps({'unique_wavs':len(clips),'capture_locale_bindings':len(guide),'selected_markers':len(expected),'source_and_minio_readback_sha_verified':True,'new_paid_calls':0,'guide_manifest_sha256':a.manifest_sha}))
if __name__=='__main__':main()
