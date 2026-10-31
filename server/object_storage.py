"""Private, explicit MinIO media adapter. Existing local storage stays caller-owned."""
from contextlib import suppress
from dataclasses import dataclass
import hashlib
import io
import re
import threading
from urllib.parse import urlsplit

from fastapi import HTTPException
from starlette.responses import Response, StreamingResponse


KEY = re.compile(r'(?:tours/(?:images|thumbnails)/[a-f0-9]{32}\.jpg|'
                 r'tours/audio/[a-f0-9]{32}\.wav|studio/assets/[a-f0-9]{32})')
MISSING = {'NoSuchKey', 'NoSuchObject'}


def _key(key):
    if not isinstance(key, str) or not KEY.fullmatch(key):
        raise ValueError('Object key must use a server-generated media namespace and ID')
    return key


def _error(error):
    from minio.error import S3Error
    return HTTPException(404 if isinstance(error, S3Error) and error.code in MISSING else 503,
                         'Media unavailable' if isinstance(error, S3Error) and error.code in MISSING
                         else 'Object storage unavailable')


def _close(response):
    try:
        with suppress(Exception):
            response.close()
    finally:
        with suppress(Exception):
            response.release_conn()


@dataclass(frozen=True)
class ObjectInfo:
    size: int
    content_type: str
    sha256: str | None


class ObjectResponse(StreamingResponse):
    """Close SDK response even if cancelled before body iteration starts."""
    def __init__(self, source, *, length, status_code, media_type, headers):
        self.source = source
        def chunks():
            remaining = length
            try:
                while remaining:
                    chunk = source.read(min(64 * 1024, remaining))
                    if not chunk:
                        raise HTTPException(503, 'Object storage interrupted')
                    remaining -= len(chunk)
                    yield chunk
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(503, 'Object storage interrupted') from None
        super().__init__(chunks(), status_code=status_code, media_type=media_type, headers=headers)

    async def __call__(self, scope, receive, send):
        try:
            await super().__call__(scope, receive, send)
        finally:
            _close(self.source)


class MinioStorage:
    def __init__(self, client, bucket):
        self.client, self.bucket = client, bucket
        # Deployment is one app process; serialize check+put within this instance.
        self._write_lock = threading.RLock()

    def stat(self, key):
        _key(key)
        try:
            result = self.client.stat_object(self.bucket, key)
            metadata = {str(k).lower(): v for k, v in (result.metadata or {}).items()}
            return ObjectInfo(result.size, result.content_type or 'application/octet-stream',
                              metadata.get('x-amz-meta-sha256'))
        except Exception as error:
            raise _error(error) from None

    def get_bytes(self, key):
        _key(key)
        response = None
        try:
            response = self.client.get_object(self.bucket, key)
            return response.read()
        except Exception as error:
            raise _error(error) from None
        finally:
            if response is not None:
                _close(response)

    def put_bytes(self, key, data, content_type):
        _key(key)
        if not isinstance(data, bytes):
            raise ValueError('Object data must be validated bytes')
        if content_type not in {'image/jpeg', 'image/png', 'image/webp', 'audio/wav', 'model/gltf-binary'}:
            raise ValueError('Unsupported media content type')
        digest = hashlib.sha256(data).hexdigest()
        with self._write_lock:
            try:
                existing = self.stat(key)
            except HTTPException as error:
                if error.status_code != 404:
                    raise
            else:
                same = existing.size == len(data) and existing.content_type == content_type
                # Legacy objects without checksum metadata are compared by bytes.
                same = same and (existing.sha256 == digest if existing.sha256 else self.get_bytes(key) == data)
                if not same:
                    raise HTTPException(409, 'Immutable media object already exists with different content')
                return existing
            try:
                self.client.put_object(self.bucket, key, io.BytesIO(data), len(data),
                                       content_type=content_type, metadata={'sha256': digest},
                                       num_parallel_uploads=1)
            except Exception as error:
                raise _error(error) from None
        return ObjectInfo(len(data), content_type, digest)

    def remove(self, key):
        """Explicit orphan cleanup only; caller must prove no snapshot references it."""
        _key(key)
        try:
            self.client.remove_object(self.bucket, key)
        except Exception as error:
            raise _error(error) from None

    def response(self, key, *, range_header=None):
        info = self.stat(key)
        headers = {'Accept-Ranges': 'bytes', 'Cache-Control': 'no-store',
                   'X-Content-Type-Options': 'nosniff'}
        start, length, status = 0, info.size, 200
        if range_header is not None:
            match = re.fullmatch(r'bytes=([0-9]{0,20})-([0-9]{0,20})', range_header)
            if not match or not any(match.groups()) or info.size == 0:
                return Response(status_code=416, headers={**headers, 'Content-Range': f'bytes */{info.size}'})
            left, right = match.groups()
            if left:
                start = int(left)
                end = min(int(right), info.size - 1) if right else info.size - 1
            else:
                count = int(right)
                start, end = max(0, info.size - count), info.size - 1
            if start >= info.size or start > end:
                return Response(status_code=416, headers={**headers, 'Content-Range': f'bytes */{info.size}'})
            length, status = end - start + 1, 206
            headers['Content-Range'] = f'bytes {start}-{end}/{info.size}'
        headers['Content-Length'] = str(length)
        if length == 0:
            return Response(content=b'', media_type=info.content_type, headers=headers)
        try:
            source = self.client.get_object(self.bucket, _key(key), offset=start, length=length)
        except Exception as error:
            raise _error(error) from None
        return ObjectResponse(source, length=length, status_code=status,
                              media_type=info.content_type, headers=headers)


