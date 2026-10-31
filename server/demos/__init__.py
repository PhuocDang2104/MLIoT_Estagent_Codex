"""Read-only catalog for the explicitly supplied cached home; no ZIP/file gateway."""
import json
import math
from pathlib import Path
import re
from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse
from server.object_storage import ObjectResponse

DEMO_ID = 'zind-house-000'
BUNDLE_SHA = '734f7053604b67c24701acff3a044e2d33241272149e9596b0eefdca5fc592e3'
SEOUL_ID = 'seoul-apartment'
SEOUL_SHA = '254d6bc4a53ac452e07247b05b1418066f7ad4546a072e0ed1325a099e5b8d58'
TYPES = {'image/jpeg', 'image/png', 'image/svg+xml', 'model/gltf-binary',
         'application/javascript', 'text/css', 'application/json', 'audio/wav'}


def read_catalog(path, demo_id=DEMO_ID, bundle_sha=BUNDLE_SHA):
    try:
        doc = json.loads(Path(path).read_text())
        if doc['id'] != demo_id or doc['source_bundle_sha256'] != bundle_sha:
            raise ValueError()
        export_types = {'.mp4': 'video/mp4', '.txt': 'text/plain', '.vtt': 'text/vtt'} if demo_id == SEOUL_ID else {}
        for name, asset in doc['assets'].items():
            if (not re.fullmatch(r'(?:runtime|house)/[A-Za-z0-9_./-]+', name)
                    or any(p in {'', '.', '..'} for p in name.split('/'))
                    or not name.endswith(('.js', '.css', '.json', '.jpg', '.png', '.svg', '.glb', '.wav', *export_types))
                    or not re.fullmatch('[a-f0-9]{64}', asset['sha256'])
                    or asset['key'] != f'demos/{demo_id}/{asset["sha256"]}/{name}'
                    or asset['content_type'] not in TYPES | set(export_types.values()) or not isinstance(asset['bytes'], int)
                    or asset['bytes'] <= 0):
                raise ValueError()
        if not {'house/manifest.json', 'house/dollhouse-studio.glb'} <= doc['assets'].keys():
            raise ValueError()
        if doc['thumbnail'] not in doc['assets']:
            raise ValueError()
        if 'exports' in doc:
            package = doc['exports']
            if (demo_id != SEOUL_ID or package['locale'] != 'en'
                    or package['scope'] != 'seoul_sample_only'
                    or package['voice_source'] != 'openai_generated'
                    or package['voice_model'] != 'gpt-4o-mini-tts'
                    or not math.isfinite(package['duration_seconds'])
                    or not 1 <= package['duration_seconds'] <= 600):
                raise ValueError()
            for kind, extension, mime in [('video', 'mp4', 'video/mp4'), ('audio', 'wav', 'audio/wav'),
                    ('transcript', 'txt', 'text/plain'), ('captions', 'vtt', 'text/vtt')]:
                name = package[kind]
                if name != f'house/exports/seoul-tour-en.{extension}' or doc['assets'][name]['content_type'] != mime:
                    raise ValueError()
            ids = ['00000000', '00000030', '00000070', '00000110', '00000150', '00000180', '00000250', '00000310']
            if [c['capture_id'] for c in package['chapters']] != ids:
                raise ValueError()
            previous_end = 0
            for chapter in package['chapters']:
                start, duration = chapter['start'], chapter['duration']
                if (not math.isfinite(start) or not math.isfinite(duration) or start < previous_end - .01
                        or duration <= 0 or start + duration > package['duration_seconds'] + .1
                        or not isinstance(chapter['text'], str) or not 1 <= len(chapter['text']) <= 2000
                        or not isinstance(chapter['title'], str) or not 1 <= len(chapter['title']) <= 120):
                    raise ValueError()
                previous_end = start + duration
        locales=set()
        for item in doc.get('intro', []):
            if (item['locale'] not in {'en','vi'} or item['locale'] in locales
                    or item['asset'] != f"house/intro/{item['locale']}.wav"
                    or item['asset'] not in doc['assets']
                    or item['sha256'] != doc['assets'][item['asset']]['sha256']
                    or item['source'] != 'openai_generated'
                    or item['scope'] != 'neutral_tour_intro_not_room_specific'):
                raise ValueError()
            locales.add(item['locale'])
        guide_keys=set()
        for item in doc.get('guide', []):
            pair=(item['capture_id'],item['locale'])
            if (item['locale'] not in {'en','vi'} or pair in guide_keys
                    or not re.fullmatch(r'pano_[0-9]+', item['capture_id'])
                    or not re.fullmatch(r'complete_room_[0-9]+', item['room_id'])
                    or item['asset'] not in doc['assets']
                    or doc['assets'][item['asset']]['content_type'] != 'audio/wav'
                    or item['sha256'] != doc['assets'][item['asset']]['sha256']
                    or item['source'] != 'openai_generated'):
                raise ValueError()
            guide_keys.add(pair)
        return doc
    except (OSError, ValueError, TypeError, KeyError):
        raise ValueError('DEMO_CATALOG_PATH: missing or invalid allowlisted demo catalog') from None


