"""Bounded tour text / STT / TTS. Existing tours API owns session and turn storage."""
import hashlib,json,sqlite3,threading
from contextlib import contextmanager
from pathlib import Path
from fastapi import HTTPException
from openai import OpenAI
from server.file_lock import acquire,release
from server.limits import AttemptLedger,Group,Window,_positive
from server.tours.audio import decode_wav
from .graph import build_graph
from .provider import Provider

class Service:
    def __init__(self,env,root,interpreter=None,provider=None):
        self.root=Path(root)/'visitor-chat';self.root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.enabled=env.get('TOUR_CHAT_ENABLED','0')=='1'
        if env.get('TOUR_CHAT_ENABLED','0') not in {'0','1'}:raise ValueError('TOUR_CHAT_ENABLED must be 0 or 1')
        groups={kind:Group(1,(Window(kind,_positive(env,'TOUR_CHAT_'+kind.upper()+'_ATTEMPTS'),86400),)) for kind in ['text','stt','tts']} if self.enabled else {}
        self.client=None;key=(env.get('OPENAI_TOUR_API_KEY') or '').strip()
        if self.enabled and key and provider is None:
            self.client=OpenAI(api_key=key,base_url='https://api.openai.com/v1',max_retries=0,timeout=30);provider=Provider(self.client,env)
        self.provider=provider;self.configured=self.enabled and bool(provider or interpreter);self.voice_configured=self.enabled and provider is not None
        self.graph=build_graph(interpreter or provider.answer) if self.configured else None
        self.semaphore=threading.BoundedSemaphore(1);self.lock=threading.RLock()
        self.path=self.root/'requests.sqlite'
        with self.db() as db:db.execute('CREATE TABLE IF NOT EXISTS requests(scope TEXT,id TEXT,fingerprint TEXT,status TEXT,result TEXT,PRIMARY KEY(scope,id))')
        self.path.chmod(0o600)
        self.ledger=AttemptLedger(self.root/'allowance.sqlite',groups) if self.enabled else None
    @contextmanager
    def db(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
            try:
                with db:yield db
            finally:db.close()
    @contextmanager
    def admission(self,kind):
        if not self.configured or kind!='text' and not self.voice_configured:raise HTTPException(503,'Trợ lý chưa được kết nối / Configure TOUR_CHAT_ENABLED and OPENAI_TOUR_API_KEY.')
        if not self.semaphore.acquire(blocking=False):raise HTTPException(429,'Trợ lý đang xử lý yêu cầu khác / Please retry shortly.',headers={'Retry-After':'3'})
        handle=None;held=False
        try:
            handle=(self.root/'provider.lock').open('a+b')
            try:acquire(handle);held=True
            except BlockingIOError:raise HTTPException(429,'Trợ lý đang bận / Assistant busy',headers={'Retry-After':'3'}) from None
            try:denied=self.ledger.reserve(kind)
            except (sqlite3.Error,OSError,ValueError):raise HTTPException(503,'Usage ledger unavailable') from None
            if denied:raise HTTPException(429,'Đã hết giới hạn hôm nay / Daily allowance exhausted.',headers={'Retry-After':str(denied[1])})
            yield
        finally:
            if handle:
                if held:release(handle)
                handle.close()
            self.semaphore.release()
    def answer(self,context):return self.graph.invoke({'context':context})['result']
    def cached(self,scope,id,fingerprint):
        with self.db() as db:
            row=db.execute('SELECT * FROM requests WHERE scope=? AND id=?',(scope,id)).fetchone()
            if row:
                if row['fingerprint']!=fingerprint:raise HTTPException(409,'Request ID payload differs')
                if row['status']!='completed':raise HTTPException(409,'Earlier attempt did not complete; no automatic retry')
                return json.loads(row['result'])
        return None
    def record(self,scope,id,fingerprint,status,result=None):
        with self.db() as db:db.execute('INSERT OR REPLACE INTO requests VALUES(?,?,?,?,?)',(scope,id,fingerprint,status,json.dumps(result) if result is not None else None))
    def transcribe(self,scope,id,body,locale):
        wav,info=decode_wav(body)
        if info['duration_seconds']>20 or info['channels']!=1 or info['sample_rate']!=16000:raise HTTPException(422,'Record at most 20 seconds, mono 16 kHz WAV')
        fingerprint=hashlib.sha256(locale.encode()+wav).hexdigest();cached=self.cached(scope,id,fingerprint)
        if cached is not None:return cached
        with self.admission('stt'):
            cached=self.cached(scope,id,fingerprint)
            if cached is not None:return cached
            self.record(scope,id,fingerprint,'started')
            try:result={'text':self.provider.transcribe(wav,locale)}
            except Exception:
                self.record(scope,id,fingerprint,'error');raise HTTPException(502,'Không nhận được lời nói / Transcription failed.') from None
            self.record(scope,id,fingerprint,'completed',result);return result
    def speech(self,scope,id,text,locale):
        if len(text)>800:raise HTTPException(422,'Response is too long for voice; read the text instead')
        fingerprint=hashlib.sha256((text+'\n'+locale+'\n'+getattr(self.provider,'tts_model','fixture')+'\ncoral').encode()).hexdigest();cached=self.cached(scope,id,fingerprint)
        if cached is not None:return (self.root/cached['file']).read_bytes()
        with self.admission('tts'):
            cached=self.cached(scope,id,fingerprint)
            if cached is not None:return (self.root/cached['file']).read_bytes()
            self.record(scope,id,fingerprint,'started')
            try:
                wav,_=decode_wav(self.provider.speech(text,locale));name=hashlib.sha256((scope+id+fingerprint).encode()).hexdigest()+'.wav';p=self.root/name;p.write_bytes(wav);p.chmod(0o600)
            except Exception:
                self.record(scope,id,fingerprint,'error');raise HTTPException(502,'Không tạo được giọng / Voice response failed.') from None
            self.record(scope,id,fingerprint,'completed',{'file':name});return wav
    def close(self):
        if self.client:self.client.close()
