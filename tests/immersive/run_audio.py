"""Real Chromium + production API + synthetic sine WAV. No model, user media or paid calls."""
import array
import math
import os
from pathlib import Path
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import uuid
import wave
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'tests/immersive/evidence'

def main():
    cli=shutil.which('playwright-cli')
    if not cli:raise RuntimeError('playwright-cli and Chromium required')
    session='tour-audio-'+uuid.uuid4().hex[:8]
    child_env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL','DISPLAY'}};child_env['PYTHONPATH']=str(ROOT)
    with socket.socket() as socket_:socket_.bind(('127.0.0.1',0));port=socket_.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    def browser(*args):
        r=subprocess.run([cli,f'-s={session}','--raw',*args],cwd=ROOT,env=child_env,capture_output=True,text=True,timeout=120)
        if r.returncode or '### Error' in r.stdout:raise RuntimeError(r.stdout+r.stderr)
        return r.stdout
    EVIDENCE.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='runtime-',dir=ROOT/'tests/immersive') as temp,(EVIDENCE/'browser.log').open('w') as log,(EVIDENCE/'server.log').open('w') as server_log:
        for i,color in [(1,'navy'),(2,'teal')]:Image.new('RGB',(300,180),color).save(f'{temp}/{i}.png')
        for name,seconds,frequency in [('music',30,220),('voice-one',8,440),('voice-two',4,660)]:
            samples=array.array('h',(int(1400*math.sin(2*math.pi*frequency*i/16000)) for i in range(seconds*16000)))
            if sys.byteorder!='little':samples.byteswap()
            with wave.open(f'{temp}/{name}.wav','wb') as target:target.setnchannels(1);target.setsampwidth(2);target.setframerate(16000);target.writeframes(samples.tobytes())
        try:
            browser('open','about:blank')
            for script in ['audio-browser.js','audio-restart.js']:
                server=subprocess.Popen([sys.executable,'tests/audio/local_server.py','--db',f'{temp}/assistant.sqlite','--port',str(port)],cwd=ROOT,env=child_env,stdout=subprocess.PIPE,stderr=server_log,text=True)
                try:
                    with selectors.DefaultSelector() as selector:
                        selector.register(server.stdout,selectors.EVENT_READ)
                        if not selector.select(timeout=25) or server.stdout.readline().strip()!='AUDIO_TEST_READY':raise RuntimeError('Audio test server failed startup; inspect server.log')
                    source=(ROOT/'tests/immersive'/script).read_text()
                    for key,value in {'__BASE_URL__':base,'__IMAGE_ONE__':f'{temp}/1.png','__IMAGE_TWO__':f'{temp}/2.png','__MUSIC__':f'{temp}/music.wav','__VOICE_ONE__':f'{temp}/voice-one.wav','__VOICE_TWO__':f'{temp}/voice-two.wav'}.items():source=source.replace(key,value)
                    result=browser('run-code',source)
                    if '"pass":true' not in result and '"pass": true' not in result:raise RuntimeError(result)
                    log.write(script+': '+result+'\n');log.flush();print('PASS '+script,flush=True)
                finally:
                    server.terminate()
                    try:server.wait(timeout=10)
                    except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
                    server.stdout.close()
        finally:browser('close')
    print('PASS real WAV/media/browser/restart; fixtures are tones, not human narration or licensed music.',flush=True)

if __name__=='__main__':main()
