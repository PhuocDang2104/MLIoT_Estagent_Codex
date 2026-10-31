"""Single-process upload admission, not an OS quota or a bound on all DB writes."""
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import sqlite3
import threading

from fastapi import HTTPException

_locks = {}
_locks_lock = threading.Lock()


class UploadStorage:
    def __init__(self, root, max_bytes, min_free_bytes):
        self.root = root
        self.max_bytes = max_bytes
        self.min_free_bytes = min_free_bytes
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        with _locks_lock:
            self.lock = _locks.setdefault(str(root), threading.RLock())

    def usage(self):
        """All regular file lengths, including DBs/WAL/journals/backups; no symlinks."""
        total = 0
        def unavailable(error):
            raise error
        for directory, dirs, files in os.walk(self.root, followlinks=False, onerror=unavailable):
            for name in dirs + files:
                path = Path(directory) / name
                if path.is_symlink():
                    raise OSError('storage tree contains a symlink')
                if path.is_file():
                    total += path.stat().st_size
        return total

    @contextmanager
    def reserve(self, payload_bytes):
        # SQLite BLOB persistence may grow both main DB and WAL. Metadata/page
        # slack is reserved before writes; this is conservative admission, not a
        # claim that arbitrary concurrent SQL/background jobs have a hard quota.
        growth = 3 * payload_bytes + 65536
        with self.lock:
            try:
                used = self.usage()
                free = shutil.disk_usage(self.root).free
            except OSError:
                raise HTTPException(507, 'Upload storage unavailable / Không thể kiểm tra dung lượng lưu trữ.') from None
            if used + growth > self.max_bytes or free - growth < self.min_free_bytes:
                raise HTTPException(507, 'Upload storage limit reached. Existing tours remain readable / Đã đạt giới hạn lưu trữ; tour hiện có vẫn xem được.')
            yield


@contextmanager
def upload_reservation(request, payload_bytes):
    guard = getattr(request.app.state, 'storage_limits', None)
    if guard is None:
        yield
    else:
        try:
            with guard.reserve(payload_bytes):
                yield
        except (OSError, sqlite3.Error):
            raise HTTPException(507, 'Upload storage unavailable / Không thể lưu tệp; hãy thử lại sau.') from None


def validate_storage(env, paths=None):
    """Validate config and create the directory, never reserve/write an upload."""
    enabled = env.get('STORAGE_LIMITS_ENABLED', '0')
    if enabled not in {'0', '1'}:
        raise ValueError('STORAGE_LIMITS_ENABLED must be 0 or 1')
    if enabled == '0':
        return None
    if paths is None:
        assistant = Path(env.get('ASSISTANT_DB') or Path(__file__).resolve().parents[1] / 'projects/assistant/work/checkpoints.sqlite')
        paths = [assistant, Path(env.get('TOUR_DATA_DIR', assistant.parent/'tours')),
                 Path(env.get('STUDIO_DATA_DIR', assistant.parent/'studio'))]
    raw = env.get('STORAGE_LIMITS_ROOT', '')
    root = Path(raw)
    if not raw or raw != raw.strip() or not root.is_absolute() or root.is_symlink():
        raise ValueError('STORAGE_LIMITS_ROOT requires a dedicated absolute directory without symlinks')
    # Reject symlinked ancestors as well; all application storage must be inside.
    if any(p.is_symlink() for p in [root, *root.parents]):
        raise ValueError('STORAGE_LIMITS_ROOT must not contain symlink ancestors')
    root = root.resolve()
    if any(not Path(p).resolve().is_relative_to(root) for p in paths):
        raise ValueError('STORAGE_LIMITS_ROOT must contain all assistant/tour/Studio storage')
    values = []
    for name in ('STORAGE_LIMITS_MAX_BYTES', 'STORAGE_LIMITS_MIN_FREE_BYTES'):
        value = env.get(name, '')
        if not isinstance(value, str) or not value.isascii() or not value.isdecimal() or not 0 < int(value) <= 2**63-1:
            raise ValueError(f'{name} requires an explicit positive integer')
        values.append(int(value))
    try:
        guard = UploadStorage(root, *values)
        guard.usage()
        shutil.disk_usage(root)
    except OSError:
        raise ValueError('STORAGE_LIMITS_ROOT unavailable or contains unsupported entries') from None
    return guard


def install_storage(app, env, paths):
    app.state.storage_limits = validate_storage(env, paths)
