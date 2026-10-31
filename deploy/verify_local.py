"""Native QA of committed assistant + current deploy tooling, not a production release.

Uses temporary SQLite, synthetic input and a fake key only. Full smoke never sends
a valid model request. Existing application tests mock model/network calls.
"""
import io
from contextlib import closing
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]


def main():
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    blob = subprocess.check_output([
        'git', 'archive', sha, 'server/assistant', 'server/tours', 'server/creator', 'web', 'tests/ai',
    ], cwd=ROOT)
    print(f'Application snapshot: {sha}; deploy tooling: current uncommitted files', flush=True)
    with tempfile.TemporaryDirectory(prefix='estagent-native-qa-') as directory:
        stage = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(blob)) as archive:
            archive.extractall(stage, filter='data')
        shutil.copytree(ROOT / 'deploy', stage / 'deploy', ignore=shutil.ignore_patterns(
            'evidence', '__pycache__', '.env', '.env.*', 'runtime', '*.tar', '*.tar.gz'))
        env = {k: v for k, v in os.environ.items() if not k.startswith((
            'OPENAI_', 'ASSISTANT_', 'TOUR_', 'STUDIO_', 'CREATOR_', 'ESTAGENT_', 'LANGCHAIN_', 'LANGSMITH_'))}
        env.update({
            'PYTHONDONTWRITEBYTECODE': '1', 'NO_PROXY': '127.0.0.1,localhost',
            'ASSISTANT_DB': str(stage / 'data' / 'checkpoints.sqlite'),
            'ASSISTANT_ORIGIN': 'https://estagent-weld.vercel.app',
            'ASSISTANT_REQUIRED_FIELDS': 'address,area,bedrooms',
            'OPENAI_MODEL_TEXT': 'gpt-6.1-sol',
            'OPENAI_MODEL_REALTIME': 'gpt-realtime-2.1',
            'OPENAI_MODEL_TRANSCRIBE': 'gpt-transcribe',
        })

        def command(*args, expected=0, environment=None):
            result = subprocess.run([sys.executable, *args], cwd=stage, env=environment or env,
                                    capture_output=True, text=True, timeout=90)
            if result.returncode != expected:
                # All child input in this harness is synthetic. No live keys inherited.
                print(result.stdout, result.stderr, flush=True)
                raise RuntimeError(f'{args[0]} returned {result.returncode}, expected {expected}')
            return result.stdout.strip()

        command('deploy/entrypoint.py', '--check-config', expected=2)
        print('PASS config: missing key rejected without starting runtime', flush=True)
        preview = {**env, 'OPENAI_API_KEY': '', 'ESTAGENT_KEYLESS_PREVIEW': '1'}
        command('deploy/entrypoint.py', '--check-config', environment=preview)
        command('deploy/entrypoint.py', '--check-config', expected=2,
                environment={**preview, 'OPENAI_API_KEY': 'fixture-secret'})
        print('PASS keyless preview: explicit opt-in accepted; nonempty key rejected', flush=True)
        configured = {**env, 'OPENAI_API_KEY': 'local-fixture-not-a-real-key'}
        print(command('deploy/entrypoint.py', '--check-config', environment=configured), flush=True)
        for name, value in [('OPENAI_API_KEY', '   '), ('ASSISTANT_ORIGIN', 'http://invalid.example'),
                            ('ASSISTANT_REQUIRED_FIELDS', 'not-an-app-field')]:
            command('deploy/entrypoint.py', '--check-config', expected=2,
                    environment={**configured, name: value})
        print('PASS config: blank key, non-HTTPS origin, unknown field rejected', flush=True)

        for label, runtime in [('unconfigured', env), ('configured-fixture', configured)]:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            base = f'http://127.0.0.1:{port}'
            with (stage / f'{label}.log').open('w') as output:
                process = subprocess.Popen([
                    sys.executable, '-m', 'uvicorn', 'server.assistant.app:app',
                    '--host', '127.0.0.1', '--port', str(port), '--workers', '1',
                    '--no-proxy-headers', '--no-access-log',
                ], cwd=stage, env=runtime, stdout=output, stderr=subprocess.STDOUT)
                try:
                    deadline = time.monotonic() + 20
                    while True:
                        try:
                            with urlopen(base + '/api/assistant/state', timeout=1) as response:
                                if response.status == 200:
                                    break
                        except (URLError, TimeoutError, OSError):
                            if time.monotonic() >= deadline:
                                raise RuntimeError(f'{label}: native HTTP startup timed out')
                            threading.Event().wait(0.1)
                    flags = ['--allow-unconfigured'] if label == 'unconfigured' else []
                    print(label + ': ' + command('deploy/smoke.py', '--base-url', base,
                          '--origin', env['ASSISTANT_ORIGIN'], '--check-static', *flags,
                          environment=runtime), flush=True)
                    print(command('deploy/smoke.py', '--base-url', base, '--health-only',
                                  *flags, environment=runtime), flush=True)
                    if label == 'unconfigured':
                        command('deploy/smoke.py', '--base-url', base, '--health-only', expected=1)
                        print('PASS health: unconfigured server fails production health', flush=True)
                finally:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
            with closing(sqlite3.connect(env['ASSISTANT_DB'])) as db:
                if db.execute('PRAGMA quick_check').fetchone() != ('ok',):
                    raise RuntimeError('SQLite integrity check failed')
        print('PASS native restart: SQLite reopens and passes quick_check', flush=True)
        print(command('-m', 'pytest', '-q', 'tests/ai/test_assistant.py'), flush=True)
    print('LOCAL QA PASS; Docker build/volume/TLS/live OpenAI NOT verified', flush=True)


if __name__ == '__main__':
    main()
