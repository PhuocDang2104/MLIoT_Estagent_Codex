"""Optional async HTTP geometry adapter. The worker owns Blender/MCP/GPU execution.

POST /v1/builds must deduplicate operation_id, including after a lost response.
GET /v1/builds/{id} is read-only; no URL/path from a model is ever executed.
"""
import base64
import hashlib
import json
import re
import time
from urllib.parse import urlsplit
import httpx


class WorkerPending(Exception):
    pass


class HTTPGeometryWorker:
    def __init__(self, env, store, transport=None):
        self.url = env['STUDIO_GEOMETRY_URL'].rstrip('/')
        parsed = urlsplit(self.url)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('STUDIO_GEOMETRY_URL must be an operator-controlled HTTP(S) base URL without credentials/query')
        self.token = env.get('STUDIO_GEOMETRY_TOKEN', '')
        self.store, self.transport = store, transport
        store.execute('''CREATE TABLE IF NOT EXISTS worker_operations(
            id TEXT PRIMARY KEY, job TEXT, started REAL NOT NULL, polls INTEGER NOT NULL DEFAULT 0)''')

    def request(self, method, path, data=None, operation=None):
        headers = {'Authorization': 'Bearer '+self.token} if self.token else {}
        if operation:
            headers['Idempotency-Key'] = operation
        started = time.monotonic()
        with httpx.Client(timeout=httpx.Timeout(25,connect=5,write=10,pool=5), follow_redirects=False, trust_env=False, transport=self.transport) as client:
            with client.stream(method, self.url+path, json=data, headers=headers) as response:
                if response.status_code not in (200, 201, 202):
                    raise ValueError('Geometry worker request failed')
                body = bytearray()
                for part in response.iter_bytes():
                    body.extend(part)
                    if time.monotonic()-started > 45 or len(body) > 30*1024*1024:
                        raise ValueError('Geometry worker result exceeds limit')
        value = json.loads(body)
        if not isinstance(value, dict) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}', value.get('id', '')):
            raise ValueError('Invalid geometry job ID')
        if value.get('status') not in ('queued', 'running', 'completed', 'failed'):
            raise ValueError('Invalid geometry job status')
        return value

    def build(self, project, rooms, connections, assets):
        inputs = [a for a in assets if a['kind'] in ('panorama', 'floorplan')]
        payload = {'version':1, 'project':{k:project[k] for k in ('id','name','description','locale')},
                   'rooms':rooms, 'connections':connections, 'assets':inputs}
        # Stable across retries and restarts; a fork with different spatial input has a new key.
        operation = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        rows = self.store.rows('SELECT * FROM worker_operations WHERE id=?', (operation,))
        if not rows:
            self.store.execute('INSERT INTO worker_operations(id,started) VALUES(?,?)', (operation,time.time()))
            rows = self.store.rows('SELECT * FROM worker_operations WHERE id=?', (operation,))
        row = rows[0]
        if time.time()-row['started'] > 1800 or row['polls'] >= 180:
            raise ValueError('Geometry job exceeded 30 minutes or 180 polls')
        self.store.execute('UPDATE worker_operations SET polls=polls+1 WHERE id=?', (operation,))
        if row['job']:
            result = self.request('GET', '/v1/builds/'+row['job'])
            if result['id'] != row['job']:
                raise ValueError('Geometry worker returned another job')
        else:
            payload['operation_id'] = operation
            payload['assets'] = [{**a, 'content_base64':base64.b64encode(self.store.content(a)).decode()} for a in inputs]
            result = self.request('POST', '/v1/builds', payload, operation)
            self.store.execute('UPDATE worker_operations SET job=? WHERE id=?', (result['id'],operation))
        if result['status'] in ('queued', 'running'):
            raise WorkerPending()
        if result['status'] != 'completed':
            raise ValueError('Geometry job failed')
        return {'glb':base64.b64decode(result['glb_base64'], validate=True), 'anchors':result['anchors']}
