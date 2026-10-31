"""Opt-in, single-worker admission guards; counts attempts, never tokens or USD.

SQLite stores aggregate windows only. No request bodies, URLs, identities or keys.
Use install_limits last in the app factory so admission precedes body buffering.
"""
from contextlib import closing
from dataclasses import dataclass
import math
from pathlib import Path
import re
import sqlite3
import threading
import time

from starlette.responses import JSONResponse


@dataclass(frozen=True)
class Window:
    name: str
    count: int
    seconds: int


@dataclass(frozen=True)
class Group:
    concurrency: int
    windows: tuple[Window, ...]


def _positive(env, name, default=None):
    value = env.get(name, default)
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,8}', value):
        raise ValueError(f'{name}: require an explicit positive integer (at most 9 digits)')
    return int(value)


class AttemptLedger:
    """Fixed windows anchored at first admission, persisted across app restarts.

    All window checks/increments share one short SQLite write transaction.
    A backward wall-clock jump never resets a window or creates new allowance.
    Window durations are immutable for this ledger; changing a cap preserves used.
    """
    def __init__(self, path, groups, clock=time.time):
        self.path = Path(path)
        self.groups = groups
        self.clock = clock
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(self._connect()) as db, db:
                db.execute('BEGIN IMMEDIATE')
                tables = {row[0] for row in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                if tables - {'limit_windows', 'limit_clock'}:
                    raise ValueError('API_LIMITS_DB: require a dedicated limits database')
                db.execute('CREATE TABLE IF NOT EXISTS limit_windows '
                           '(name TEXT PRIMARY KEY, seconds INTEGER NOT NULL, '
                           'started REAL NOT NULL, used INTEGER NOT NULL)')
                db.execute('CREATE TABLE IF NOT EXISTS limit_clock '
                           '(id INTEGER PRIMARY KEY CHECK(id=1), highwater REAL NOT NULL)')
                expected = {w.name: w.seconds for g in groups.values() for w in g.windows}
                for name, seconds in db.execute('SELECT name, seconds FROM limit_windows'):
                    if name not in expected or seconds != expected[name]:
                        raise ValueError('API_LIMITS_DB: persisted window configuration differs; '
                                         'do not reset the live ledger to bypass allowance')
            self.path.chmod(0o600)
        except (OSError, sqlite3.Error):
            raise ValueError('API_LIMITS_DB: cannot initialize dedicated SQLite storage') from None

    def _connect(self):
        # A busy/unavailable ledger fails closed; never wait on a model in this transaction.
        return sqlite3.connect(self.path, timeout=0.1)

    def reserve(self, group):
        now = float(self.clock())
        if not math.isfinite(now) or now < 0:
            raise ValueError('API limits clock must be finite and non-negative')
        with closing(self._connect()) as db, db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT highwater FROM limit_clock WHERE id=1').fetchone()
            now = max(now, row[0]) if row else now
            db.execute('INSERT INTO limit_clock VALUES (1, ?) '
                       'ON CONFLICT(id) DO UPDATE SET highwater=excluded.highwater', (now,))
            pending, denied = [], []
            for window in self.groups[group].windows:
                row = db.execute('SELECT seconds, started, used FROM limit_windows WHERE name=?',
                                 (window.name,)).fetchone()
                if row and row[0] != window.seconds:
                    raise ValueError('API limits window changed while running')
                start, used = (row[1], row[2]) if row else (now, 0)
                if now >= start + window.seconds:
                    start, used = now, 0
                if used >= window.count:
                    denied.append((window.name, max(1, math.ceil(start + window.seconds - now))))
                pending.append((window.name, window.seconds, start, used + 1))
            if denied:
                # Rejected admission does not increment attempts; highwater still commits.
                return max(denied, key=lambda item: item[1])
            db.executemany('INSERT INTO limit_windows VALUES (?, ?, ?, ?) '
                           'ON CONFLICT(name) DO UPDATE SET started=excluded.started, used=excluded.used',
                           pending)
        return None


class LimitsMiddleware:
    """Pure ASGI: hold a slot until the downstream app finishes, including streams."""
    def __init__(self, app, *, ledger, groups):
        self.app, self.ledger = app, ledger
        self.slots = {name: threading.BoundedSemaphore(group.concurrency)
                      for name, group in groups.items()}

    @staticmethod
    def group(scope):
        if scope['type'] != 'http' or scope['method'] != 'POST':
            return None
        path = scope['path'].rstrip('/')
        if path in {'/api/assistant/turn', '/api/assistant/voice'} or re.fullmatch(
                r'/api/tours/(drafts|published)/[^/]+/chat', path) or re.fullmatch(
                r'/api/studio/projects/[^/]+/generations', path) or re.fullmatch(
                r'/api/studio/generations/[^/]+/(review|retry|edits)', path) or re.fullmatch(
                r'/api/studio/generations/[^/]+/edits/[^/]+/apply', path) or re.fullmatch(
                r'/api/studio-tours/[^/]+/questions', path):
            return 'ai'
        if path in {'/api/tours/assets', '/api/tours/audio-assets'} or re.fullmatch(
                r'/api/studio/projects/[^/]+/assets', path):
            return 'upload'
        return None

    async def __call__(self, scope, receive, send):
        group = self.group(scope)
        if group is None:
            return await self.app(scope, receive, send)
        slot = self.slots[group]
        if not slot.acquire(blocking=False):
            return await self.reject(scope, receive, send, 'concurrency_limited', 1)
        try:
            try:
                denied = self.ledger.reserve(group)
            except (sqlite3.Error, OSError, ValueError):
                # Explicit, sanitized error. No fallback to unguarded provider calls.
                return await self.reject(scope, receive, send, 'limits_unavailable', 1, status=503)
            if denied:
                name, retry = denied
                code = 'attempt_allowance_exhausted' if name == 'ai_allowance' else 'rate_limited'
                return await self.reject(scope, receive, send, code, retry)
            await self.app(scope, receive, send)
        finally:
            slot.release()

    @staticmethod
    async def reject(scope, receive, send, code, retry, status=429):
        message = ('Bộ giới hạn yêu cầu chưa sẵn sàng. Hãy thử lại sau.' if status == 503 else
                   'Đã đạt giới hạn yêu cầu. Hãy thử lại sau.')
        response = JSONResponse({'error': message, 'code': code, 'retry_after': retry},
                                status_code=status, headers={'Retry-After': str(retry),
                                'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
        await response(scope, receive, send)


def install_limits(app, env, *, clock=time.time):
    """Install once before app startup. Optional clock injection is for deterministic QA.

    Disabled by default only for keyless compatibility. A configured OpenAI key
    requires explicit opt-in and all AI bounds; enabling is not spend authorization.
    """
    enabled = env.get('API_LIMITS_ENABLED', '0')
    if enabled not in {'0', '1'}:
        raise ValueError('API_LIMITS_ENABLED: require 0 or 1')
    if enabled == '0':
        if (env.get('OPENAI_API_KEY') or '').strip():
            raise ValueError('API_LIMITS_ENABLED must be 1 when OPENAI_API_KEY is configured')
        return None
    if getattr(app.state, 'api_limits', None) is not None:
        raise ValueError('install_limits must be called only once')
    raw_path = env.get('API_LIMITS_DB', '')
    if not isinstance(raw_path, str) or not raw_path.strip() or raw_path != raw_path.strip():
        raise ValueError('API_LIMITS_DB: require a dedicated absolute file path')
    path = Path(raw_path)
    if not path.is_absolute() or path.is_symlink():
        raise ValueError('API_LIMITS_DB: require a dedicated absolute file path, not a symlink')
    root = Path(__file__).resolve().parents[1]
    assistant = Path(env.get('ASSISTANT_DB') or root / 'projects/assistant/work/checkpoints.sqlite')
    tours = Path(env.get('TOUR_DATA_DIR') or assistant.parent / 'tours') / 'tours.sqlite'
    if path.resolve() in {assistant.resolve(), tours.resolve()}:
        raise ValueError('API_LIMITS_DB: cannot reuse assistant/tour database')
    groups = {
        'ai': Group(_positive(env, 'API_LIMITS_AI_CONCURRENCY'), (
            Window('ai_burst', _positive(env, 'API_LIMITS_AI_REQUESTS'),
                   _positive(env, 'API_LIMITS_AI_WINDOW_SECONDS')),
            Window('ai_allowance', _positive(env, 'API_LIMITS_AI_ATTEMPTS'),
                   _positive(env, 'API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS')))),
        'upload': Group(_positive(env, 'API_LIMITS_UPLOAD_CONCURRENCY', '1'), (
            Window('upload_burst', _positive(env, 'API_LIMITS_UPLOAD_REQUESTS', '6'),
                   _positive(env, 'API_LIMITS_UPLOAD_WINDOW_SECONDS', '60')),)),
    }
    if groups['ai'].windows[1].seconds < groups['ai'].windows[0].seconds:
        raise ValueError('API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS must cover the burst window')
    ledger = AttemptLedger(path, groups, clock)
    app.add_middleware(LimitsMiddleware, ledger=ledger, groups=groups)
    app.state.api_limits = ledger
    return ledger
