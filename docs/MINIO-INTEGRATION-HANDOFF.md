# MinIO media route integration — deployment handoff

Branch `feature/minio-integration`, base `879caf20abae586befcf596d4526070b2d7732ba`.
Includes adapter cherry-pick `415568d` (same source as approved `df19dd1`). Owns
server route/Store/Creator wiring and `tests/ai/test_minio_integration.py` only;
no web changes, credentials, main merge/push, VM provisioning or deployment.

## Media placement and compatibility

`create_app` constructs exactly one `create_object_storage(env)` instance and
shares it through `app.state.object_storage`, legacy tour handlers and the
optional Creator/Store constructor parameters. `MEDIA_STORAGE_BACKEND=local`
stays the default. Explicit MinIO uses the adapter's validated server-only
configuration and refuses startup fallback when the bucket/client is unavailable.

New remote media keys are server generated:

- `tours/images/<hex32>.jpg`, `tours/thumbnails/<hex32>.jpg` — normalized image pair.
- `tours/audio/<hex32>.wav` — normalized uploaded PCM WAV.
- `studio/assets/<hex32>` — uploaded images/floorplan/music and generated TTS/GLB.

Tour SQLite adds `media_storage(kind,id,backend)`; Studio adds
`media_refs(asset,backend,object_key)`. These internal tables are not part of the
public manifest. No existing rows, files or BLOBs are migrated/deleted. Existing
unmarked legacy files and Studio BLOBs remain readable even when MinIO is enabled.
New remote tour media creates no JPEG/WAV copy locally. New remote Studio assets
keep the existing metadata row with an **empty BLOB** plus a media ref: input,
TTS and GLB bytes are not duplicated in SQLite.

Exact additive marker schemas (no media bytes or credentials in these tables):

```sql
-- <TOUR_DATA_DIR>/tours.sqlite; kind is image or audio.
CREATE TABLE IF NOT EXISTS media_storage (
    kind TEXT, id TEXT, backend TEXT NOT NULL, PRIMARY KEY(kind,id)
);
-- <STUDIO_DATA_DIR>/creator.sqlite; asset references assets.id.
CREATE TABLE IF NOT EXISTS media_refs (
    asset TEXT PRIMARY KEY, backend TEXT NOT NULL, object_key TEXT NOT NULL
);
```

Remote rows use `backend='minio'`; keys for tour image/thumbnail/audio are derived
from kind/id, whereas Studio stores its generated `studio/assets/<id>` key.
Rollback preflight must inspect both tables for any MinIO rows (if the tables
exist), independently of manifest audio status or current backend environment.
An image-only remote tour has `audio.status=unavailable` and still requires a
MinIO-aware reader. Studio new rows have `length(assets.content)=0`; marker
presence, rather than empty content alone, is the backend authority. Missing
tables in a pre-MinIO DB mean no registered remote refs for that store.

Fallback is explicitly per asset: a marked remote object uses MinIO only. Missing
credentials, a disabled remote backend, object absence or an outage cannot select
a local file/BLOB instead. Deduped uploads retain their original backend and ID;
old local inputs remain local when replayed after switching the deployment.

## Access, publication and failure handling

HTTP URLs and owner/session checks remain unchanged. No bucket URL/key/credentials
are exposed to browsers. Public routes check membership of the immutable snapshot
before serving the private object. Owner-only routes remain owner checked; bare
object keys have no public API route. This does not introduce login/authentication.

Both legacy and Studio publish paths verify each referenced remote object using
`stat`, never a response/get stream that would remain unconsumed. Studio also
checks registered size/MIME/checksum where supplied by the adapter. Legacy publish
checks the image and thumbnail pair plus all referenced audio. Audio attachment
validation also uses stat. Normal reads use the adapter's managed streaming
response; Range headers reach MinIO for legacy WAV and all Studio media. Legacy
filesystem WAV retains FileResponse Range handling; legacy Studio BLOB responses
gain single-range 206/416 handling. Midstream transport interruption can abort an
already-started HTTP response; it cannot change headers to a new JSON error.

