"""Private project assets and durable event/job metadata in a dedicated SQLite DB."""
import hashlib
import io
import json
import math
import logging
import re
from contextlib import nullcontext
import sqlite3
import struct
import threading
import uuid
import wave
from datetime import datetime, timezone
from contextlib import contextmanager
from fastapi import HTTPException
from fastapi.responses import Response


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


def image_info(data):
    """Use the existing Pillow dependency to validate the entire image."""
    from PIL import Image, UnidentifiedImageError
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as source:
                mime = {'PNG':'image/png', 'JPEG':'image/jpeg', 'WEBP':'image/webp'}.get(source.format)
                width, height = source.size
                if not mime or min(width,height) < 64 or max(width,height) > 20000 or width*height > 32_000_000:
                    raise ValueError('Use JPEG/PNG/WebP, 64-20000 pixels, at most 32 megapixels')
                source.verify()
            with Image.open(io.BytesIO(data)) as source:
                source.load()
        return mime, width, height
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('Invalid or oversized image') from None


def wav_duration(data):
    with wave.open(io.BytesIO(data), 'rb') as audio:
        duration = audio.getnframes() / audio.getframerate()
        if not 0 < duration <= 600:
            raise ValueError('Audio must be between 0 and 600 seconds')
        if len(audio.readframes(audio.getnframes())) < audio.getnframes() * audio.getnchannels() * audio.getsampwidth():
            raise ValueError('Truncated WAV')
        return duration


def sanitize_image(data):
    """Validate before decoding; remove embedded metadata and bake EXIF orientation."""
    from PIL import Image, ImageOps
    image_info(data)
    with Image.open(io.BytesIO(data)) as source:
        if getattr(source, 'is_animated', False):
            raise ValueError('Use a static property image')
        if not source.info and not source.getexif():
            return data
        fmt = source.format
        pixels = ImageOps.exif_transpose(source)
        pixels = pixels.convert('RGB' if fmt == 'JPEG' else 'RGBA' if 'A' in pixels.getbands() or pixels.mode == 'P' else 'RGB')
        pixels.info.clear()
        pixels.getexif().clear()
        output = io.BytesIO()
        pixels.save(output, format=fmt, **({'quality':92} if fmt in ('JPEG','WEBP') else {}))
        result = output.getvalue()
        if len(result) > 20*1024*1024:
            raise ValueError('Normalized image exceeds 20 MB; resize the image')
        return result


