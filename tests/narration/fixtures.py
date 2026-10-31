"""Actual API/SQLite/MinIO adapter; SDK fixture emits a tone, NOT speech."""
import importlib
import math
import struct
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from server.narration.api import install_narration
from server.narration.provider import OpenAISpeech
from server.object_storage import MinioStorage
from tests.ai.test_object_storage import Client

ENV={'NARRATION_ENABLED':'1','NARRATION_ATTEMPTS':'30','NARRATION_CHARACTERS':'10000',
     'NARRATION_WINDOW_SECONDS':'3600','NARRATION_CACHE_SECONDS':'60',
     'ASSISTANT_ORIGIN':'http://testserver'}
class SpeechSDK:
    def __init__(self):
        self.calls=[];self.entered=threading.Event();self.release=None;self.failure=False
        self.audio=SimpleNamespace(speech=SimpleNamespace(with_streaming_response=self))
    @contextmanager
    def create(self,**kwargs):
        self.calls.append(kwargs);self.entered.set()
        if self.release is not None:assert self.release.wait(8),'fixture release timed out'
        if self.failure:raise RuntimeError('PRIVATE upstream details')
        pcm=b''.join(struct.pack('<h',int(2000*math.sin(i*2*math.pi*440/24000))) for i in range(24000))
        yield SimpleNamespace(iter_bytes=lambda **kw:iter([pcm]))

def build(root,env=None,sdk=None,clock=None):
    env=ENV| (env or {});sdk=sdk or SpeechSDK();objects=Client();holder=[]
    module=importlib.import_module('server.assistant.app');tours=importlib.import_module('server.tours.api')
    original=tours.install_audio
    def hook(router,db,owner,draft,check_revision,validate_doc,published,data_root,**kwargs):
        verify=original(router,db,owner,draft,check_revision,validate_doc,published,data_root,**kwargs)
        service=install_narration(router,db,owner,draft,check_revision,validate_doc,data_root,env,
            object_storage=kwargs.get('object_storage'),provider=OpenAISpeech(sdk,env.get('OPENAI_MODEL_TTS','gpt-4o-mini-tts')) if env.get('FIXTURE_PROVIDER','1')=='1' else None,clock=clock)
        holder.append(service);return verify
    with patch.object(module,'create_object_storage',lambda _:MinioStorage(objects,'fixture')),patch.object(tours,'install_audio',hook):
        app=module.create_app(db_path=root/'assistant.sqlite',env=env)
    holder[0].storage=app.state.storage_limits
    return app,holder[0],sdk,objects
