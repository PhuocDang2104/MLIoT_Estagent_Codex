# Rollback: preserve tours and recorded audio

`346a0ba40051f3e5b739a318e86549a26730d439` predates recorded audio. Its
`server/tours/models.py` already has an Audio field, but accepts only
`status=unavailable`, `source=none`, `narration=null`, `music=null` (omitted
fields use those defaults). It forbids unknown Audio fields. The old edit and
publish routes validate the entire stored Manifest: newly attached `ready` or
`partial` / `user_uploaded` audio makes those operations fail 422. The old
server also lacks published WAV routes and its Viewer cannot play these tracks.
The existence of an `audio` key or an unused `audio_assets` table alone is not
evidence of incompatibility.

## Gate before changing the image

1. Keep the current accepted image/env/release SHA and volume. Remove live key
   for a keyless rollback; do not run an older image with an unguarded real key.
2. Drain public writes and in-flight requests, then stop only the Estagent app.
   Preserve the shared Caddy/other applications. No old/new process may write
   the same SQLite volume concurrently. An edge 503 during maintenance is safer
   than taking writes after the compatibility snapshot.
3. On the dedicated Estagent volume, make an SQLite backup via Python's SQLite
   backup API, not a raw copy of a potentially active DB/WAL. Keep backup outside
   the mounted application data tree, mode 0600, directory 0700. Back up tour
   media and Studio/checkpoint stores too; the tour DB alone is not a full backup.
4. Run from the new accepted source tree (stdlib Python only):

   ```bash
   python3 deploy/rollback_preflight.py \
     --tour-db /private/operator-backups/rollback-check/tours.sqlite \
     --target-commit 346a0ba40051f3e5b739a318e86549a26730d439
   ```

   `0`: recorded-audio compatibility check passed. `1`: stored draft or published
   snapshot is incompatible. `2`: target/input cannot be checked. Both nonzero
   exits block this downgrade. Output reports counts only, not IDs or content.
   Use a stable standalone backup with no `-wal`, `-shm`, `-journal` sidecars;
   the checker uses immutable/read-only SQLite and never opens production for writing.
   It refuses unknown/short target SHAs instead of importing or executing arbitrary
   Git source. This policy checks the known audio extension, not every application
   schema, filesystem permission or runtime dependency.
5. Rehearse the exact target image on a **separate writable copy** of all backup
   data, isolated loopback port/network and keyless env. Verify existing visual
   snapshots/assets, owner draft read/edit/review/publish and SQLite integrity.
   Synthetic new writes belong only in this disposable copy. A passing count
   check is necessary but does not replace this candidate behavior check.
6. Only after compatibility and candidate checks pass, switch the single app
   image against the preserved original volume. Verify health, HTTPS, snapshots
   and assets. Keep rollback metadata and every backup. If the target fails,
   roll forward to the prior accepted image with the same original volume.

### SQLite backup example (operator substitutes actual dedicated paths)

Run only after draining/stopping writes; this command creates a new backup file,
never restores or overwrites an existing one. The backup path must not be in the
live data tree. Do not use another application's database or volume.

```python
import os
from pathlib import Path
import sqlite3

source = Path('/dedicated-estagent-volume/tours/tours.sqlite')
backup = Path('/private/operator-backups/rollback-check/tours.sqlite')
backup.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
fd = os.open(backup, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
os.close(fd)
with sqlite3.connect(source.absolute().as_uri() + '?mode=ro', uri=True) as src:
    with sqlite3.connect(backup) as dst:
        src.backup(dst)
        assert dst.execute('PRAGMA quick_check').fetchone() == ('ok',)
```

## If recorded audio exists

Refuse rollback to `346a0ba`. Use a separately reviewed image that retains the
new audio schema, storage and media routes, or roll forward with a focused fix.
Never clear audio refs, edit immutable snapshots, restore an older DB over new
data, remove `audio_assets`, or delete media to make the compatibility check pass.
Studio data remains preserved even if an old image cannot serve its routes;
restoring Studio availability requires an image that supports that workflow.

This tooling changes no production data, makes no network/provider calls, adds
no dependency, and does not grant deployment permission. New Codex-assisted code
uses Python stdlib/SQLite against reviewed repo source; H0 remains unconfirmed.

Validation: `python3 -m pytest tests/deploy/test_rollback_preflight.py -q`:
22 passed. Tests inspect the pinned target Audio class via AST (no source execution),
exercise real SQLite drafts/snapshots, strict refusal/defaults, sidecar/wrong-input
handling, CLI exit codes/redaction, and unchanged DB hash/mtime/directory contents.
No production compatibility check or candidate container rollout was performed by
this lane. The target-source test needs the pinned commit available in Git history.
