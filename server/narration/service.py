"""One bounded worker. Durable attempts/jobs; no provider I/O inside DB transactions."""
from contextlib import contextmanager, nullcontext
import fcntl
import hashlib
import json
import logging
from pathlib import Path
import queue
import secrets
import sqlite3
import threading
import time

from fastapi import HTTPException
from openai import OpenAI
from server.tours.audio import decode_wav, summarize_audio
from .provider import OpenAISpeech, PROMPT_VERSION


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def positive(env, key, default=None):
    value=env.get(key,default)
    if not isinstance(value,str) or not value.isascii() or not value.isdecimal() or not 0<int(value)<=10000000:
        raise ValueError(f'{key}: require a positive integer')
    return int(value)


class NarrationService:
    def __init__(self, env, root, *, db, draft, check_revision, validate_doc,
                 object_storage=None, storage_guard=None, provider=None, clock=time.time):
        self.db,self.draft,self.check_revision,self.validate_doc=db,draft,check_revision,validate_doc
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.path=self.root/'narration.sqlite';self.clock=clock
        self.objects,self.storage=object_storage,storage_guard
        flag=env.get('NARRATION_ENABLED','0')
        if flag not in {'0','1'}:raise ValueError('NARRATION_ENABLED must be 0 or 1')
        self.enabled=flag=='1';self.client=None
        self.model=env.get('OPENAI_MODEL_TTS','gpt-4o-mini-tts')
        if not self.model or len(self.model)>100 or self.model!=self.model.strip():raise ValueError('OPENAI_MODEL_TTS must be non-empty, trimmed, at most 100 characters')
        self.max_chars=positive(env,'NARRATION_MAX_SCRIPT_CHARS','1200')
        if self.max_chars>2000:raise ValueError('NARRATION_MAX_SCRIPT_CHARS cannot exceed 2000')
        self.queue_size=positive(env,'NARRATION_QUEUE_SIZE','4')
        self.cache_age=positive(env,'NARRATION_CACHE_SECONDS','3600')
        self.attempts=positive(env,'NARRATION_ATTEMPTS') if self.enabled else 1
        self.characters=positive(env,'NARRATION_CHARACTERS') if self.enabled else 1
        self.window=positive(env,'NARRATION_WINDOW_SECONDS') if self.enabled else 3600
        self.timeout=positive(env,'NARRATION_TIMEOUT_SECONDS','30')
        if self.timeout>60:raise ValueError('NARRATION_TIMEOUT_SECONDS cannot exceed 60')
        key=(env.get('OPENAI_TTS_API_KEY') or '').strip()
        if self.enabled and provider is None and key:
            self.client=OpenAI(api_key=key,max_retries=0,timeout=self.timeout)
            provider=OpenAISpeech(self.client,self.model)
        self.provider=provider
        self.configured=self.enabled and provider is not None
        self.lock=threading.RLock();self.queue=queue.Queue(self.queue_size)
        self.thread=None;self.closed=False
        self.worker_lock=(self.root/'narration.worker.lock').open('a')
        try:fcntl.flock(self.worker_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.worker_lock.close()
            raise ValueError('Narration requires exactly one worker process per data root') from None
        with self.connect() as conn:
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,owner TEXT NOT NULL,request_id TEXT NOT NULL,
              fingerprint TEXT NOT NULL,cache_key TEXT NOT NULL,payload TEXT NOT NULL,created REAL NOT NULL,
              status TEXT NOT NULL,track TEXT,error TEXT,attachment TEXT,UNIQUE(owner,request_id));
            CREATE TABLE IF NOT EXISTS allowance(id INTEGER PRIMARY KEY,started REAL,highwater REAL,
              seconds INTEGER,attempts INTEGER,characters INTEGER);
            ''')
            row=conn.execute('SELECT seconds FROM allowance WHERE id=1').fetchone()
            if self.enabled and row and row[0]!=self.window:raise ValueError('NARRATION_WINDOW_SECONDS differs from persisted allowance')
            # Crash/timeout may already have incurred billing: never auto-retry after restart.
            conn.execute("UPDATE jobs SET status='error',error='interrupted_restart' WHERE status IN ('queued','running')")
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        with self.lock:
            conn=sqlite3.connect(self.path,timeout=5);conn.row_factory=sqlite3.Row
            try:
                with conn:yield conn
            finally:conn.close()

    def view(self,row):
        p=json.loads(row['payload'])
        return {'id':row['id'],'status':row['status'],'draft_id':p['draft_id'],'scene_id':p['scene_id'],
                'revision':p['revision'],'locale':p['locale'],'voice':p['voice'],'text':p['text'],
                'script_sha256':p['script_sha256'],'track':json.loads(row['track']) if row['track'] else None,
                'error':row['error'],'attached':bool(row['attachment'])}

    def owned(self,conn,id,who):
        row=conn.execute('SELECT * FROM jobs WHERE id=? AND owner=?',(id,who)).fetchone()
        if not row:raise HTTPException(404,'Narration job not found')
        return row

    def get(self,id,who):
        with self.connect() as conn:return self.view(self.owned(conn,id,who))

    def submit(self,data,who):
        if not self.configured:raise HTTPException(503,'Narration unavailable: enable NARRATION_ENABLED and configure OPENAI_TTS_API_KEY')
        if len(data.text)>self.max_chars:raise HTTPException(422,'Script exceeds configured character limit')
        payload=data.model_dump();fingerprint=digest({'payload':payload,'model':self.model,'prompt':PROMPT_VERSION})
        cache_key=digest({k:payload[k] for k in ('text','locale','voice')}|{'model':self.model,'prompt':PROMPT_VERSION})
        with self.connect() as conn:
            previous=conn.execute('SELECT * FROM jobs WHERE owner=? AND request_id=?',(who,data.request_id)).fetchone()
            if previous:
                if previous['fingerprint']!=fingerprint:raise HTTPException(409,'Request ID already used for another script/settings')
                return self.view(previous)
            if self.closed:raise HTTPException(503,'Narration worker is shutting down')
            with self.db() as tour:
                _,doc=self.draft(tour,data.draft_id,who);self.check_revision(doc,data.revision)
                if data.scene_id not in {s['id'] for s in doc['scenes']}:raise HTTPException(422,'Unknown scene')
            pending=conn.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
            if pending>=self.queue_size or self.queue.full():raise HTTPException(429,'Narration queue is full',headers={'Retry-After':'5'})
            now=self.clock()
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT * FROM allowance WHERE id=1').fetchone()
            if row:now=max(now,row['highwater'])
            start,attempts,chars=(row['started'],row['attempts'],row['characters']) if row else (now,0,0)
            if now>=start+self.window:start,attempts,chars=now,0,0
            if attempts>=self.attempts or chars+len(data.text)>self.characters:
                raise HTTPException(429,'Narration global attempt/character allowance exhausted',headers={'Retry-After':str(max(1,int(start+self.window-now)+1))})
            conn.execute('INSERT OR REPLACE INTO allowance VALUES(1,?,?,?,?,?)',(start,now,self.window,attempts+1,chars+len(data.text)))
            cached=conn.execute("SELECT track,created FROM jobs WHERE owner=? AND cache_key=? AND status='completed' AND created>=? AND track IS NOT NULL ORDER BY created DESC LIMIT 1",(who,cache_key,now-self.cache_age)).fetchone()
            id=secrets.token_hex(16);status='completed' if cached else 'queued'
            conn.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,NULL)',(id,who,data.request_id,fingerprint,cache_key,json.dumps(payload,ensure_ascii=False),cached['created'] if cached else now,status,cached['track'] if cached else None,None))
            conn.commit()
            if not cached:
                self.queue.put_nowait(id)
                if self.thread is None:
                    self.thread=threading.Thread(target=self._worker,name='narration-worker',daemon=True);self.thread.start()
            return self.view(self.owned(conn,id,who))

    def cancel(self,id,who):
        with self.connect() as conn:
            row=self.owned(conn,id,who)
            if row['attachment']:raise HTTPException(409,'Already attached; edit the draft audio explicitly')
            conn.execute("UPDATE jobs SET status='cancelled' WHERE id=?",(id,))
        return self.get(id,who)

    def _store(self,who,body,payload):
        normalized,measured=decode_wav(body)
        id=secrets.token_hex(16)
        track={'asset_id':id,'url':f'/api/tours/audio-assets/{id}',**measured,
               'source_label':'OpenAI generated tour narration','rights':'licensed',
               'rights_note':'AI-generated speech from Creator-approved text; sharing remains subject to provider terms.',
               'generation':{'provider':'openai','model':self.model,'voice':payload['voice'],
                 'locale':payload['locale'],'script_sha256':payload['script_sha256']}}
        key=f'tours/audio/{id}.wav';target=self.root/'audio'/f'{id}.wav';attempted=False
        # Provider has returned; reserve only the storage write, never hold it during generation.
        guard=self.storage() if callable(self.storage) else self.storage
        # Match the legacy upload lock order (tour DB mutex -> storage mutex).
        # Reversing this order can deadlock a concurrent upload and generated write.
        with self.db() as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS audio_assets(id TEXT PRIMARY KEY,owner TEXT NOT NULL,digest TEXT NOT NULL,metadata TEXT NOT NULL,UNIQUE(owner,digest))')
            if conn.execute('SELECT count(*) FROM audio_assets WHERE owner=?',(who,)).fetchone()[0]>=100:
                raise HTTPException(413,'Session audio limit reached (100)')
            with guard.reserve(4096 if self.objects else len(normalized)) if guard else nullcontext():
                try:
                    attempted=True
                    if self.objects:self.objects.put_bytes(key,normalized,'audio/wav')
                    else:
                        target.parent.mkdir(exist_ok=True,mode=0o700)
                        with target.open('xb') as out:out.write(normalized)
                        target.chmod(0o600)
                    # Unique ID/digest: approved-script cache is managed separately.
                    conn.execute('INSERT INTO audio_assets VALUES(?,?,?,?)',(id,who,digest(track),json.dumps(track)))
                    if self.objects:conn.execute("INSERT INTO media_storage VALUES('audio',?,'minio')",(id,))
                except BaseException:
                    if attempted:
                        if self.objects:
                            try:self.objects.remove(key)
                            except Exception:logging.getLogger(__name__).warning('Narration orphan cleanup failed; reconciliation required')
                        else:target.unlink(missing_ok=True)
                    raise
        return track

    def _worker(self):
        while True:
            id=self.queue.get()
            try:
                if id is None:return
                with self.connect() as conn:
                    row=conn.execute('SELECT * FROM jobs WHERE id=?',(id,)).fetchone()
                    if row['status']!='queued':continue
                    conn.execute("UPDATE jobs SET status='running' WHERE id=?",(id,))
                    payload=json.loads(row['payload']);who=row['owner']
                try:
                    with self.db() as tour:
                        _,doc=self.draft(tour,payload['draft_id'],who);self.check_revision(doc,payload['revision'])
                    body=self.provider.generate(payload['text'],payload['locale'],payload['voice'])
                    with self.connect() as conn:
                        if conn.execute('SELECT status FROM jobs WHERE id=?',(id,)).fetchone()[0]=='cancelled':continue
                    with self.db() as tour:
                        _,doc=self.draft(tour,payload['draft_id'],who);self.check_revision(doc,payload['revision'])
                    track=self._store(who,body,payload)
                    with self.connect() as conn:
                        conn.execute("UPDATE jobs SET status='completed',track=? WHERE id=? AND status='running'",(json.dumps(track),id))
                except Exception as error:
                    code='stale_revision' if isinstance(error,HTTPException) and error.status_code==409 else 'generation_failed'
                    with self.connect() as conn:
                        conn.execute("UPDATE jobs SET status='error',error=? WHERE id=? AND status='running'",(code,id))
                    # Never log upstream exception/body/script/IDs; failure is visible via job state.
            finally:self.queue.task_done()

    def attach(self,id,who,revision):
        with self.connect() as conn:
            row=self.owned(conn,id,who);payload=json.loads(row['payload'])
            if row['attachment']:
                previous=json.loads(row['attachment'])
                if previous['input_revision']!=revision:raise HTTPException(409,'Attachment request revision differs')
                return previous['manifest']
            if row['status']!='completed':raise HTTPException(409,'Generate and preview a completed clip before attaching')
            if revision!=payload['revision']:raise HTTPException(409,'Script review belongs to a different draft revision')
            track=json.loads(row['track'])
            if self.objects:self.objects.stat(f'tours/audio/{track["asset_id"]}.wav')
            elif not (self.root/'audio'/f'{track["asset_id"]}.wav').is_file():raise HTTPException(404,'Generated audio missing')
            with self.db() as tour:
                _,doc=self.draft(tour,payload['draft_id'],who)
                # Reconcile a crash after draft commit but before job attachment record.
                existing=next((n for n in doc['audio'].get('narration') or [] if n['scene_id']==payload['scene_id'] and n['locale']==payload['locale']),None)
                reconciled=doc['revision']==revision+1 and existing and existing['track']['asset_id']==track['asset_id']
                if not reconciled:
                    self.check_revision(doc,revision)
                    if payload['scene_id'] not in {s['id'] for s in doc['scenes']}:raise HTTPException(422,'Scene no longer exists')
                    narrations=[n for n in doc['audio'].get('narration') or [] if (n['scene_id'],n['locale'])!=(payload['scene_id'],payload['locale'])]
                    narrations.append({'scene_id':payload['scene_id'],'locale':payload['locale'],'transcript':payload['text'],'track':track})
                    doc['audio']['narration']=narrations;doc['revision']+=1
                    doc=self.validate_doc(summarize_audio(doc))
                    tour.execute('UPDATE drafts SET doc=?,reviewed=NULL WHERE id=?',(json.dumps(doc),payload['draft_id']))
            conn.execute('UPDATE jobs SET attachment=? WHERE id=?',(json.dumps({'input_revision':revision,'manifest':doc}),id))
            return doc

    def close(self):
        with self.lock:
            if self.closed:return
            self.closed=True
        if self.thread:
            # Drain pending tasks as explicit failures; never silently resume them on restart.
            with self.connect() as conn:conn.execute("UPDATE jobs SET status='cancelled' WHERE status='queued'")
            self.queue.put(None)
            self.thread.join(timeout=self.timeout+10)
            if self.thread.is_alive():raise RuntimeError('Narration worker did not stop; do not start another worker')
        if self.client:self.client.close()
        self.worker_lock.close()
