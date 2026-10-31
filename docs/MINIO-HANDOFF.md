# Private MinIO adapter — integration handoff

Branch `feature/minio-adapter`, base `5498fdc`. Owned files are
`server/object_storage.py`, `tests/ai/test_object_storage.py`, this handoff only.
No application route, requirement, container, production instance or data migration
is changed here. Integrator approved runtime dependency `minio==7.2.20` and owns
adding it to requirements/release packaging.

## Stable interface

```python
from server.object_storage import create_object_storage
storage = create_object_storage(env)  # None for default/local; MinioStorage for minio
info = storage.put_bytes(key, validated_bytes, 'audio/wav')
info = storage.stat(key)             # ObjectInfo(size, content_type, sha256)
payload = storage.get_bytes(key)     # closes/releases SDK connection
response = storage.response(key, range_header=request.headers.get('range'))
storage.remove(key)                  # explicit orphan cleanup only
```

Construct one shared adapter at startup and pass it to tour/Studio stores.
Sync SDK calls belong in sync routes/worker threads; do not block async handlers
on network operations. Caller retains ownership/session/Origin checks, decoding,
request/storage quotas, credit declarations and DB transactions. **Publish existence
checks must call `stat`, not `response`**, to avoid opening an unconsumed stream.
Methods return sanitized HTTPException 404 only for missing object; auth/bucket/
network/service failures become 503. Invalid server keys/content types are programmer
ValueErrors. No raw SDK exception body, endpoint, credentials or metadata is logged.

Only exact server key namespaces are accepted:

- `tours/images/{32_lower_hex}.jpg`
- `tours/thumbnails/{32_lower_hex}.jpg`
- `tours/audio/{32_lower_hex}.wav`
- `studio/assets/{32_lower_hex}`

There are no browser credentials, public URLs, presigned URLs, bucket creation,
policy changes, asset enumeration, automatic migration or local fallback here.
`local` returns None so the caller retains its existing local backend explicitly.
When `minio` is selected, errors never change backend to local. Integrator must
separately decide how existing local images/audio/SQLite Studio blobs remain readable
and how their location is tracked during migration. Do not silently orphan old data.

## Configuration and operator setup

```dotenv
MEDIA_STORAGE_BACKEND=minio
MINIO_ENDPOINT=estagent-minio:9000
MINIO_SECURE=0
MINIO_ACCESS_KEY=<dedicated-server-access-key>
MINIO_SECRET_KEY=<dedicated-server-secret>
MINIO_BUCKET=estagent-media
```

Default backend is `local`. Endpoint accepts only host[:port], not a URL, path,
credentials/query/fragment; secure is exactly `0`/`1` (defaults `1`). Credentials
and bucket are required in MinIO mode. Config/initial bucket connectivity errors
fail startup without a fallback. Constructor checks `bucket_exists`; it does not
change or independently audit bucket policies. **Operator must provision an
existing private bucket and dedicated scoped credentials**, verify anonymous
access is denied, and keep MinIO/console on the private Docker network. HTTP (`0`)
is intended only for that dedicated private network; TLS retains SDK certificate
verification. No shared project credentials, bucket or volume should be reused.
SDK HTTP pool uses 5s connect/20s read timeout, retries disabled. SDK is thread-safe
within one process; use one app worker as the existing deployment requires.

`put_bytes` validates keys/types and records SHA-256 metadata. Within one adapter
instance a lock serializes check+put. Same key/size/content type/checksum returns
existing metadata; different bytes/type fail 409, never overwrite. Existing objects
without SHA metadata are read and compared before accepting an idempotent put.
This is **not a cross-process conditional write guarantee**: SDK's public put API
has no conditional-create parameter. Keep one writer, random IDs and bucket access
restricted to this app; use reviewed versioning/object lock if stronger protection
is required. `remove` is only for caller-proven unreferenced orphan objects; never
delete published references to recover space or bypass rollback checks.

`response` supports full200 and one byte range206 (bounded, open-ended or suffix),
with Accept-Ranges/Content-Length/Content-Range and416 for invalid/multi/unsatisfiable
ranges. SDK close+release runs in ASGI response finally, including cancellation
before first body chunk. Read failures after headers interrupt the stream with a
sanitized error; an already-started HTTP200/206 cannot become503. Content-Length
allows clients to detect truncation. `get_bytes` reads all bytes; caller's existing
upload caps must constrain media, especially Studio provider reads. No arbitrary
large-object download endpoint is authorized by this module.

## Validation and source declaration

`uv run --quiet --python 3.13 --with pytest --with minio==7.2.20
--with-requirements server/assistant/requirements.txt python -m pytest
tests/ai/test_object_storage.py -q`: **41 passed**. Tests use real FastAPI/ASGI HTTP
responses and actual pinned SDK S3Error types, injecting a fake MinIO client only.
They cover config/no remote local mode, sanitized failures, immutable/idempotent
writes, allowed namespaces, connection cleanup on success/read error/cancellation,
and full/range/416 responses. No external object server or paid service is called.
Initial fixture used the wrong positional S3Error constructor; it was corrected
to the pinned SDK keyword signature before the passing run.

Official reference used: [MinIO Python API v7.2.20](https://github.com/minio/minio-py/blob/7.2.20/docs/API.md),
constructor, bucket_exists, put_object, stat_object, get_object and remove_object.
New Codex-assisted implementation on existing FastAPI/Starlette/urllib3 and Python
stdlib; MinIO Python SDK is Apache-2.0. No reference project code/media copied.
H0 unconfirmed; no claim that this code was built inside contest hours. Root owns
VM bucket/private-access checks, migration, restart/persistence and production QA.
