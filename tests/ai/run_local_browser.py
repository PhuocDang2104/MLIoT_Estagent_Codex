"""Run browser → real HTTP → LangGraph → SQLite without paid provider calls.

Requires installed playwright-cli + browser and existing assistant dependencies.
Uses a dedicated browser session, fresh temporary DB, three backend processes.
Never loads .env.local; no browser API route fulfillment or model network calls.
"""
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'tests/ai/evidence'


def main():
    cli = shutil.which('playwright-cli')
    if not cli:
        raise RuntimeError('Install/provide playwright-cli before running this check')
    EVIDENCE.mkdir(exist_ok=True)
    session = f'assistant-local-{uuid.uuid4().hex[:8]}'
    # No application secrets/tracing are passed to either subprocess.
    child_env = {k: v for k, v in os.environ.items()
                 if k in {'PATH', 'HOME', 'TMPDIR', 'LANG', 'LC_ALL', 'DISPLAY'}}
    child_env['PYTHONPATH'] = str(ROOT)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    base = f'http://127.0.0.1:{port}'

    def browser(*args):
        result = subprocess.run([cli, f'-s={session}', '--raw', *args], cwd=ROOT,
                                env=child_env, capture_output=True, text=True, timeout=90)
        # CLI may report run-code errors in stdout even when exit status is zero.
        if result.returncode or '### Error' in result.stdout:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout

    with tempfile.TemporaryDirectory(prefix='estagent-browser-') as temp, \
            (EVIDENCE / 'local-browser.log').open('w') as log, \
            (EVIDENCE / 'local-server.log').open('w') as server_log:
        log.write('Scope: actual HTTP/LangGraph/SQLite; finite model fixture; no paid API calls.\n')
        log.write(f'Base commit: {subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()}\n')
        try:
            browser('open', 'about:blank')
            for mode, script in [('fixture', 'local_browser_flow.js'),
                                 ('fixture', 'local_browser_restart.js'),
                                 ('missing-key', 'local_browser_no_key.js')]:
                server = subprocess.Popen(
                    [sys.executable, 'tests/ai/local_fixture_server.py', '--db', f'{temp}/checkpoints.sqlite',
                     '--port', str(port), '--mode', mode], cwd=ROOT, env=child_env,
                    stdout=subprocess.PIPE, stderr=server_log, text=True)
                try:
                    # Wait for a single startup event, not process/status polling.
                    with selectors.DefaultSelector() as selector:
                        selector.register(server.stdout, selectors.EVENT_READ)
                        if not selector.select(timeout=20) or server.stdout.readline().strip() != 'LOCAL_FIXTURE_READY':
                            raise RuntimeError('Local server did not become ready; inspect local-server.log')
                    source = (ROOT / 'tests/ai' / script).read_text().replace('__BASE_URL__', base)
                    result = browser('run-code', source)
                    if '"pass": true' not in result and '"pass":true' not in result:
                        raise RuntimeError(f'No passing browser result for {script}: {result}')
                    log.write(f'{script}: {result}\n')
                    log.flush()
                    print(f'PASS {script}', flush=True)
                finally:
                    server.terminate()
                    try:
                        server.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        server.kill()
                        server.wait(timeout=5)
                    server.stdout.close()
            log.write('PASS: all three phases; database removed with the temporary test directory.\n')
        finally:
            browser('close')


if __name__ == '__main__':
    main()
