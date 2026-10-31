"""Publish only the explicitly authorized local four-image demo; never use AI.

Image files and session cookies are not written into source or reports. Existing
published tours are never edited/deleted. A matching demo title prevents duplicates.
"""
import argparse
from http.cookiejar import CookieJar
import json
from pathlib import Path
from urllib.request import build_opener, HTTPCookieProcessor, Request

TITLE = 'DEMO — Không gian Hackathon · 4 điểm panorama'
SCENES = [
    ('0774', 'Sảnh thang máy', 'Ảnh sự kiện mẫu: khu sảnh thang máy. Tên điểm do biên tập; thứ tự tour không chứng minh đường nối giữa các khu.'),
    ('0773', 'Khu sân khấu', 'Ảnh sự kiện mẫu: khu sân khấu. Panorama tại một vị trí chụp; không phải mô hình 3D hoặc bất động sản đang cho thuê.'),
    ('0772', 'Khu làm việc', 'Ảnh sự kiện mẫu: khu có các bàn làm việc. Không có dữ liệu xác minh diện tích, sức chứa hoặc kích thước nội thất.'),
    ('0775', 'Góc bên cửa sổ', 'Ảnh sự kiện mẫu: góc nhìn bên cửa sổ. Góc phủ 240° là hiệu chỉnh tạm; vùng không chụp giữ trắng. Chưa có nhạc hoặc lời thu âm.'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--images', type=Path, required=True)
    parser.add_argument('--publish', action='store_true', required=True,
                        help='Explicit approval to make these four image derivatives public')
    args = parser.parse_args()
    base = args.base_url.rstrip('/')
    if base != 'https://estagent.duckdns.org':
        raise SystemExit('Only the explicitly scoped Estagent production hostname is supported')
    files = [args.images / f'IMG_{id}.jpg' for id, _, _ in SCENES]
    for path in files:
        if not path.is_file() or path.stat().st_size > 12 * 1024 * 1024:
            raise SystemExit(f'Demo file missing/too large: {path.name}')
    client = build_opener(HTTPCookieProcessor(CookieJar()))

    def api(path, method='GET', body=None, binary=False):
        headers = {'Origin': base}
        if body is not None:
            headers['Content-Type'] = 'application/octet-stream' if binary else 'application/json'
            if not binary:
                body = json.dumps(body, ensure_ascii=False).encode()
        request = Request(base + '/api/tours' + path, data=body, headers=headers, method=method)
        with client.open(request, timeout=90) as response:
            return json.load(response)

    existing = next((item for item in api('/published') if item['title'] == TITLE), None)
    if existing:
        print(json.dumps({'existing': True, 'url': base + '/viewer.html?tour=' + existing['id']}, ensure_ascii=False))
        return
    api('/session')
    assets = [api('/assets', 'POST', path.read_bytes(), True) for path in files]
    draft = api('/drafts', 'POST', {
        'asset_ids': [item['id'] for item in assets], 'title': TITLE, 'locale': 'vi',
        'text': 'Authorized demonstration event photos, not a rental listing. Editorial checkpoint tour; provisional coverage, no 3D or generated audio.',
        'request_id': 'authorized-demo-hackathon-panorama-v1',
    })
    scenes = []
    for scene, (_, name, description) in zip(draft['scenes'], SCENES):
        scenes.append({**{k: v for k, v in scene.items() if k not in {'image_url', 'thumbnail_url'}},
                       'name': name, 'description': description,
                       'projection': 'cylindrical', 'coverage_degrees': 240,
                       'coverage_source': 'user_provisional'})
    draft = api('/drafts/' + draft['id'], 'PUT', {
        'revision': draft['revision'], 'title': TITLE, 'locale': 'vi',
        'scenes': scenes, 'start_scene_id': scenes[1]['id'],
    })
    revision = {'revision': draft['revision']}
    api('/drafts/' + draft['id'] + '/review', 'POST', revision)
    published = api('/drafts/' + draft['id'] + '/publish', 'POST', revision)
    verified = api('/published/' + published['id'])
    assert len(verified['scenes']) == 4 and verified['status'] == 'published'
    print(json.dumps({'published': True, 'id': published['id'],
                      'url': base + '/viewer.html?tour=' + published['id'],
                      'scenes': [scene['name'] for scene in verified['scenes']],
                      'projection': 'cylindrical', 'coverage': '240 degrees provisional',
                      'audio': 'unavailable', 'ai_calls': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
