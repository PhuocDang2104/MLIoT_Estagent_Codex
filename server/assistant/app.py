"""Run locally: python3 -m uvicorn server.assistant.app:app --host 127.0.0.1 --port 5180."""
import json
import os
import re
import secrets
import sqlite3
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI, APIError
from pydantic import BaseModel, Field, ConfigDict
from langgraph.checkpoint.sqlite import SqliteSaver
from starlette.concurrency import run_in_threadpool
from .graph import build_graph, make_extractor, LABELS, QUESTIONS

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / 'web'
COOKIE = 'estagent_assistant'

class Turn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(pattern=r'^[a-zA-Z0-9-]{8,80}$')

def create_app(*, db_path=None, extractor=None, env=None, voice_transport=None):
    env = dict(os.environ if env is None else env)
    origin = env.get('ASSISTANT_ORIGIN', 'http://127.0.0.1:5180')
    required = tuple(x.strip() for x in env.get('ASSISTANT_REQUIRED_FIELDS','address,area,bedrooms').split(','))
    key = env.get('OPENAI_API_KEY')
    configured = bool(extractor or key)
    path = Path(db_path or env.get('ASSISTANT_DB', ROOT / 'projects/assistant/work/checkpoints.sqlite'))
    lock = threading.RLock()  # One local worker; serialize checkpoint writes and duplicate requests.

    @asynccontextmanager
    async def lifespan(app):
        path.parent.mkdir(parents=True,exist_ok=True)
        connection = sqlite3.connect(path,check_same_thread=False)
        os.chmod(path,0o600)
        saver = SqliteSaver(connection)
        client = OpenAI(api_key=key,max_retries=0,timeout=30) if key else None
        def unavailable(_): raise ValueError('Cần cấu hình OpenAI ở máy chủ để tiếp tục.')
        graph = build_graph(extractor or (make_extractor(client,env.get('OPENAI_MODEL_TEXT','gpt-6.1-sol')) if client else unavailable),saver,required)
        app.state.graph = graph
        yield
        if client: client.close()
        connection.close()

    app = FastAPI(lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)

    @app.middleware('http')
    async def boundaries(request, call_next):
        if request.url.path.startswith('/api/assistant/'):
            if request.method == 'POST' and request.headers.get('origin') != origin:
                return JSONResponse({'error':'Nguồn yêu cầu không hợp lệ.'},status_code=403)
            if request.method == 'POST':
                size = 0; chunks = []
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > 65536: return JSONResponse({'error':'Yêu cầu quá lớn.'},status_code=413)
                    chunks.append(chunk)
                request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def session(request, response, create=False):
        token = request.cookies.get(COOKIE,'')
        if not re.fullmatch(r'[a-f0-9]{64}',token):
            if not create: raise HTTPException(401,'Hãy tải lại trang để bắt đầu phiên trò chuyện.')
            token = secrets.token_hex(32)
            response.set_cookie(COOKIE,token,httponly=True,samesite='strict',secure=origin.startswith('https:'),max_age=30*24*3600,path='/api/assistant/')
        return {'configurable':{'thread_id':token}}

    def public(state):
        return {**{k:state.get(k,default) for k,default in [('profile',{}),('deferred',[]),('history',[]),('awaiting',required[0]),('stage','required'),('confirmed',False)]},
                'reply':state.get('reply','Mình sẽ giúp bạn tạo hồ sơ căn hộ, từng thông tin một. '+QUESTIONS[required[0]]),
                'required':list(required),'labels':LABELS,'configured':configured}

    @app.get('/api/assistant/state')
    def state(request:Request,response:Response):
        config = session(request,response,True)
        with lock: values = app.state.graph.get_state(config).values
        return public(values)

    @app.post('/api/assistant/turn')
    def turn(data:Turn,request:Request,response:Response):
        config = session(request,response)
        if not configured: return JSONResponse({'error':'Trợ lý chưa được kết nối. Cần cấu hình OpenAI ở máy chủ.'},status_code=503)
        text = data.text.strip()
        if not text: raise HTTPException(422,'Câu trả lời đang trống.')
        try:
            with lock:
                before = app.state.graph.get_state(config).values
                if before.get('last_request_id') == data.request_id: return public(before)
                values = app.state.graph.invoke({'text':text,'request_id':data.request_id},config)
            return public(values)
        except APIError as error:
            status = 429 if getattr(error,'status_code',None) == 429 else 502
            return JSONResponse({'error':'OpenAI chưa xử lý được yêu cầu. Kiểm tra quyền model/quota hoặc thử lại sau.'},status_code=status)
        except ValueError:
            return JSONResponse({'error':'Chưa hiểu chắc chắn câu trả lời. Bạn thử diễn đạt lại nhé.'},status_code=502)

    @app.post('/api/assistant/voice')
    async def voice(request:Request,response:Response):
        session(request,response)
        if not key: return JSONResponse({'error':'Giọng nói chưa được kết nối với OpenAI.'},status_code=503)
        if not request.headers.get('content-type','').startswith('application/sdp'): raise HTTPException(415,'Cần SDP.')
        sdp = (await request.body()).decode('utf8',errors='replace')
        if not sdp.startswith('v=0') or 'm=audio' not in sdp: raise HTTPException(400,'SDP không hợp lệ.')
        settings = {
            'type':'realtime','model':env.get('OPENAI_MODEL_REALTIME','gpt-realtime-2.1'),
            'instructions':'Bạn là giọng đọc AI của Estagent. Chỉ đọc nguyên văn văn bản được cung cấp bằng tiếng Việt. Không tự trả lời, không thêm dữ kiện.',
            'max_output_tokens':512,
            'audio':{'input':{
                'transcription':{'model':env.get('OPENAI_MODEL_TRANSCRIBE','gpt-transcribe')},
                'turn_detection':{'type':'server_vad','create_response':False,'interrupt_response':False}},
                'output':{'voice':'marin'}},
        }
        try:
            async with httpx.AsyncClient(timeout=30,transport=voice_transport) as client:
                upstream = await client.post('https://api.openai.com/v1/realtime/calls',headers={'Authorization':f'Bearer {key}'},files={'sdp':(None,sdp),'session':(None,json.dumps(settings))})
            if upstream.status_code >= 400:
                return JSONResponse({'error':'Chưa kết nối được giọng nói. Kiểm tra quyền model và quota OpenAI.'},status_code=429 if upstream.status_code == 429 else 502)
            if not upstream.text.startswith('v=0'): raise ValueError('Invalid SDP')
            return Response(upstream.text,media_type='application/sdp')
        except (httpx.HTTPError,ValueError):
            return JSONResponse({'error':'Kết nối giọng nói bị gián đoạn. Bạn vẫn có thể chat chữ.'},status_code=502)

    @app.get('/')
    def home(): return FileResponse(WEB/'assistant.html')

    @app.get('/{filename}')
    def static_file(filename:str):
        allowed = {'assistant.html','assistant.css','assistant.js','index.html','experience.html','styles.css','app.js','i18n.js','intake.js','property.js'}
        if filename not in allowed or not (WEB/filename).is_file(): raise HTTPException(404)
        return FileResponse(WEB/filename)

    app.mount('/assets',StaticFiles(directory=WEB/'assets'),name='assets')
    return app

app = create_app()
