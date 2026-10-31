"""Single-host SQLite outbox; an OS lock fences a second API process.

External paid work is at-least-once: an interrupted running job requires an
explicit retry. Queued jobs survive a restart without a browser resubmission.
"""
import json
import os
import threading
import time


class RuntimeLock:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=True)
        self.file = (root / 'runtime.lock').open('a+b')
        try:
            if os.name == 'nt':
                import msvcrt
                self.file.seek(0)
                if not self.file.read(1):
                    self.file.write(b'0')
                    self.file.flush()
                self.file.seek(0)
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise RuntimeError('Studio data directory already has a runtime; use one ASGI worker') from None

    def close(self):
        self.file.close()


class DurableQueue:
    def __init__(self, store, run, clock=time.time):
        self.store, self.run = store, run
        self.clock = clock
        self.stop = threading.Event()
        self.wake = threading.Event()
        self.thread = threading.Thread(target=self.loop, name='studio-outbox', daemon=True)

    @staticmethod
    def put(store, generation_id, payload):
        from langgraph.types import Command
        value = {'resume': payload.resume} if isinstance(payload, Command) else {'input': payload}
        store.execute('''INSERT INTO jobs(generation,payload,status) VALUES(?,?,'queued')
            ON CONFLICT(generation) DO UPDATE SET payload=excluded.payload,status='queued',available_at=0
            WHERE jobs.status IN ('done','failed')''', (generation_id, json.dumps(value)))

    def loop(self):
        from langgraph.types import Command
        while not self.stop.is_set():
            rows = self.store.rows("SELECT generation,payload FROM jobs WHERE status='queued' AND available_at<=? ORDER BY rowid LIMIT 1", (self.clock(),))
            if not rows:
                self.wake.wait(.2)
                self.wake.clear()
                continue
            row = rows[0]
            value = json.loads(row['payload'])
            payload = Command(resume=value['resume']) if 'resume' in value else value['input']
            self.store.execute("UPDATE jobs SET status='running' WHERE generation=?", (row['generation'],))
            self.run(row['generation'], payload)

    def close(self):
        self.stop.set()
        self.wake.set()
        self.thread.join()  # Provider/adapter calls have bounded timeouts.

    def ensure_ready(self):
        if self.stop.is_set() or not self.thread.is_alive():
            from fastapi import HTTPException
            raise HTTPException(503, 'Runtime đang dừng hoặc cần khởi động lại. Job đã lưu được giữ nguyên.')
