import asyncio
import json
import re
import secrets
import hashlib
import struct
import wave
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from .models import ProjectInput, Action, Review
from .store import image_info, wav_duration
from server.storage import upload_reservation

COOKIE = 'estagent_studio'


def router(origin):
    routes = APIRouter(prefix='/api/studio')

    def creator(request):
        return request.app.state.creator

    def owner(request, response=None):
        value = request.cookies.get(COOKIE, '')
        if not re.fullmatch(r'[a-f0-9]{64}', value):
            if response is None:
                raise HTTPException(401, 'Tải lại Studio để bắt đầu phiên.')
            value = secrets.token_hex(32)
            response.set_cookie(COOKIE, value, path='/api/studio/', httponly=True,
                secure=origin.startswith('https:'), samesite='strict', max_age=30*24*3600)
        return value

    @routes.get('/session')
    def session(request: Request, response: Response):
        token = owner(request, response)
        service = creator(request)
        projects = [json.loads(r['data']) for r in service.store.rows('SELECT data FROM projects WHERE owner=? ORDER BY rowid DESC', (token,))]
        return {'configured': service.provider is not None, 'geometry_configured': service.worker is not None,
                'projects': [{k: p[k] for k in ('id', 'name', 'created_at')} for p in projects]}

    @routes.post('/projects', status_code=201)
    def create(data: ProjectInput, request: Request):
        return creator(request).create(owner(request), data)

    @routes.get('/projects/{project_id}')
    def project(project_id: str, request: Request):
        return creator(request).project(owner(request), project_id)

    @routes.post('/projects/{project_id}/assets', status_code=201)
    async def upload(project_id: str, request: Request, kind: str = 'panorama', name: str = 'image', credit: str = ''):
        service = creator(request)
        token = owner(request)
        project = service.store.project(token, project_id)
        if kind not in ('panorama', 'floorplan', 'music') or not 1 <= len(name) <= 150 or len(credit) > 300:
            raise HTTPException(422, 'Thông tin tệp không hợp lệ.')
        data = await request.body()
        try:
            if kind == 'music':
                if not credit.strip():
                    raise ValueError('Nhập nguồn và quyền sử dụng nhạc nền.')
                mime, width, height = 'audio/wav', 0, 0
                duration = wav_duration(data)
            else:
                mime, width, height = image_info(data)
                duration = None
        except (ValueError, EOFError, IndexError, struct.error, wave.Error) as error:
            raise HTTPException(422, str(error)) from None
        # Serialize validation and insert with generate/input freeze.
        with service.store.lock:
            if service.store.rows('SELECT id FROM generations WHERE project=?', (project_id,)):
                raise HTTPException(409, 'Đầu vào đã khóa khi bắt đầu tạo tour.')
            assets = service.store.assets(project_id)
            digest = hashlib.sha256(data).hexdigest()
            duplicate = next((a for a in assets if a['sha256'] == digest and a['kind'] == kind), None)
            if duplicate:
                return duplicate
            if sum(a['size'] for a in assets) + len(data) > 80*1024*1024:
                raise HTTPException(413, 'Project vượt giới hạn 80 MB.')
            if sum(a['kind'] == kind for a in assets) >= (12 if kind == 'panorama' else 1):
                raise HTTPException(422, 'Đã đạt giới hạn tệp của loại này.')
            projection = 'equirectangular' if project.get('panorama_confirmed') and kind == 'panorama' and abs(width/height-2) <= .15 else 'photo'
            with upload_reservation(request,len(data)):
                return service.store.put_asset(project_id, name, kind, mime, data,
                    {**({'projection': projection} if kind == 'panorama' else {}),
                     'width': width, 'height': height, 'duration': duration, 'credit': credit.strip(),
                     'warning': 'Ảnh không có tỷ lệ panorama 2:1; hãy kiểm tra.' if kind == 'panorama' and abs(width/height-2) > .15 else None})

    @routes.delete('/projects/{project_id}/assets/{asset_id}')
    def remove(project_id: str, asset_id: str, request: Request):
        service = creator(request)
        service.store.project(owner(request), project_id)
        with service.store.lock:
            if service.store.rows('SELECT id FROM generations WHERE project=?', (project_id,)):
                raise HTTPException(409, 'Đầu vào đã khóa khi bắt đầu tạo tour.')
            service.store.execute('DELETE FROM assets WHERE id=? AND project=?', (asset_id, project_id))
        return {'removed': True}

    @routes.get('/projects/{project_id}/assets/{asset_id}')
    def asset(project_id: str, asset_id: str, request: Request):
        service = creator(request)
        service.store.project(owner(request), project_id)
        found = next((a for a in service.store.assets(project_id) if a['id'] == asset_id), None)
        if not found:
            raise HTTPException(404, 'Không tìm thấy tệp.')
        return Response(service.store.content(found), media_type=found['mime'])

    @routes.post('/projects/{project_id}/generations', status_code=202)
    def generate(project_id: str, data: Action, request: Request):
        return creator(request).start(owner(request), project_id, data.request_id)

    @routes.get('/generations/{generation_id}')
    def generation(generation_id: str, request: Request):
        return creator(request).generation(owner(request), generation_id)

    @routes.post('/generations/{generation_id}/review', status_code=202)
    def review(generation_id: str, data: Review, request: Request):
        return creator(request).resume(owner(request), generation_id, data)

    @routes.post('/generations/{generation_id}/retry', status_code=202)
    def retry(generation_id: str, data: Action, request: Request):
        return creator(request).retry(owner(request), generation_id, data.request_id)

    @routes.post('/generations/{generation_id}/publish')
    def publish(generation_id: str, data: Action, request: Request):
        return creator(request).publish(owner(request), generation_id, data.request_id)

    @routes.get('/generations/{generation_id}/events')
    async def events(generation_id: str, request: Request, after: int = 0):
        service = creator(request)
        token = owner(request)
        service.generation(token, generation_id)
        try:
            cursor = max(after, int(request.headers.get('last-event-id', '0')))
            if cursor < 0:
                raise ValueError('Negative cursor')
        except ValueError:
            raise HTTPException(422, 'Event cursor không hợp lệ.') from None
        async def stream():
            nonlocal cursor
            while not await request.is_disconnected():
                for event in service.store.events(generation_id, cursor):
                    cursor = event['event_id']
                    yield f"id: {cursor}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                state = service.store.rows('SELECT status FROM generations WHERE id=?', (generation_id,))[0]['status']
                if state not in ('queued', 'running'):
                    # Drain once more if the worker committed its last event meanwhile.
                    for event in service.store.events(generation_id, cursor):
                        cursor = event['event_id']
                        yield f"id: {cursor}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"
                    yield 'event: settled\ndata: {}\n\n'
                    break
                yield ': heartbeat\n\n'
                await asyncio.sleep(.5)
        return StreamingResponse(stream(), media_type='text/event-stream',
            headers={'X-Accel-Buffering': 'no', 'Cache-Control': 'no-store'})

    return routes
