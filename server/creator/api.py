import asyncio
import json
import re
import secrets
import hashlib
import struct
import wave
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from .models import ProjectInput, Action, Review, EditRequest, ApplyEdit
from .store import image_info, wav_duration, sanitize_image
from server.storage import upload_reservation
from .music import replace_music, PLACEHOLDER, CREDIT

COOKIE = 'estagent_studio'


def router(origin):
    routes = APIRouter(prefix='/api/studio')

    def creator(request):
        return request.app.state.creator

    def owner(request, response=None):
        value = request.cookies.get(COOKIE, '')
        if not re.fullmatch(r'[a-f0-9]{64}', value):
            if response is None:
                raise HTTPException(401, 'Reload Studio to start a session.')
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

    @routes.get('/health')
    def health(request: Request):
        service = creator(request)
        service.queue.ensure_ready()
        service.store.rows('SELECT 1')
        return {'ready':True, 'mode':'single-host-sqlite', 'geometry_configured':service.worker is not None}

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
            raise HTTPException(422, 'Invalid file information.')
        data = await request.body()
        try:
            if kind == 'music':
                if not credit.strip():
                    raise ValueError('Enter the music source and usage rights.')
                mime, width, height = 'audio/wav', 0, 0
                duration = wav_duration(data)
            else:
                data = sanitize_image(data)
                mime, width, height = image_info(data)
                duration = None
        except (ValueError, EOFError, IndexError, struct.error, wave.Error) as error:
            raise HTTPException(422, str(error)) from None
        # Serialize validation and insert with generate/input freeze.
        with service.store.lock:
            if kind == 'music':
                return replace_music(service.store, project_id, name, data, credit.strip())
            if service.store.rows('SELECT id FROM generations WHERE project=?', (project_id,)):
                raise HTTPException(409, 'Inputs are locked once tour generation starts.')
            assets = service.store.assets(project_id)
            digest = hashlib.sha256(data).hexdigest()
            duplicate = next((a for a in assets if a['sha256'] == digest and a['kind'] == kind), None)
            if duplicate:
                return duplicate
            if sum(a['size'] for a in assets) + len(data) > 80*1024*1024:
                raise HTTPException(413, 'The project exceeds the 80 MB limit.')
            if sum(a['kind'] == kind for a in assets) >= (12 if kind == 'panorama' else 1):
                raise HTTPException(422, 'The file limit for this type has been reached.')
            projection = 'equirectangular' if project.get('panorama_confirmed') and kind == 'panorama' and abs(width/height-2) <= .15 else 'photo'
            with upload_reservation(request,4096 if service.store.object_storage else len(data)):
                return service.store.put_asset(project_id, name, kind, mime, data,
                    {**({'projection': projection} if kind == 'panorama' else {}),
                     'width': width, 'height': height, 'duration': duration, 'credit': credit.strip(),
                     'warning': 'This image does not have a 2:1 panorama ratio; please check it.' if kind == 'panorama' and abs(width/height-2) > .15 else None})

    @routes.post('/projects/{project_id}/music/placeholder')
    def placeholder(project_id: str, data: Action, request: Request):
        service = creator(request)
        token = owner(request)
        service.store.project(token, project_id)
        return service.store.action(token, data.request_id, {'placeholder_music':project_id},
            lambda: replace_music(service.store,project_id,'Dream Culture (demo excerpt)',
                                  PLACEHOLDER.read_bytes(),CREDIT))

    @routes.delete('/projects/{project_id}/assets/{asset_id}')
    def remove(project_id: str, asset_id: str, request: Request):
        service = creator(request)
        service.store.project(owner(request), project_id)
        with service.store.lock:
            asset = next((a for a in service.store.assets(project_id) if a['id']==asset_id), None)
            if service.store.rows('SELECT id FROM published WHERE project=?', (project_id,)) or (
                (not asset or asset['kind'] != 'music') and
                service.store.rows('SELECT id FROM generations WHERE project=?', (project_id,))):
                raise HTTPException(409, 'Inputs are locked once tour generation starts.')
            service.store.execute('DELETE FROM assets WHERE id=? AND project=?', (asset_id, project_id))
        return {'removed': True}

    @routes.get('/projects/{project_id}/assets/{asset_id}')
    def asset(project_id: str, asset_id: str, request: Request):
        service = creator(request)
        service.store.project(owner(request), project_id)
        found = next((a for a in service.store.assets(project_id) if a['id'] == asset_id), None)
        if not found:
            raise HTTPException(404, 'File not found.')
        return service.store.response(found,range_header=request.headers.get('range'))

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

    @routes.post('/generations/{generation_id}/edits')
    def propose_edit(generation_id: str, data: EditRequest, request: Request):
        return creator(request).propose_edit(owner(request), generation_id, data)

    @routes.get('/generations/{generation_id}/edits')
    def edits(generation_id: str, request: Request):
        service = creator(request)
        token = owner(request)
        service.generation(token, generation_id)
        return [{'id':r['id'], 'revision':r['revision'], 'status':r['status'], **json.loads(r['data'])}
                for r in service.store.rows('SELECT * FROM edits WHERE generation=? AND owner=? ORDER BY rowid DESC LIMIT 20', (generation_id, token))]

    @routes.post('/generations/{generation_id}/edits/{edit_id}/apply', status_code=202)
    def apply_edit(generation_id: str, edit_id: str, data: ApplyEdit, request: Request):
        return creator(request).apply_edit(owner(request), generation_id, edit_id, data)

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
            raise HTTPException(422, 'Invalid event cursor.') from None
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
