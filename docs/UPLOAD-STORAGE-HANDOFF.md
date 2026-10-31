# Upload storage admission — integrator handoff

Branch `feature/upload-storage`, base `5498fdc`. Owns `server/storage.py`, upload
routes in `server/tours/api.py`, `server/tours/audio.py`, `server/creator/api.py`,
storage install in `server/assistant/app.py`, and isolated storage tests.

## Behavior

Explicit opt-in `STORAGE_LIMITS_ENABLED=1` adds one shared process lock and disk
admission policy for legacy JPEG/PNG/WebP image uploads (normalized JPEG texture
plus thumbnail), normalized PCM WAV upload, Studio images/floorplan and WAV music.
Actual validated/encoded payload lengths are known before persistence. The lock
spans the payload writes and their SQLite commit; any raised error releases it.
Legacy image/WAV write failures roll back metadata and remove newly created files.
Existing dedupe is checked first: exact same-owner/project replays can succeed
when storage is full and do not create another payload. New sessions/projects
cannot reset the shared capacity; each newly persisted copy consumes real space.

Each admission recursively counts **all regular file logical lengths** below the
dedicated root, including assistant/tour/Studio SQLite files, WAL/journals, orphan
payloads, and backups. No cookie/counter/DB reset can erase that measured usage.
Symlinked roots/ancestors, storage paths outside the root and symlink entries in
the tree are rejected. Filesystem scan/free-space failure denies uploads with
sanitized HTTP 507. Quota/headroom rejection also returns 507 and leaves existing
assets/public snapshots readable. No data migration, deletion or cleanup runs.

Reserved growth is `3 * verified_payload_bytes + 65536`: conservative room for
payload, SQLite BLOB/WAL amplification, pages and metadata. Filesystem free bytes
must remain above configured headroom **after** that reservation. This is an
upload admission threshold, **not a hard OS/filesystem quota**. Directory metadata,
allocation/block overhead, unrelated processes, API text/session metadata and
background generation writes are not bounded by this mechanism. Their existing
files count on the next upload scan, but concurrent non-upload writes can consume
space independently. Use one process/worker and retain OS monitoring; multiple
replicas/processes require external quota coordination. Large trees increase scan
latency. The public no-auth app still needs rate/concurrency/body bounds before
buffering; this storage guard runs after validated upload decode, not before body
buffering. It is neither authentication, retention policy nor paid API budget.

## Configuration / NEED for integrator

Root handles deploy/example/entrypoint/packaging changes (outside this card):

```dotenv
STORAGE_LIMITS_ENABLED=1
STORAGE_LIMITS_ROOT=/data
STORAGE_LIMITS_MAX_BYTES=536870912
STORAGE_LIMITS_MIN_FREE_BYTES=1073741824
```

All numbers are explicit positive integers. Root must be absolute, dedicated and
contain `ASSISTANT_DB`, tour data and Studio data (e.g. `/data/checkpoints.sqlite`,
`/data/tours`, `/data/studio`). Flags other than 0/1 fail config. Defaults remain
disabled for backwards compatibility and fixtures; live deployments must opt in
operationally. Presence of a key does not automatically enable this storage guard.
Factory installs it with actual resolved storage paths; helper
`server.storage.validate_storage(env)` validates all config, creates/checks the
root and returns the guard without reserving or writing an upload. Entry point
can call it for `--check-config` without starting an OpenAI client.

Add `server/storage.py` to Docker COPY/context and release/QA archive allowlists.
Keep `/data` on the existing persistent project-only volume; no new volume or
database migration. Backups inside `/data` intentionally count toward the cap.
Guard disable does not erase files/counters; rolling forward rescans existing use.
The existing API limits must include image/WAV/Studio uploads and be enabled on
keyless production too to bound buffered request concurrency.

## Evidence and declaration

`uv run --quiet --python 3.13 --with pytest --with jsonschema --with-requirements
server/assistant/requirements.txt python -m pytest tests/ai/test_storage_limits.py -q`
uses real FastAPI requests, local SQLite, actual PNG/WAV decode, file writes and
temporary storage. Coverage: four upload families, full-cap dedupe/read, rotated
sessions, empty project after rejection, published tour survives full quota and
app restart, all file/WAL/backup accounting, headroom failure, failed write cleanup
and retry, invalid config/root boundaries, and compressed-vs-normalized image size.
Two guard instances for the same root serialize reservations across threads and
remeasure changed capacity after waiting. Final full regression: **101 passed**
(`tests/ai`, 7.40 seconds), including **14 storage tests**; one pre-existing
LangChain deprecation warning. Diff whitespace check passed. No core/build/browser
claim is made by this backend-only lane.
No paid calls, network, production credentials, extra runtime dependencies or real
property/audio inputs. Synthetic fixture helpers reused from this repository.
Code written with Codex on 2026-10-31; H0 unknown, no competition-time claim.
