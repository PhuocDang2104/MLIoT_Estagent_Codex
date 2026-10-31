import asyncio
import hashlib
import io
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from minio.error import S3Error

from server.object_storage import create_object_storage, MinioStorage


KEY = 'tours/audio/' + 'a' * 32 + '.wav'
ENV = {'MEDIA_STORAGE_BACKEND': 'minio', 'MINIO_ENDPOINT': 'minio-private:9000',
       'MINIO_SECURE': '0', 'MINIO_ACCESS_KEY': 'synthetic-access',
       'MINIO_SECRET_KEY': 'synthetic-secret', 'MINIO_BUCKET': 'estagent-media'}


def s3error(code):
    return S3Error(response=None, code=code, message='PRIVATE provider body and credentials',
                   resource='/private', request_id='request', host_id='host')


class Source(io.BytesIO):
    def __init__(self, data, fail=False):
        super().__init__(data)
        self.closes = self.releases = 0
        self.fail = fail

    def read(self, *args):
        if self.fail:
            raise OSError('PRIVATE SDK URL and credentials')
        return super().read(*args)

    def close(self):
        self.closes += 1
        super().close()

    def release_conn(self):
        self.releases += 1


class Client:
    def __init__(self):
        self.objects = {}
        self.responses = []
        self.puts = 0
        self.exists = True
        self.failure = None
        self.fail_read = False

    def bucket_exists(self, bucket):
        if self.failure:
            raise self.failure
        return self.exists

    def stat_object(self, bucket, key):
        if self.failure:
            raise self.failure
        if key not in self.objects:
            raise s3error('NoSuchKey')
        data, mime, metadata = self.objects[key]
        return SimpleNamespace(size=len(data), content_type=mime, metadata=metadata)

    def get_object(self, bucket, key, offset=0, length=0):
        self.stat_object(bucket, key)
        data = self.objects[key][0]
        response = Source(data[offset:offset + length] if length else data[offset:], self.fail_read)
        self.responses.append(response)
        return response

    def put_object(self, bucket, key, source, length, **kwargs):
        if self.failure:
            raise self.failure
        self.puts += 1
        self.objects[key] = (source.read(), kwargs['content_type'],
                             {'x-amz-meta-sha256': kwargs['metadata']['sha256']})

    def remove_object(self, bucket, key):
        if self.failure:
            raise self.failure
        self.objects.pop(key, None)


@pytest.fixture
def storage():
    client = Client()
    adapter = create_object_storage(ENV, client_factory=lambda *a, **k: client)
    return adapter, client


def test_local_default_does_not_create_client():
    def forbidden(*args, **kwargs):
        raise AssertionError('No remote client in local mode')
    assert create_object_storage({}, client_factory=forbidden) is None


@pytest.mark.parametrize('name,value', (
    ('MEDIA_STORAGE_BACKEND', 's3'), ('MINIO_ENDPOINT', 'https://example.com'),
    ('MINIO_ENDPOINT', 'user:password@example.com:9000'), ('MINIO_ENDPOINT', 'host:9000/path'),
    ('MINIO_ENDPOINT', 'host:99999'), ('MINIO_ENDPOINT', 'host:0'),
    ('MINIO_ENDPOINT', 'host?private=1'), ('MINIO_ENDPOINT', 'host\n'),
    ('MINIO_ACCESS_KEY', ''), ('MINIO_SECRET_KEY', ' '), ('MINIO_BUCKET', 'PUBLIC'),
    ('MINIO_BUCKET', 'a..b'), ('MINIO_BUCKET', '127.0.0.1'), ('MINIO_SECURE', 'true'),
))
def test_invalid_config_rejected_before_network(name, value):
    def forbidden(*args, **kwargs):
        raise AssertionError('Unexpected client construction')
    with pytest.raises(ValueError):
        create_object_storage({**ENV, name: value}, client_factory=forbidden)


def test_constructor_uses_server_config_and_no_bucket_mutation():
    seen = []
    client = Client()
    def factory(*args, **kwargs):
        seen.append((args, kwargs))
        return client
    assert isinstance(create_object_storage(ENV, client_factory=factory), MinioStorage)
    assert seen == [(('minio-private:9000',), {'access_key': 'synthetic-access',
        'secret_key': 'synthetic-secret', 'secure': False})]
    client.exists = False
    with pytest.raises(ValueError):
        create_object_storage(ENV, client_factory=factory)
    client.failure = s3error('AccessDenied')
    with pytest.raises(ValueError) as exc:
        create_object_storage(ENV, client_factory=factory)
    assert 'PRIVATE' not in str(exc.value)


def test_write_once_idempotency_and_metadata(storage):
    adapter, client = storage
    first = adapter.put_bytes(KEY, b'0123456789', 'audio/wav')
    assert first.sha256 == hashlib.sha256(b'0123456789').hexdigest()
    assert adapter.put_bytes(KEY, b'0123456789', 'audio/wav') == first
    assert client.puts == 1
    with pytest.raises(HTTPException) as exc:
        adapter.put_bytes(KEY, b'new bytes', 'audio/wav')
    assert exc.value.status_code == 409
    assert adapter.get_bytes(KEY) == b'0123456789'
    assert client.responses[-1].closes == client.responses[-1].releases == 1
    adapter.remove(KEY)
    with pytest.raises(HTTPException) as exc:
        adapter.stat(KEY)
    assert exc.value.status_code == 404


