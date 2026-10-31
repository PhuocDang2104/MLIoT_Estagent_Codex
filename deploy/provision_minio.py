"""Provision only the dedicated Estagent bucket/user. Credentials come from env files."""
import argparse
import io
import json
import uuid
import os
from minio import Minio, MinioAdmin
from minio.credentials import StaticProvider
from minio.error import S3Error
import urllib3


def clients():
    env = os.environ
    endpoint = env['MINIO_ENDPOINT']
    http = urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=20), retries=False)
    credentials = StaticProvider(env['MINIO_ROOT_USER'], env['MINIO_ROOT_PASSWORD'])
    return (Minio(endpoint, credentials=credentials, secure=False, http_client=http),
            MinioAdmin(endpoint=endpoint, credentials=credentials, secure=False, http_client=http))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-quota-before-rollout', action='store_true', help='Temporarily lower this unused bucket quota; only before application rollout')
    args = parser.parse_args()
    env = os.environ
    bucket = env['MINIO_BUCKET']
    if bucket != 'estagent-media' or env['MINIO_SECURE'] != '0':
        raise ValueError('Require the dedicated private-network Estagent bucket')
    if env['MINIO_ACCESS_KEY'] == env['MINIO_ROOT_USER']:
        raise ValueError('Application must use a separate account')
    root, admin = clients()
    if not root.bucket_exists(bucket):
        root.make_bucket(bucket)
    # This command is deliberate operator setup; rerun uses the same external env.
    admin.user_add(env['MINIO_ACCESS_KEY'], env['MINIO_SECRET_KEY'])
    policy = {'Version':'2012-10-17','Statement':[
        {'Effect':'Allow','Action':['s3:GetBucketLocation','s3:ListBucket'],
         'Resource':[f'arn:aws:s3:::{bucket}']},
        {'Effect':'Allow','Action':['s3:GetObject','s3:PutObject','s3:DeleteObject',
          's3:AbortMultipartUpload','s3:ListMultipartUploadParts'],
         'Resource':[f'arn:aws:s3:::{bucket}/*']}]}
    admin.policy_add('estagent-media-app', policy=policy)
    admin.policy_set('estagent-media-app', user=env['MINIO_ACCESS_KEY'])
    admin.bucket_quota_set(bucket, 536870912)
    quota = json.loads(admin.bucket_quota_get(bucket))
    if quota.get('quota') != 536870912 or quota.get('quotatype') != 'hard':
        raise ValueError('Bucket hard quota verification failed')
    if args.verify_quota_before_rollout:
        key = 'studio/assets/' + uuid.uuid4().hex
        app = Minio(env['MINIO_ENDPOINT'], access_key=env['MINIO_ACCESS_KEY'],
                    secret_key=env['MINIO_SECRET_KEY'], secure=False,
                    http_client=urllib3.PoolManager(timeout=urllib3.Timeout(connect=5, read=20), retries=False))
        existing = 'studio/assets/' + uuid.uuid4().hex
        app.put_object(bucket, existing, io.BytesIO(b'existing fixture'), 16)
        try:
            admin.bucket_quota_set(bucket, 1)
            response = app.get_object(bucket, existing)
            try:
                if response.read() != b'existing fixture':
                    raise ValueError('Existing object unreadable at full quota')
            finally:
                response.close()
                response.release_conn()
            try:
                app.put_object(bucket, key, io.BytesIO(b'quota probe'), 11)
            except S3Error as error:
                if error.code != 'XMinioAdminBucketQuotaExceeded':
                    raise ValueError('Unexpected quota rejection code') from None
            else:
                app.remove_object(bucket, key)
                raise ValueError('Hard quota did not reject new write')
        finally:
            admin.bucket_quota_set(bucket, 536870912)
            app.remove_object(bucket, existing)  # Only the disposable fixture created above.
        print('PASS hard quota rejects new app write while existing media stays readable; restored 536870912')
    print('PASS dedicated bucket, separate app policy, hard quota 536870912')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Upstream admin error bodies can contain account/request data; never print them.
        raise SystemExit('MinIO provisioning failed: ' + type(error).__name__) from None
