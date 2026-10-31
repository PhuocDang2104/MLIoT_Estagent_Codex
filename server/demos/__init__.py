"""Read-only catalog for the explicitly supplied cached home; no ZIP/file gateway."""
import json
from pathlib import Path
import re
from fastapi import HTTPException, Request, Response
from fastapi.responses import FileResponse
from server.object_storage import ObjectResponse

DEMO_ID = 'zind-house-000'
BUNDLE_SHA = '734f7053604b67c24701acff3a044e2d33241272149e9596b0eefdca5fc592e3'
TYPES = {'image/jpeg', 'image/png', 'image/svg+xml', 'model/gltf-binary',
         'application/javascript', 'text/css', 'application/json', 'audio/wav'}


def read_catalog(path):
    try:
        doc = json.loads(Path(path).read_text())
        if doc['id'] != DEMO_ID or doc['source_bundle_sha256'] != BUNDLE_SHA:
            raise ValueError()
        for name, asset in doc['assets'].items():
            if (not re.fullmatch(r'(?:runtime|house)/[A-Za-z0-9_./-]+', name)
                    or any(p in {'', '.', '..'} for p in name.split('/'))
                    or not name.endswith(('.js', '.css', '.json', '.jpg', '.png', '.svg', '.glb', '.wav'))
                    or not re.fullmatch('[a-f0-9]{64}', asset['sha256'])
                    or asset['key'] != f'demos/{DEMO_ID}/{asset["sha256"]}/{name}'
                    or asset['content_type'] not in TYPES or not isinstance(asset['bytes'], int)
                    or asset['bytes'] <= 0):
                raise ValueError()
        if not {'house/manifest.json', 'house/dollhouse-studio.glb'} <= doc['assets'].keys():
            raise ValueError()
        if doc['thumbnail'] not in doc['assets']:
            raise ValueError()
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
    if catalog and app.state.object_storage is None:
        raise ValueError('Cached demo requires configured private MinIO storage')

    @app.get('/api/demos')
    def catalog_list():
        if not catalog:
            return []
        return [{'id': DEMO_ID, 'kind': 'cached_demo', 'title': 'NHÀ DEMO — Nhà mẫu 000',
                 'href': f'/demos/{DEMO_ID}', 'thumbnail_url': f'/api/demos/{DEMO_ID}/assets/{catalog["thumbnail"]}',
                 'rooms': 15, 'captures': 32, 'markers': 16, 'source_mode': 'user_provided_cached',
                 'rights_status': 'not_independently_verified', 'audio_available': bool(catalog.get('intro'))}]

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
        if demo_id != DEMO_ID or not catalog:
            raise HTTPException(404)
        return FileResponse(web/'demos'/'house.html', headers={
            'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' blob:; media-src 'self' blob:; object-src 'none'; base-uri 'self'; frame-ancestors 'self'"})

    @app.get('/demos/static/{name}')
    def demo_static(name: str):
        if name not in {'house.css', 'house.js'}:
            raise HTTPException(404)
        return FileResponse(web/'demos'/name)

    @app.api_route('/api/demos/{demo_id}/assets/{name:path}', methods=['GET', 'HEAD'])
    def asset(demo_id: str, name: str, request: Request):
        if demo_id != DEMO_ID or not catalog or name not in catalog['assets']:
            raise HTTPException(404)
        item = catalog['assets'][name]
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