def test_existing_object_without_metadata_compares_bytes(storage):
    adapter, client = storage
    client.objects[KEY] = (b'hello', 'audio/wav', {})
    assert adapter.put_bytes(KEY, b'hello', 'audio/wav').size == 5
    assert client.puts == 0
    with pytest.raises(HTTPException) as exc:
        adapter.put_bytes(KEY, b'other', 'audio/wav')
    assert exc.value.status_code == 409


@pytest.mark.parametrize('key', ('../../private', 'https://example.com/media',
                               'tours/audio/wrong.wav', 'studio/assets/' + 'A'*32))
def test_keys_cannot_be_user_paths_or_urls(storage, key):
    adapter, _ = storage
    for method in (adapter.stat, adapter.get_bytes, adapter.remove):
        with pytest.raises(ValueError):
            method(key)


@pytest.mark.parametrize('error,status', ((s3error('NoSuchKey'), 404),
    (s3error('NoSuchBucket'), 503), (s3error('AccessDenied'), 503),
    (OSError('PRIVATE endpoint/secret'), 503)))
def test_failures_sanitized_no_fallback(storage, error, status):
    adapter, client = storage
    client.failure = error
    for operation in (lambda: adapter.stat(KEY), lambda: adapter.get_bytes(KEY),
                      lambda: adapter.put_bytes(KEY, b'x', 'audio/wav'), lambda: adapter.remove(KEY)):
        with pytest.raises(HTTPException) as exc:
            operation()
        assert exc.value.status_code == status and 'PRIVATE' not in exc.value.detail


@pytest.mark.parametrize('range_header,status,body,content_range', (
    (None, 200, b'0123456789', None), ('bytes=2-5', 206, b'2345', 'bytes 2-5/10'),
    ('bytes=7-', 206, b'789', 'bytes 7-9/10'), ('bytes=-3', 206, b'789', 'bytes 7-9/10'),
    ('bytes=8-99', 206, b'89', 'bytes 8-9/10'), ('bytes=-99', 206, b'0123456789', 'bytes 0-9/10'),
    ('bytes=10-', 416, b'', 'bytes */10'), ('bytes=-0', 416, b'', 'bytes */10'),
    ('bytes=5-2', 416, b'', 'bytes */10'), ('bytes=0-1,4-5', 416, b'', 'bytes */10'),
    ('bytes=-', 416, b'', 'bytes */10'), ('bytes='+'9'*500+'-', 416, b'', 'bytes */10'),
))
def test_http_range_and_stream_cleanup(storage, range_header, status, body, content_range):
    adapter, client = storage
    adapter.put_bytes(KEY, b'0123456789', 'audio/wav')
    app = FastAPI()
    @app.get('/media')
    def media(request: Request):
        return adapter.response(KEY, range_header=request.headers.get('range'))
    with TestClient(app) as browser:
        result = browser.get('/media', headers={'Range': range_header} if range_header is not None else {})
    assert (result.status_code, result.content) == (status, body)
    assert result.headers.get('content-range') == content_range
    if status != 416:
        assert int(result.headers['content-length']) == len(body)
        assert client.responses[-1].closes == client.responses[-1].releases == 1


def test_get_read_error_closes_connection(storage):
    adapter, client = storage
    adapter.put_bytes(KEY, b'hello', 'audio/wav')
    client.fail_read = True
    with pytest.raises(HTTPException) as exc:
        adapter.get_bytes(KEY)
    assert exc.value.status_code == 503 and 'PRIVATE' not in exc.value.detail
    assert client.responses[-1].closes == client.responses[-1].releases == 1


def test_cancel_before_iteration_closes_sdk_stream(storage):
    adapter, client = storage
    adapter.put_bytes(KEY, b'hello', 'audio/wav')
    response = adapter.response(KEY)
    async def cancelled(*args):
        raise asyncio.CancelledError()
    async def run():
        with pytest.raises(asyncio.CancelledError):
            await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, cancelled, cancelled)
    asyncio.run(run())
    assert client.responses[-1].closes == client.responses[-1].releases == 1


def test_zero_size_and_read_error_during_http_stream(storage):
    adapter, client = storage
    adapter.put_bytes(KEY, b'', 'audio/wav')
    assert adapter.response(KEY).body == b''
    assert adapter.response(KEY, range_header='bytes=0-').status_code == 416
    client.objects[KEY] = (b'hello', 'audio/wav', {})
    client.fail_read = True
    response = adapter.response(KEY)
    async def send(message):
        pass
    async def run():
        with pytest.raises(HTTPException) as exc:
            await response({'type': 'http', 'asgi': {'spec_version': '2.4'}}, send, send)
        assert exc.value.status_code == 503 and 'PRIVATE' not in exc.value.detail
    asyncio.run(run())
    assert client.responses[-1].closes == client.responses[-1].releases == 1