def install_demos(app, env, web):
    raw = env.get('DEMO_CATALOG_PATH', '')
    catalog = read_catalog(raw) if raw else None
    seoul_path = env.get('SEOUL_CATALOG_PATH', '')
    seoul = read_catalog(seoul_path, SEOUL_ID, SEOUL_SHA) if seoul_path else None
    catalogs = {key: value for key, value in [(DEMO_ID, catalog), (SEOUL_ID, seoul)] if value}
    if catalogs and app.state.object_storage is None:
        raise ValueError('Cached demo requires configured private MinIO storage')

    @app.get('/api/demos')
    def catalog_list():
        result = []
        if catalog:
            result.append({'id': DEMO_ID, 'kind': 'cached_demo', 'title': 'DEMO HOUSE — Sample home 000',
                 'href': f'/demos/{DEMO_ID}', 'thumbnail_url': f'/api/demos/{DEMO_ID}/assets/{catalog["thumbnail"]}',
                 'rooms': 15, 'captures': 32, 'markers': 16, 'source_mode': 'user_provided_cached',
                 'rights_status': 'not_independently_verified', 'audio_available': bool(catalog.get('intro'))})
        if seoul:
            result.append({'id': SEOUL_ID, 'kind': 'cached_demo', 'title': 'SEOUL — Furnished apartment',
                 'href': f'/demos/{SEOUL_ID}', 'thumbnail_url': f'/api/demos/{SEOUL_ID}/assets/{seoul["thumbnail"]}',
                 'rooms': 6, 'captures': 8, 'markers': 5, 'source_mode': 'user_provided_cached',
                 'rights_status': 'not_independently_verified', 'audio_available': bool(seoul.get('exports'))})
        return result

    @app.get('/api/demos/{demo_id}/exports')
    def demo_exports(demo_id: str):
        if demo_id != SEOUL_ID or not seoul or not seoul.get('exports'):
            raise HTTPException(404)
        package = seoul['exports']
        return {k: v for k, v in package.items() if k not in {'video', 'audio', 'transcript', 'captions'}} | {
            kind: {'url': f'/api/demos/{SEOUL_ID}/assets/{package[kind]}',
                   'download_url': f'/api/demos/{SEOUL_ID}/assets/{package[kind]}?download=1'}
            for kind in ['video', 'audio', 'transcript', 'captions']}

    @app.get('/api/demos/{demo_id}/intro')
    def demo_intro(demo_id: str):
        if demo_id != DEMO_ID or not catalog:
            raise HTTPException(404)
        return [{k:v for k,v in item.items() if k != 'asset'} |
                {'url':f'/api/demos/{DEMO_ID}/assets/{item["asset"]}'} for item in catalog.get('intro', [])]

    @app.get('/api/demos/{demo_id}/guide')
    def demo_guide(demo_id: str):
        if demo_id != DEMO_ID or not catalog:
            raise HTTPException(404)
        return [{k:v for k,v in item.items() if k != 'asset'} |
                {'url':f'/api/demos/{DEMO_ID}/assets/{item["asset"]}'} for item in catalog.get('guide', [])]

    @app.get('/demos/{demo_id}')
    def demo_page(demo_id: str):
        if demo_id not in catalogs:
            raise HTTPException(404)
        return FileResponse(web/'demos'/('seoul.html' if demo_id == SEOUL_ID else 'house.html'), headers={
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' blob:; media-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"})

    @app.get('/demos/static/{name}')
    def demo_static(name: str):
        if name not in {'house.css', 'house.js', 'seoul.css', 'seoul.js', 'chat-panel.js', 'chat-panel.css', 'chat-bootstrap.js'}:
            raise HTTPException(404)
        return FileResponse(web/'demos'/name)

    @app.api_route('/api/demos/{demo_id}/assets/{name:path}', methods=['GET', 'HEAD'])
    def asset(demo_id: str, name: str, request: Request):
        selected_catalog = catalogs.get(demo_id)
        if not selected_catalog or name not in selected_catalog['assets']:
            raise HTTPException(404)
        item = selected_catalog['assets'][name]
        store = request.app.state.object_storage
        if store is None:
            raise HTTPException(503, 'Demo storage unavailable')
        try:
            info = store.client.stat_object(store.bucket, item['key'])
            metadata = {k.lower(): v for k, v in (info.metadata or {}).items()}
            if info.size != item['bytes'] or metadata.get('x-amz-meta-sha256') != item['sha256']:
                raise HTTPException(503, 'Demo object verification failed')
            start, length, status = 0, info.size, 200
            headers = {'Accept-Ranges': 'bytes', 'ETag': '"'+item['sha256']+'"',
                       'X-Content-Type-Options': 'nosniff', 'Cross-Origin-Resource-Policy': 'same-origin'}
            if demo_id == SEOUL_ID and request.query_params.get('download') == '1' and name in {
                    selected_catalog.get('exports', {}).get(kind) for kind in ['video', 'audio', 'transcript', 'captions']}:
                headers['Content-Disposition'] = f'attachment; filename="{name.rsplit("/", 1)[-1]}"'
            selected = request.headers.get('range')
            if selected:
                match = re.fullmatch(r'bytes=([0-9]{0,20})-([0-9]{0,20})', selected)
                if not match or not any(match.groups()):
                    return Response(status_code=416, headers={'Content-Range': f'bytes */{info.size}'})
                left, right = match.groups()
                start = int(left) if left else max(0, info.size-int(right))
                end = min(int(right), info.size-1) if left and right else info.size-1
                if start >= info.size or end < start or (not left and int(right)==0):
                    return Response(status_code=416, headers={'Content-Range': f'bytes */{info.size}'})
                length, status = end-start+1, 206
                headers['Content-Range'] = f'bytes {start}-{end}/{info.size}'
            headers['Content-Length'] = str(length)
            if request.method == 'HEAD':
                return Response(status_code=status, headers=headers, media_type=item['content_type'])
            source = store.client.get_object(store.bucket, item['key'], offset=start, length=length)
            return ObjectResponse(source, length=length, status_code=status,
                                  media_type=item['content_type'], headers=headers)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, 'Demo storage unavailable') from None
