"""Actual browser+renderer, using only synthetic owner fixtures from API QA."""
import json
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'tests/exports/evidence'

def main():
    fixture=json.loads(Path(os.environ['QA_OUTPUT_DIR'],'browser-private.json').read_text())
    cli=os.environ['VIDEO_EXPORT_HYPERFRAMES']
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','DISPLAY'}};env['PYTHONPATH']=str(ROOT)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    name='export-'+uuid.uuid4().hex[:8]
    def browser(*args):
        output=subprocess.run([shutil.which('playwright-cli'),'-s='+name,'--raw',*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=300)
        if output.returncode or '### Error' in output.stdout:raise RuntimeError(output.stdout+output.stderr)
        return output.stdout
    restart_only=os.environ.get('QA_RESTART_ONLY')=='1'
    scripts=['restart.js','restart.js'] if restart_only else ['browser.js']
    result_path=EVIDENCE/('restart-browser.log' if restart_only else 'browser.log')
    results=[]
    try:
        browser('open','about:blank')
        with (EVIDENCE/'browser-server.log').open('a') as log:
            for script in scripts:
                server=subprocess.Popen([sys.executable,'tests/exports/local_server.py','--root',fixture['root'],'--port',str(port),'--cli',cli],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=log,text=True)
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(server.stdout,selectors.EVENT_READ)
                        if not selector.select(timeout=25) or server.stdout.readline().strip()!='EXPORT_TEST_READY':raise RuntimeError('QA server failed startup')
                    source=(ROOT/'tests/exports'/script).read_text()
                    for key,value in {'__BASE__':f'http://127.0.0.1:{port}','__COOKIE__':fixture['cookie'],'__TOUR__':fixture['tour_id'],'__JOB__':fixture['job_id']}.items():source=source.replace(key,value)
                    result=browser('run-code',source)
                    if '\"pass\":true' not in result and '\"pass\": true' not in result:raise RuntimeError(result)
                    results.append(result.rstrip())
                finally:
                    server.terminate()
                    try:server.wait(timeout=15)
                    except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
                    server.stdout.close()
        result_path.write_text('\n'.join(results)+'\n')
        print('PASS '+('actual server restart + private MP4 playback' if restart_only else 'real export UI + two MP4 playback')+', no provider')
    finally:browser('close')

if __name__=='__main__':main()
