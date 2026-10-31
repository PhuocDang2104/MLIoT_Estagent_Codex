"""Scoped local browser QA: isolated env/data, loopback servers, finally cleanup."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]


def main():
    evidence = ROOT/'tests/ai/evidence/studio-runtime'
    evidence.mkdir(parents=True,exist_ok=True)
    env = {k:v for k,v in os.environ.items() if k.upper() in (
        'PATH','SYSTEMROOT','SYSTEMDRIVE','WINDIR','TEMP','TMP','APPDATA','LOCALAPPDATA','USERPROFILE','COMSPEC',
        'CREATOR_QA_BROWSER')}
    env.update(PYTHONUTF8='1',LANGSMITH_TRACING='false',LANGCHAIN_TRACING_V2='false')
    results = []
    for name, port, runner, fixture in [
        ('full',5187,'run_creator_full_browser',True),
        ('waiting',5186,'run_creator_browser',True),
        ('keyless',5188,'run_creator_no_key_browser',False)]:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1',port))  # Refuse to interact with another local service.
        target = evidence/name
        target.mkdir(exist_ok=True)
        # Keep synthetic diagnostics in OS temp. Windows security/indexing can
        # retain SQLite handles after process exit; QA never deletes live data.
        data = tempfile.mkdtemp(prefix='estagent-runtime-'+name+'-')
        with (target/'server.log').open('w',encoding='utf8') as log:
            child_env = {**env, 'CREATOR_QA_EVIDENCE_DIR':str(target),
                'CREATOR_QA_DB':str(Path(data)/'assistant.sqlite'),
                'CREATOR_QA_ORIGIN':f'http://127.0.0.1:{port}', 'CREATOR_QA_WORKER':'1' if name == 'full' else '0',
                'ASSISTANT_DB':str(Path(data)/'assistant.sqlite'), 'ASSISTANT_ORIGIN':f'http://127.0.0.1:{port}'}
            module = 'tests.ai.creator_browser_server:app' if fixture else 'server.assistant.app:app'
            server = subprocess.Popen([sys.executable,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port),'--no-access-log'],
                cwd=ROOT, env=child_env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic()+30
                while time.monotonic()<deadline:
                    if server.poll() is not None:
                        raise RuntimeError('QA server stopped; inspect synthetic server.log')
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/api/studio/health',timeout=1) as response:
                            if json.load(response)['ready']:
                                break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise RuntimeError('QA server startup timed out')
                subprocess.run([sys.executable,'-m','tests.ai.'+runner],cwd=ROOT,env=child_env,check=True,timeout=150)
                results.append({'mode':name,'status':'PASS','paid_calls':0})
            finally:
                if os.name == 'nt' and server.poll() is None:
                    # Windows venv launchers can have a separate Python child.
                    subprocess.run(['taskkill','/PID',str(server.pid),'/T','/F'],capture_output=True,check=True)
                else:
                    server.terminate()
                try:
                    server.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    server.kill(); server.wait()
    (evidence/'browser-results.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')


if __name__ == '__main__':
    main()
