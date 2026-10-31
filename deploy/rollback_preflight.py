"""Read-only recorded-audio compatibility gate for a known legacy rollback target.

Input must be a standalone SQLite backup, never a live database with a WAL.
This does not execute target source, restore data, or certify whole-app compatibility.
"""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3


LEGACY_TARGET = '346a0ba40051f3e5b739a318e86549a26730d439'
LEGACY_AUDIO = {'status': 'unavailable', 'source': 'none', 'narration': None, 'music': None}


def _legacy_audio(doc):
    if not isinstance(doc, dict) or doc.get('schema_version', 'checkpoint-tour-v1') != 'checkpoint-tour-v1':
        return False
    # Manifest.audio and all four old Audio fields had defaults. Explicit null Audio
    # and unknown fields were rejected by the old strict Pydantic model.
    audio = doc.get('audio', {})
    return (isinstance(audio, dict) and not (audio.keys() - LEGACY_AUDIO.keys())
            and all(audio.get(key, default) == default for key, default in LEGACY_AUDIO.items()))


def inspect(tour_db, target_commit):
    if target_commit != LEGACY_TARGET:
        raise ValueError('Unknown target commit: no reviewed rollback policy available')
    path = Path(tour_db).absolute()
    if path.is_symlink() or not path.is_file():
        raise ValueError('Require an existing standalone tour database backup, not a symlink')
    if any(Path(str(path) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
        raise ValueError('Require a standalone SQLite backup without WAL/journal sidecars')
    before = path.stat()
    counts = {}
    # immutable avoids SQLite creating/changing SHM sidecars. It is safe only for
    # a stable standalone backup; never point this at a writer's live database.
    uri = path.as_uri() + '?mode=ro&immutable=1'
    with closing(sqlite3.connect(uri, uri=True)) as db:
        db.execute('PRAGMA query_only=ON')
        if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('SQLite integrity check failed')
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'drafts', 'published'} <= tables:
            raise ValueError('Not a recognized tour database: drafts/published tables required')
        for table in ('drafts', 'published'):
            if 'doc' not in {r[1] for r in db.execute(f'PRAGMA table_info({table})')}:
                raise ValueError('Not a recognized tour database: manifest column missing')
            total = incompatible = 0
            for (raw,) in db.execute(f'SELECT doc FROM {table}'):
                total += 1
                try:
                    compatible = _legacy_audio(json.loads(raw))
                except (ValueError, TypeError, RecursionError):
                    compatible = False
                incompatible += not compatible
            counts[table] = {'total': total, 'incompatible': incompatible}
    after = path.stat()
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('Backup changed while checking; create a stable SQLite backup again')
    if any(Path(str(path) + suffix).exists() for suffix in ('-wal', '-shm', '-journal')):
        raise ValueError('Backup acquired SQLite sidecars while checking; refuse unstable input')
    return {'target_commit': target_commit, 'check': 'legacy_recorded_audio_compatibility',
            'compatible': not any(v['incompatible'] for v in counts.values()), 'manifests': counts}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tour-db', required=True, type=Path, help='stable SQLite backup snapshot')
    parser.add_argument('--target-commit', required=True, help='full reviewed legacy target SHA')
    args = parser.parse_args(argv)
    try:
        result = inspect(args.tour_db, args.target_commit)
    except (ValueError, OSError, sqlite3.Error) as error:
        # Never include SQL errors, DB paths, titles, owners or document contents.
        reason = str(error) if isinstance(error, ValueError) else 'Cannot read a valid SQLite backup'
        print(json.dumps({'compatible': False, 'error': reason}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['compatible'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
