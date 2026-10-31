"""Run the integrated Creator/Viewer through a real isolated local server."""
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=Path('/private/tmp/estagent-demo-ux-integration')


def main():
    cli=shutil.which('playwright-cli')
    if not cli:raise RuntimeError('playwright-cli is required')
    EVIDENCE.mkdir(exist_ok=True)
    session='demo-integration-'+uuid.uuid4().hex[:8]
    env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL','DISPLAY'}}
    env['PYTHONPATH']=str(ROOT)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    def browser(*args):
        result=subprocess.run([cli,f'-s={session}','--raw',*args],cwd=ROOT,env=env,capture_output=True,text=True,timeout=180)
        if result.returncode or '### Error' in result.stdout:raise RuntimeError(result.stdout+result.stderr)
        return result.stdout
    with tempfile.TemporaryDirectory(prefix='demo-ux-integration-') as temp,(EVIDENCE/'server.log').open('w') as log:
        # app.py exports a default app at import time. Its narration lease needs
        # a separate data root from the explicit test app below.
        env['ASSISTANT_DB']=temp+'/import/assistant.sqlite'
        for i,color in enumerate(['#273c59','#5e7765','#d39157'],1):
            Image.new('RGB',(1200,800),color).save(f'{temp}/{i}.png')
        server=subprocess.Popen([sys.executable,'tests/audio/local_server.py','--db',temp+'/runtime/assistant.sqlite','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=log,text=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(server.stdout,selectors.EVENT_READ)
                if not selector.select(timeout=30) or server.stdout.readline().strip()!='AUDIO_TEST_READY':raise RuntimeError('Server startup failed: '+str(EVIDENCE/'server.log'))
            browser('open','about:blank')
            source=(ROOT/'tests/demo-ux/integration-browser.js').read_text()
            for key,value in {'__BASE_URL__':f'http://127.0.0.1:{port}','__EVIDENCE_DIR__':str(EVIDENCE),'__IMAGE_ONE__':temp+'/1.png','__IMAGE_TWO__':temp+'/2.png','__IMAGE_THREE__':temp+'/3.png'}.items():source=source.replace(key,value)
            result=browser('run-code',source)
            if '"pass": true' not in result and '"pass":true' not in result:raise RuntimeError(result)
            (EVIDENCE/'browser.json').write_text(result)
            print(result)
        finally:
            server.terminate()
            try:server.wait(timeout=15)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
            server.stdout.close()
            browser('close')


if __name__=='__main__':main()