Metadata registration is transactional. If a newly generated media ID fails partway
through object puts or DB registration, the route/Store attempts to remove only
the newly attempted keys. Existing/deduped media is never deleted by this path.
Cleanup is best effort: a failed remove emits a generic warning requesting operator
reconciliation, without IDs, object URLs or credentials. A process crash/ambiguous
network commit can leave an orphan: there is no atomic distributed transaction or
automatic bucket garbage collection. Existing Studio delete behavior may also
leave an unreferenced remote object; no broad deletion policy is introduced here.

Existing upload storage admission remains active before writes when configured.
Remote uploads reserve conservative space for **local metadata**, rather than
charging the external payload to the local media volume. Store-generated audio/
models also reserve local metadata before put/registration. Local mode keeps
payload reservations and legacy behavior. Remote bucket capacity is an operator
MinIO quota, not an SDK/client memory counter or a USD cap. Upload request body,
decode and concurrency limits remain required independently.

## Deployment NEED

Deploy owns packaging/config/provisioning:

1. Include `server/object_storage.py` and all changed modules; pinned SDK MinIO
   7.2.20 is already in the approved requirements baseline. Keep one app process.
2. Provision a **dedicated MinIO instance on the existing Estagent VM** (no new cloud resource), private bucket,
   least-privilege application access key and server-enforced quota (planned
   512 MiB). Do not reuse another project's bucket/keys or publish bucket policy.
3. Pass `MEDIA_STORAGE_BACKEND=minio`, `MINIO_ENDPOINT` as host/port without URL,
   `MINIO_SECURE=0|1`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` via
   the private runtime env only. Endpoint must be reachable by the app. Verify TLS
   or private transport/network controls as appropriate; no environment values are
   included in this handoff.
4. Retain local persistent SQLite/files and their backups. Back up metadata and
   object bucket together; snapshots now reference both stores. This lane has
   not run a production migration or copied any existing media.
5. Test real VM upload/dedupe/private denial/publish/public Range/restart and
   stat/read failure recovery before calling the deployment complete. Verify a
   full bucket rejects new writes while existing media remains readable.
6. Rollback must retain a MinIO-aware binary/config and bucket availability for
   newly remote assets. A pre-MinIO release cannot read new remote asset markers
   or empty Studio BLOBs; flipping the backend to local does not migrate them.
   Do not delete bucket/object/metadata data to roll back.

The Studio upload's existing raw image metadata/EXIF behavior is retained; storage
placement itself does not add redaction or change source/privacy policy.

## Verification and declaration

Tests use actual FastAPI HTTP/owner checks, LangGraph and SQLite plus the real
MinIO adapter against its in-memory SDK client fixture. No real S3 network,
credentials, property data, human narration, paid provider or VM is involved.
Synthetic PNG/WAV/provider/triangle GLB fixtures are reused from this repository.

Seven new integration tests cover: remote-only image/thumb/WAV; dedupe; private
denial and public snapshot membership; Range 206/416 and stream cleanup; stat-only
publish/attach; old filesystem/BLOB compatibility; explicit no fallback for marked
remote media; restart/outage recovery; actual Studio generation writing input,
music/TTS/GLB without BLOB duplicates; missing-object publish rejection; rollback
cleanup after three DB registration failures and a second-image-object failure.

First new test run reported two mismatched assertions (expected 404 without a
cookie, while existing routes correctly return 401). Tests were corrected to
assert 401 first, then create a different session and assert 404. App security
behavior was preserved. Final targeted run: **7 passed** (2.33 seconds).
Final complete backend regression: **149 passed** (10.77 seconds), one existing
LangChain deprecation warning. Required `scripts/gate.sh ai --strict`: compile,
pytest and fixture/schema contract **PASS**, `GATE OK (ai)`.
Code is Codex-assisted, based on existing repo/approved adapter and pinned SDK;
no copied external application source or new dependency. H0 remains unconfirmed;
no claim of writing inside competition hours. VM/private bucket/real S3/browser
verification belongs to Deploy; this lane does not claim it.
