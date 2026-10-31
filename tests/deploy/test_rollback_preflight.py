import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('rollback_preflight', ROOT / 'deploy/rollback_preflight.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def database(tmp_path, drafts=(), published=()):
    path = tmp_path / 'backup.sqlite'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE drafts(id TEXT PRIMARY KEY, doc TEXT NOT NULL)')
        db.execute('CREATE TABLE published(id TEXT PRIMARY KEY, doc TEXT NOT NULL)')
        for table, docs in (('drafts', drafts), ('published', published)):
            db.executemany(f'INSERT INTO {table} VALUES(?,?)',
                           [(str(i), json.dumps(doc)) for i, doc in enumerate(docs)])
    return path


def check(path):
    return guard.inspect(path, guard.LEGACY_TARGET)


def test_old_audio_defaults_and_empty_database_are_compatible(tmp_path):
    path = database(tmp_path)
    assert check(path)['compatible']
    path.unlink()
    path = database(tmp_path, ({}, {'audio': {}}, {'audio': guard.LEGACY_AUDIO}),
                    ({'audio': {'status': 'unavailable'}},))
    assert check(path)['compatible']


def test_policy_matches_exact_reviewed_target_source():
    # Inspect the pinned historical source as text; never import/exec target code.
    source = subprocess.check_output(['git', 'show',
        f'{guard.LEGACY_TARGET}:server/tours/models.py'], cwd=ROOT, text=True)
    tree = ast.parse(source)
    audio = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Audio')
    fields = {node.target.id: ast.literal_eval(node.value) for node in audio.body
              if isinstance(node, ast.AnnAssign)}
    assert fields == guard.LEGACY_AUDIO
    annotations = {node.target.id: ast.unparse(node.annotation) for node in audio.body
                   if isinstance(node, ast.AnnAssign)}
    assert annotations == {'status': "Literal['unavailable']", 'narration': 'None',
                           'music': 'None', 'source': "Literal['none']"}


@pytest.mark.parametrize('table', ('drafts', 'published'))
@pytest.mark.parametrize('audio', (
    {'status': 'ready', 'source': 'user_uploaded', 'narration': [{'track': {'asset_id': 'a'*32}}]},
    {'status': 'partial', 'source': 'user_uploaded', 'music': {'asset_id': 'b'*32}},
    {'narration': []}, {'source': 'user_uploaded'}, {'unknown': None}, None,
))
def test_both_drafts_and_snapshots_refuse_new_or_invalid_audio(tmp_path, table, audio):
    path = database(tmp_path, **{table: ({'audio': audio},)})
    result = check(path)
    assert result['compatible'] is False
    assert result['manifests'][table] == {'total': 1, 'incompatible': 1}


def test_manifest_schema_or_malformed_json_fails_closed(tmp_path):
    path = database(tmp_path, ({'schema_version': 'future'}, []))
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO published VALUES('bad','not JSON')")
    assert check(path)['manifests'] == {
        'drafts': {'total': 2, 'incompatible': 2}, 'published': {'total': 1, 'incompatible': 1}}


def test_no_database_or_sidecar_write(tmp_path):
    path = database(tmp_path, ({'audio': guard.LEGACY_AUDIO},))
    original = hashlib.sha256(path.read_bytes()).hexdigest()
    before = path.stat()
    files = sorted(p.name for p in tmp_path.iterdir())
    assert check(path)['compatible']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == original
    assert path.stat().st_mtime_ns == before.st_mtime_ns
    assert sorted(p.name for p in tmp_path.iterdir()) == files


@pytest.mark.parametrize('suffix', ('-wal', '-shm', '-journal'))
def test_sidecar_input_rejected_without_changes(tmp_path, suffix):
    path = database(tmp_path)
    sidecar = Path(str(path) + suffix)
    sidecar.write_bytes(b'sensitive synthetic WAL data')
    with pytest.raises(ValueError, match='standalone'):
        check(path)
    assert sidecar.read_bytes() == b'sensitive synthetic WAL data'


def test_unknown_target_does_not_read_or_create_database(tmp_path):
    missing = tmp_path / 'missing.sqlite'
    with pytest.raises(ValueError, match='Unknown target'):
        guard.inspect(missing, '346a0ba')
    assert not missing.exists()


def test_wrong_database_missing_file_and_symlink_rejected(tmp_path):
    missing = tmp_path / 'missing.sqlite'
    with pytest.raises(ValueError):
        check(missing)
    assert not missing.exists()
    with sqlite3.connect(missing) as db:
        db.execute('CREATE TABLE unrelated(secret TEXT)')
    with pytest.raises(ValueError, match='recognized'):
        check(missing)
    link = tmp_path / 'link.sqlite'
    link.symlink_to(missing)
    with pytest.raises(ValueError, match='symlink'):
        check(link)


def test_cli_exit_and_redaction(tmp_path, capsys):
    path = database(tmp_path, ({'title': 'PRIVATE TITLE', 'audio': {'status': 'ready'}},))
    args = ['--tour-db', str(path), '--target-commit', guard.LEGACY_TARGET]
    assert guard.main(args) == 1
    output = capsys.readouterr().out
    assert 'PRIVATE TITLE' not in output and str(path) not in output
    assert json.loads(output)['manifests']['drafts']['incompatible'] == 1
    assert guard.main(['--tour-db', str(tmp_path / 'missing'), '--target-commit', guard.LEGACY_TARGET]) == 2
