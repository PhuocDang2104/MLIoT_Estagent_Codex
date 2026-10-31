"""Real private MinIO smoke using synthetic bytes only; no publish or provider calls."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import uuid
from minio import Minio
from minio.error import S3Error
import urllib3


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--read-only', action='store_true')
    args=parser.parse_args()
    env=os.environ
    http=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5,read=20),retries=False)
    client=Minio(env['MINIO_ENDPOINT'],access_key=env['MINIO_ACCESS_KEY'],secret_key=env['MINIO_SECRET_KEY'],secure=False,http_client=http)
    bucket=env['MINIO_BUCKET']; data=b'Estagent synthetic MinIO persistence and Range fixture\n'*128
    if args.read_only:
        state=json.loads(args.state.read_text()); key=state['key']
    else:
        key='studio/assets/'+uuid.uuid4().hex
        client.put_object(bucket,key,io.BytesIO(data),len(data),content_type='application/octet-stream')
        state={'key':key,'sha256':hashlib.sha256(data).hexdigest()}
        args.state.write_text(json.dumps(state))
    info=client.stat_object(bucket,key)
    assert info.size==len(data), 'object size'
    for offset,length in [(0,len(data)),(3,17)]:
        response=client.get_object(bucket,key,offset=offset,length=length)
        try:
            content=response.read()
            assert content==data[offset:offset+length], 'read bytes'
            if offset: assert response.status==206, 'Range status'
            else: assert hashlib.sha256(content).hexdigest()==state['sha256'], 'SHA digest'
        finally:
            response.close(); response.release_conn()
    anonymous=http.request('GET','http://'+env['MINIO_ENDPOINT']+'/'+bucket+'/'+key)
    assert anonymous.status==403, 'anonymous access'
    try:
        client.make_bucket('estagent-denied-'+uuid.uuid4().hex)
    except S3Error as error:
        assert error.code=='AccessDenied', 'cross-bucket denial code'
    else:
        raise AssertionError('App account can create an unauthorized bucket')
    print('PASS MinIO put/stat/get SHA/Range206/private403/app bucket isolation' if not args.read_only else 'PASS MinIO restart preserved SHA/Range/private denial')


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        reason = str(error) if isinstance(error, AssertionError) else type(error).__name__
        raise SystemExit('MinIO smoke failed: '+reason) from None
