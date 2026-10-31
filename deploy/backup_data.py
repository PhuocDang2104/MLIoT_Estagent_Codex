"""Offline backup of the dedicated Estagent volume. Stop assistant before running.

Uses SQLite backup API (including committed WAL), preserves media, never deletes
or restores source data. Run as UID 10001 against /data in the app container.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3


def backup(root, label):
    root = root.resolve(strict=True)
    if root == Path(root.anchor) or not root.is_dir():
        raise ValueError('Require a dedicated data directory')
    if not label or len(label) > 80 or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in label):
        raise ValueError('Invalid backup label')
    output = root / 'backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'-'+label)
    source = []
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if relative.parts[0] == 'backups':
            continue
        if path.is_symlink():
            raise ValueError('Refuse symlink in dedicated data volume')
        if path.is_file() and not path.name.endswith(('-wal', '-shm', '.lock')):
            source.append((path,relative))
    if not source:
        raise ValueError('Refuse empty data backup')
    output.mkdir(parents=True,exist_ok=False)
    manifest = {}
    for path, relative in source:
        target = output / relative
        target.parent.mkdir(parents=True,exist_ok=True)
        with path.open('rb') as stream:
            is_sqlite = stream.read(16) == b'SQLite format 3\x00'
        if is_sqlite:
            with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True)) as db, closing(sqlite3.connect(target)) as copy:
                db.backup(copy)
                if copy.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise ValueError('Backup integrity check failed')
        else:
            shutil.copy2(path,target)
        target.chmod(0o600)
        digest = hashlib.sha256()
        with target.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024), b''):
                digest.update(chunk)
        manifest[str(relative)] = digest.hexdigest()
    (output/'BACKUP.json').write_text(json.dumps({'label':label,'files':manifest},indent=2)+'\n',encoding='utf8')
    (output/'BACKUP.json').chmod(0o600)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--label',required=True)
    args = parser.parse_args()
    result = backup(args.root,args.label)
    print('BACKUP READY:', result.name)
