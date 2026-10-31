"""Real browser and HTTP; isolated local SQLite, generated images, no paid calls."""
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'tests/integration/evidence'

def main():
    cli=shutil.which('playwright-cli')
    if not cli:raise RuntimeError('playwright-cli is required')
    EVIDENCE.mkdir(exist_ok=True)
    session='product-sync-'+uuid.uuid4().hex[:8]
    child_env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL','DISPLAY'}}
    child_env['PYTHONPATH']=str(ROOT)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    def browser(*args):
        r=subprocess.run([cli,f'-s={session}','--raw',*args],cwd=ROOT,env=child_env,capture_output=True,text=True,timeout=120)
        if r.returncode or '### Error' in r.stdout:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout
    # Runtime artifacts stay under the assigned worktree and are ignored by Git.
    runtime=ROOT/'projects/integration/work';runtime.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='browser-',dir=runtime) as temp, (EVIDENCE/'browser.log').open('w') as log, (EVIDENCE/'server.log').open('w') as server_log:
        for n,color in [(1,'#bdd9d0'),(2,'#dbbb92')]:
            im=Image.new('RGB',(1200,400),color);d=ImageDraw.Draw(im)
            for x in range(0,1200,100):d.rectangle((x,80,x+40,320),fill=('#384f68' if x%200 else '#f7e8a5'))
            d.text((30,25),f'SYNTHETIC CHECKPOINT {n} - NOT A PROPERTY',fill='black');im.save(f'{temp}/{n}.png')
        log.write('Real local HTTP/SQLite/image decoder/WebGL. Synthetic images. No OpenAI calls.\n')
        try:
            browser('open','about:blank')
            for mode,script in [('missing-key','browser_flow.js'),('fixture','browser_restart.js'),('missing-key','browser_counts.js')]:
                server=subprocess.Popen([sys.executable,'tests/integration/local_server.py','--db',f'{temp}/assistant.sqlite','--port',str(port),'--mode',mode],cwd=ROOT,env=child_env,stdout=subprocess.PIPE,stderr=server_log,text=True)
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(server.stdout,selectors.EVENT_READ)
                        if not selector.select(timeout=25) or server.stdout.readline().strip()!='INTEGRATION_READY':raise RuntimeError('Server failed to start; see server.log')
                    source=(ROOT/'tests/integration'/script).read_text().replace('__BASE_URL__',base).replace('__IMAGE_ONE__',f'{temp}/1.png').replace('__IMAGE_TWO__',f'{temp}/2.png')
                    result=browser('run-code',source)
                    if '"pass": true' not in result and '"pass":true' not in result:raise RuntimeError(f'Browser did not confirm success: {result}')
                    log.write(f'{script}: {result}\n');log.flush();print(f'PASS {script}',flush=True)
                finally:
                    server.terminate()
                    try:server.wait(timeout=10)
                    except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
                    server.stdout.close()
        finally:browser('close')
    print('PASS browser integration. Evidence: tests/integration/evidence/',flush=True)

if __name__=='__main__':main()