def create_object_storage(env, *, client_factory=None):
    backend = env.get('MEDIA_STORAGE_BACKEND', 'local')
    if backend == 'local':
        return None
    if backend != 'minio':
        raise ValueError('MEDIA_STORAGE_BACKEND must be local or minio')
    for name in ('MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'MINIO_BUCKET'):
        value = env.get(name)
        if not isinstance(value, str) or not value.strip() or value != value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError(f'{name} must be configured without surrounding whitespace/control characters')
    endpoint = env['MINIO_ENDPOINT']
    try:
        parsed = urlsplit('//' + endpoint)
        if (not parsed.hostname or parsed.username is not None or parsed.password is not None
                or parsed.path or parsed.query or parsed.fragment or parsed.port == 0
                or any(c.isspace() for c in endpoint) or '://' in endpoint):
            raise ValueError()
        if not re.fullmatch(r'(?:[A-Za-z0-9.-]+|\[[0-9A-Fa-f:]+\])(?::[0-9]+)?', endpoint):
            raise ValueError()
    except ValueError:
        raise ValueError('MINIO_ENDPOINT must be a host with optional port, no URL/path/credentials') from None
    bucket = env['MINIO_BUCKET']
    if (not re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket)
            or '..' in bucket or '.-' in bucket or '-.' in bucket
            or re.fullmatch(r'[0-9]+(?:\.[0-9]+){3}', bucket)):
        raise ValueError('MINIO_BUCKET must be a valid private bucket name')
    secure = env.get('MINIO_SECURE', '1')
    if secure not in {'0', '1'}:
        raise ValueError('MINIO_SECURE must be 0 or 1')
    if client_factory is None:
        from minio import Minio
        import urllib3
        def client_factory(*args, **kwargs):
            return Minio(*args, **kwargs, http_client=urllib3.PoolManager(
                timeout=urllib3.Timeout(connect=5, read=20), retries=False))
    try:
        client = client_factory(endpoint, access_key=env['MINIO_ACCESS_KEY'],
                                secret_key=env['MINIO_SECRET_KEY'], secure=secure == '1')
        if not client.bucket_exists(bucket):
            raise ValueError('MINIO_BUCKET must already exist; operator must create a private bucket')
    except ValueError:
        raise ValueError('MinIO configuration or bucket is invalid') from None
    except Exception:
        raise ValueError('MinIO storage is unavailable; refusing local fallback') from None
    return MinioStorage(client, bucket)
