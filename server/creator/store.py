"""Private project assets and durable event/job metadata in a dedicated SQLite DB."""
import hashlib
import io
import json
import math
import sqlite3
import struct
import threading
import uuid
import wave
from datetime import datetime, timezone
from fastapi import HTTPException


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


class Store:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / 'creator.sqlite', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.in_action = False
        self.db.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, owner TEXT, data TEXT);
            CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY, project TEXT, meta TEXT, content BLOB);
            CREATE TABLE IF NOT EXISTS generations(id TEXT PRIMARY KEY, project TEXT, status TEXT, error TEXT, attempts INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT, generation TEXT, data TEXT);
            CREATE INDEX IF NOT EXISTS event_generation ON events(generation,id);
            CREATE TABLE IF NOT EXISTS actions(owner TEXT, request TEXT, payload TEXT, result TEXT, PRIMARY KEY(owner,request));
            CREATE TABLE IF NOT EXISTS published(id TEXT PRIMARY KEY, project TEXT, generation TEXT UNIQUE, data TEXT);
            CREATE TABLE IF NOT EXISTS viewer_requests(owner TEXT, tour TEXT, request TEXT, payload TEXT, status TEXT, result TEXT, PRIMARY KEY(owner,tour,request));
        ''')
        self.db.execute("UPDATE generations SET status='failed',error='Tiến trình đã dừng. Kiểm tra rồi chọn thử lại.' WHERE status IN ('queued','running')")
        self.db.execute("UPDATE viewer_requests SET status='failed' WHERE status='running'")
        self.db.commit()

    def execute(self, sql, args=()):
        with self.lock:
            if self.in_action:
                return self.db.execute(sql, args)
            with self.db:
                return self.db.execute(sql, args)

    def rows(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.db.execute(sql, args).fetchall()]

    def project(self, owner, project_id):
        rows = self.rows('SELECT data FROM projects WHERE id=? AND owner=?', (project_id, owner))
        if not rows:
            raise HTTPException(404, 'Không tìm thấy project trong phiên này.')
        return json.loads(rows[0]['data'])

    def assets(self, project_id):
        return [json.loads(r['meta']) for r in self.rows('SELECT meta FROM assets WHERE project=? ORDER BY rowid', (project_id,))]

    def content(self, asset):
        rows = self.rows('SELECT content FROM assets WHERE id=?', (asset['id'],))
        if not rows:
            raise ValueError('Asset missing')
        return rows[0]['content']

    def put_asset(self, project_id, name, kind, mime, data, extra=None):
        digest = hashlib.sha256(data).hexdigest()
        for asset in self.assets(project_id):
            if asset['sha256'] == digest and asset['kind'] == kind:
                return asset
        asset = {'id': uid(), 'project_id': project_id, 'name': name,
                 'kind': kind, 'mime': mime, 'size': len(data), 'sha256': digest, **(extra or {})}
        self.execute('INSERT INTO assets VALUES(?,?,?,?)', (asset['id'], project_id,
                     json.dumps(asset, ensure_ascii=False), data))
        return asset

    def write_audio(self, project, segment_id, data):
        duration = wav_duration(data)
        asset = self.put_asset(project['id'], segment_id + '.wav', 'narration',
                               'audio/wav', data, {'duration': duration})
        return {'checkpoint_id': segment_id, 'asset_id': asset['id'], 'duration': duration}

    def write_model(self, project, result):
        data = result['glb']
        if (len(data) < 20 or data[:4] != b'glTF' or
                struct.unpack('<II', data[4:12]) != (2, len(data))):
            raise ValueError('Worker must return a valid GLB 2 container')
        length, kind = struct.unpack('<II', data[12:20])
        if kind != 0x4e4f534a or length + 20 > len(data):
            raise ValueError('GLB JSON chunk missing')
        manifest = json.loads(data[20:20+length])
        if not manifest.get('meshes') or not manifest.get('scenes'):
            raise ValueError('GLB has no renderable scene')
        anchors = result['anchors']
        for value in anchors.values():
            pos = value.get('position', [])
            if len(pos) != 3 or any(not isinstance(n, (float, int)) or not math.isfinite(n) for n in pos):
                raise ValueError('Invalid worker checkpoint anchor')
        asset = self.put_asset(project['id'], 'house.glb', 'model', 'model/gltf-binary', data)
        return {'asset_id': asset['id'], 'anchors': anchors}

    def emit(self, generation_id, node, status, message):
        event = {'generation_id': generation_id, 'node_id': node, 'event_type': 'status',
                 'status': status, 'message': message, 'timestamp': now(),
                 'artifact_type': None, 'artifact_url': None}
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
                    raise HTTPException(409, 'Request ID đã dùng cho nội dung khác.')
                return json.loads(rows[0]['result'])
            with self.db:
                self.in_action = True
                try:
                    value = operation()
                    self.db.execute('INSERT INTO actions VALUES(?,?,?,?)', (owner, request_id, serialized, json.dumps(value)))
                    return value
                finally:
                    self.in_action = False
