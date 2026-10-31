"""Import the two already-generated, authorized intro WAVs; never call a provider."""
import argparse,hashlib,io,json,os,wave
from pathlib import Path
from minio import Minio
import urllib3

def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--catalog',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 env=os.environ
 if env['MINIO_BUCKET']!='estagent-media':raise ValueError('Wrong bucket')
 c=Minio(env['MINIO_ENDPOINT'],access_key=env['MINIO_ACCESS_KEY'],secret_key=env['MINIO_SECRET_KEY'],secure=env['MINIO_SECURE']=='1',http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5,read=30),retries=False))
 doc=json.loads(a.catalog.read_text());sources=json.loads((a.source/'sources.json').read_text());intro=[]
 if {s['locale'] for s in sources}!={'en','vi'} or len(sources)!=2:raise ValueError('Exactly two approved intro samples required')
 for s in sources:
  data=(a.source/(s['locale']+'.wav')).read_bytes();sha=hashlib.sha256(data).hexdigest()
  if sha!=s['sha256'] or len(data)!=s['bytes']:raise ValueError('WAV source SHA mismatch')
  with wave.open(io.BytesIO(data)) as w:
   if (w.getnchannels(),w.getsampwidth(),w.getframerate())!=(1,2,24000) or abs(w.getnframes()/w.getframerate()-s['duration_seconds'])>.001:raise ValueError('WAV format mismatch')
  name='house/intro/'+s['locale']+'.wav';key=f'demos/zind-house-000/{sha}/{name}'
  c.put_object(env['MINIO_BUCKET'],key,io.BytesIO(data),len(data),content_type='audio/wav',metadata={'sha256':sha},num_parallel_uploads=1)
  response=c.get_object(env['MINIO_BUCKET'],key)
  try:
   if hashlib.sha256(response.read()).hexdigest()!=sha:raise ValueError('MinIO readback mismatch')
  finally:response.close();response.release_conn()
  doc['assets'][name]={'key':key,'sha256':sha,'bytes':len(data),'content_type':'audio/wav'}
  intro.append(s|{'asset':name})
 doc['intro']=intro;doc['total_bytes']=sum(x['bytes'] for x in doc['assets'].values())
 a.output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w') as f:json.dump(doc,f,ensure_ascii=False)
 print(json.dumps({'intro_locales':['en','vi'],'readback_sha_verified':True,'new_paid_calls':0,'room_specific':False}))
if __name__=='__main__':main()