class Store:
    def __init__(self, root, object_storage=None, storage_limits=None):
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        root.chmod(0o700)
        self.db = sqlite3.connect(root / 'creator.sqlite', check_same_thread=False)
        (root / 'creator.sqlite').chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.in_action = False
        self.object_storage = object_storage
        self.storage_limits = storage_limits
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, owner TEXT, data TEXT);
            CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, project TEXT, meta TEXT, content BLOB);
            CREATE TABLE IF NOT EXISTS media_refs(asset TEXT PRIMARY KEY, backend TEXT NOT NULL, object_key TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS generations(id TEXT PRIMARY KEY, project TEXT, status TEXT, error TEXT, attempts INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, generation TEXT, data TEXT);
            CREATE INDEX IF NOT EXISTS event_generation ON events(generation,id);
            CREATE TABLE IF NOT EXISTS actions(owner TEXT, request TEXT, payload TEXT, result TEXT, PRIMARY KEY(owner,request));
            CREATE TABLE IF NOT EXISTS published(id TEXT PRIMARY KEY, project TEXT, generation TEXT UNIQUE, data TEXT);
            CREATE TABLE IF NOT EXISTS viewer_requests(owner TEXT, tour TEXT, request TEXT, payload TEXT, status TEXT, result TEXT, PRIMARY KEY(owner,tour,request));
            CREATE TABLE IF NOT EXISTS jobs(generation TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS edits(id TEXT PRIMARY KEY, generation TEXT NOT NULL, owner TEXT NOT NULL, revision INTEGER NOT NULL, data TEXT, status TEXT NOT NULL);
        ''')
        columns = {r['name'] for r in self.db.execute('PRAGMA table_info(generations)')}
        for name, definition in [('revision', 'INTEGER NOT NULL DEFAULT 1'), ('parent', 'TEXT')]:
            if name not in columns:
                self.db.execute(f'ALTER TABLE generations ADD COLUMN {name} {definition}')
        if 'available_at' not in {r['name'] for r in self.db.execute('PRAGMA table_info(jobs)')}:
            self.db.execute('ALTER TABLE jobs ADD COLUMN available_at REAL NOT NULL DEFAULT 0')
        self.interrupted = [r['id'] for r in self.db.execute("SELECT id FROM generations WHERE status='running' OR (status='queued' AND id NOT IN (SELECT generation FROM jobs WHERE status='queued'))")]
        self.db.execute("UPDATE jobs SET status='failed' WHERE status='running'")
        self.db.execute("UPDATE generations SET status='failed',error='The process stopped. Check the configuration and retry.' WHERE status='running' OR (status='queued' AND id NOT IN (SELECT generation FROM jobs WHERE status='queued'))")
        self.db.execute("UPDATE edits SET status='failed' WHERE status='running'")
        self.db.execute("UPDATE viewer_requests SET status='failed' WHERE status='running'")
        self.db.commit()

    def execute(self, sql, args=()):
        with self.lock:
            if self.in_action:
                return self.db.execute(sql, args)
            with self.db:
                return self.db.execute(sql, args)

    @contextmanager
    def transaction(self):
        with self.lock:
            if self.in_action:
                yield
                return
            with self.db:
                self.in_action = True
                try:
                    yield
                finally:
                    self.in_action = False

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def project(self, owner, project_id):
        rows = self.rows('SELECT data FROM projects WHERE id=? AND owner=?', (project_id, owner))
        if not rows:
            raise HTTPException(404, 'Project not found in this session.')
        return json.loads(rows[0]['data'])

    def assets(self, project_id):
        return [json.loads(r['meta']) for r in self.rows('SELECT meta FROM assets WHERE project=? ORDER BY rowid', (project_id,))]

    def content(self, asset):
        key = self.object_key(asset['id'])
        if key is not None:
            return self.require_objects().get_bytes(key)
        rows = self.rows('SELECT content FROM assets WHERE id=?', (asset['id'],))
        if not rows:
            raise ValueError('Asset missing')
        return rows[0]['content']

    def object_key(self, asset_id):
        refs=self.rows('SELECT backend,object_key FROM media_refs WHERE asset=?',(asset_id,))
        if not refs:return None
        if refs[0]['backend']!='minio':raise HTTPException(503,'Media backend unavailable')
        return refs[0]['object_key']

    def require_objects(self):
        if self.object_storage is None:raise HTTPException(503,'Object storage unavailable')
        return self.object_storage

    def verify_asset(self, asset):
        key=self.object_key(asset['id'])
        if key is not None:
            info=self.require_objects().stat(key)
            if info.size!=asset['size'] or info.content_type!=asset['mime'] or (info.sha256 and info.sha256!=asset['sha256']):
                raise HTTPException(409,'Media does not match its registered metadata')
        else:
            rows=self.rows('SELECT length(content) AS size FROM assets WHERE id=?',(asset['id'],))
            if not rows or rows[0]['size']!=asset['size']:raise HTTPException(409,'Media unavailable')

    def response(self, asset, *, range_header=None):
        key=self.object_key(asset['id'])
        if key is not None:return self.require_objects().response(key,range_header=range_header)
        data=self.content(asset)
        headers={'Accept-Ranges':'bytes','Cache-Control':'no-store'}
        if range_header is None:return Response(data,media_type=asset['mime'],headers=headers)
        match=re.fullmatch(r'bytes=([0-9]*)-([0-9]*)',range_header)
        if not match or not any(match.groups()) or not data:
            return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{len(data)}'})
        left,right=match.groups()
        start=int(left) if left else max(0,len(data)-int(right))
        end=min(int(right),len(data)-1) if left and right else len(data)-1
        if start>=len(data) or start>end:
            return Response(status_code=416,headers={**headers,'Content-Range':f'bytes */{len(data)}'})
        return Response(data[start:end+1],status_code=206,media_type=asset['mime'],
            headers={**headers,'Content-Range':f'bytes {start}-{end}/{len(data)}'})

    def put_asset(self, project_id, name, kind, mime, data, extra=None):
        with self.lock:
            digest = hashlib.sha256(data).hexdigest()
            for asset in self.assets(project_id):
                if asset['sha256'] == digest and asset['kind'] == kind:
                    return asset
            asset = {'id': uid(), 'project_id': project_id, 'name': name,
                     'kind': kind, 'mime': mime, 'size': len(data), 'sha256': digest, **(extra or {})}
            key=f'studio/assets/{asset["id"]}'
            serialized=json.dumps(asset,ensure_ascii=False)
            reservation=self.storage_limits.reserve(len(serialized.encode()) if self.object_storage else len(data)) if self.storage_limits else nullcontext()
            attempted=False
            with reservation:
                try:
                    if self.object_storage:
                        attempted=True
                        self.object_storage.put_bytes(key,data,mime)
                    with nullcontext() if self.in_action else self.db:
                        self.db.execute('INSERT INTO assets VALUES(?,?,?,?)',
                            (asset['id'],project_id,serialized,b'' if self.object_storage else data))
                        if self.object_storage:self.db.execute('INSERT INTO media_refs VALUES(?,?,?)',(asset['id'],'minio',key))
                except BaseException:
                    if attempted:
                        try:self.object_storage.remove(key)
                        except Exception:logging.getLogger(__name__).warning('Orphan media cleanup failed; operator reconciliation required')
                    raise
            return asset

    def write_audio(self, project, segment_id, data):
        duration = wav_duration(data)
        asset = self.put_asset(project['id'], segment_id + '.wav', 'narration',
                               'audio/wav', data, {'duration': duration})
        return {'checkpoint_id': segment_id, 'asset_id': asset['id'], 'duration': duration}

    def write_model(self, project, result):
        data = result['glb']
        if (len(data) < 20 or len(data) > 20*1024*1024 or data[:4] != b'glTF' or
                struct.unpack('<II', data[4:12]) != (2, len(data))):
            raise ValueError('Worker must return a valid GLB 2 container')
        length, kind = struct.unpack('<II', data[12:20])
        if kind != 0x4e4f534a or length + 20 > len(data):
            raise ValueError('GLB JSON chunk missing')
        manifest = json.loads(data[20:20+length])
        def check_uris(value):
            if isinstance(value, dict):
                if 'uri' in value and not str(value['uri']).startswith('data:'):
                    raise ValueError('Geometry must be self-contained; external URIs are forbidden')
                for child in value.values():
                    check_uris(child)
            elif isinstance(value, list):
                for child in value:
                    check_uris(child)
        check_uris(manifest)
        if not manifest.get('meshes') or not manifest.get('scenes'):
            raise ValueError('GLB has no renderable scene')
        anchors = result['anchors']
        for value in anchors.values():
            pos = value.get('position', [])
            if len(pos) != 3 or any(not isinstance(n, (float, int)) or not math.isfinite(n) for n in pos):
                raise ValueError('Invalid worker checkpoint anchor')
        asset = self.put_asset(project['id'], 'house.glb', 'model', 'model/gltf-binary', data)
        return {'asset_id': asset['id'], 'anchors': anchors, **({'metadata':result['metadata']} if result.get('metadata') else {})}

    def emit(self, generation_id, node, status, message, event_type='status', progress=None):
        event = {'generation_id': generation_id, 'node_id': node, 'event_type': event_type,
                 'status': status, 'message': message, 'timestamp': now(),
                 'artifact_type': None, 'artifact_url': None}
        if progress is not None: event['progress']=progress
        with self.lock:
            if event_type == 'model_progress':
                # Cumulative snapshots: retain the latest summary, not thousands of token deltas.
                self.execute("DELETE FROM events WHERE generation=? AND json_extract(data,'$.event_type')='model_progress'", (generation_id,))
            self.execute('INSERT INTO events(generation,data) VALUES(?,?)', (generation_id, json.dumps(event, ensure_ascii=False)))

    def events(self, generation_id, after=0):
        return [{'event_id': r['id'], **json.loads(r['data'])} for r in self.rows(
            'SELECT id,data FROM events WHERE generation=? AND id>? ORDER BY id LIMIT 500', (generation_id, after))]

    def action(self, owner, request_id, payload, operation):
        serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        with self.lock:
            rows = self.rows('SELECT payload,result FROM actions WHERE owner=? AND request=?', (owner, request_id))
            if rows:
                if rows[0]['payload'] != serialized:
                    raise HTTPException(409, 'This request ID was already used for different content.')
                return json.loads(rows[0]['result'])
            with self.db:
                self.in_action = True
                try:
                    value = operation()
                    self.db.execute('INSERT INTO actions VALUES(?,?,?,?)', (owner, request_id, serialized, json.dumps(value)))
                    return value
                finally:
                    self.in_action = False
