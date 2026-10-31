"""Smoke the documented entry command with a fresh local data path and no secrets."""
import os
from pathlib import Path
import selectors
import socket
import subprocess
import tempfile
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]

def main():
    with socket.socket() as probe:probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    runtime=ROOT/'projects/integration/work';runtime.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dev-command-',dir=runtime) as temp:
        env={k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL'}}
        env.update(ESTAGENT_PORT=str(port),ASSISTANT_DB=f'{temp}/assistant.sqlite',UV_OFFLINE='1')
        server=subprocess.Popen(['bash','scripts/dev.sh'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,bufsize=1)
        try:
            deadline=time.monotonic()+30
            with selectors.DefaultSelector() as selector:
                selector.register(server.stdout,selectors.EVENT_READ)
                while time.monotonic()<deadline:
                    if not selector.select(timeout=max(0,deadline-time.monotonic())):raise RuntimeError('Timed out waiting for uvicorn startup event')
                    line=server.stdout.readline()
                    if not line:raise RuntimeError('Dev command exited before readiness')
                    if 'Uvicorn running on' in line:break
                else:raise RuntimeError('Dev command did not start')
            base=f'http://127.0.0.1:{port}'
            for route in ['/','/creator.html','/viewer.html','/motion.css','/motion.js','/assets/favicon.svg','/api/assistant/state','/api/tours/session','/api/tours/published']:
                with urllib.request.urlopen(base+route,timeout=10) as response:
                    assert response.status==200
                    if route=='/':assert b'hero-title' in response.read()
            print('PASS documented command: bash scripts/dev.sh; one origin; landing/Creator/Viewer/motion/favicon/assistant/tours all HTTP 200; no keys; isolated ephemeral storage.')
        finally:
            server.terminate()
            try:server.wait(timeout=10)
            except subprocess.TimeoutExpired:server.kill();server.wait(timeout=5)
            server.stdout.close()

if __name__=='__main__':main()
