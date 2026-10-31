"""Real browser/local API/SQLite, synthetic SDK; optional existing live WAV playback."""
import argparse
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'tests/narration/evidence'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--live-dir');args=parser.parse_args()
    cli=shutil.which('playwright-cli')
    if not cli:raise RuntimeError('playwright-cli and Chromium required')
    session='narration-'+uuid.uuid4().hex[:8]
    child_env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL','DISPLAY'}};child_env['PYTHONPATH']=str(ROOT)
    with socket.socket() as socket_:socket_.bind(('127.0.0.1',0));port=socket_.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    def browser(*argv):
        r=subprocess.run([cli,f'-s={session}','--raw',*argv],cwd=ROOT,env=child_env,capture_output=True,text=True,timeout=120)
        if r.returncode or '### Error' in r.stdout:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout
    EVIDENCE.mkdir(exist_ok=True)
    scenarios=[('browser.js',[]),('browser-keyless.js',['--keyless'])]
    if args.live_dir:scenarios.append(('browser-live.js',['--live-dir',args.live_dir]))
    with (EVIDENCE/'browser.log').open('w') as log,(EVIDENCE/'server.log').open('w') as server_log:
        try:
            browser('open','about:blank')
            for script,flags in scenarios:
                with tempfile.TemporaryDirectory(prefix='narration-browser-') as temp:
                    server=subprocess.Popen([sys.executable,'-m','tests.narration.local_server','--root',temp,'--port',str(port),*flags],cwd=ROOT,env=child_env,stdout=subprocess.PIPE,stderr=server_log,text=True)
                    try:
                        with selectors.DefaultSelector() as selector:
                            selector.register(server.stdout,selectors.EVENT_READ)
                            if not selector.select(timeout=25) or server.stdout.readline().strip()!='NARRATION_READY':raise RuntimeError('Server startup failed; inspect server.log')
                        source=(ROOT/'tests/narration'/script).read_text().replace('__BASE_URL__',base)
                        result=browser('run-code',source)
                        if '"pass":true' not in result and '"pass": true' not in result:raise RuntimeError(result)
                        log.write(script+': '+result+'\n');log.flush();print('PASS '+script,flush=True)
                    finally:
                        server.terminate()
                        try:server.wait(timeout=10)
                        except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
                        server.stdout.close()
        finally:browser('close')
if __name__=='__main__':main()
