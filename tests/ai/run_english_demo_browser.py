"""Real HTTP draft uploads, supplied stock bytes, no paid provider calls.

Run against tests.ai.upload_browser_server on 5195. Sample asset routes alone
use SEOUL_SAMPLE_DIR, the user's existing unpacked catalog; all Studio routes
use the real server and SQLite. Production verification uses the real catalog.
"""
import hashlib
import json
import os
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png


def main():
    root = Path(os.environ['SEOUL_SAMPLE_DIR'])
    out = Path(os.environ['UPLOAD_QA_DIR'])
    manifest = json.loads((root/'house/manifest.json').read_text())
    captures = manifest['captures']
    assert len(captures) == 8
    for capture in captures:
        assert hashlib.sha256((root/capture['image']).read_bytes()).hexdigest() == capture['sha256']
    errors, writes = [], []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=os.environ['CREATOR_QA_BROWSER'])
        context = browser.new_context(viewport={'width': 1365, 'height': 1000})
        context.add_init_script("localStorage.setItem('estagent-language','vi')")
        def sample(route):
            name = route.request.url.split('/assets/')[1]
            allowed = {'house/manifest.json', *(c['image'] for c in captures)}
            assert name in allowed
            route.fulfill(path=str(root/name), content_type='application/json' if name.endswith('.json') else 'image/jpeg')
        context.route('**/api/demos/seoul-apartment/assets/**', sample)
        page = context.new_page()
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('request', lambda r: writes.append(r.url) if r.method == 'POST' else None)
        base = os.environ.get('UPLOAD_QA_ORIGIN', 'http://127.0.0.1:5195')
        page.goto(base+'/business/create')
        page.locator('#selected-images .image-tile').nth(7).wait_for()
        assert page.locator('#selected-images .image-tile').count() == 8
        assert page.locator('[name=locale]').input_value() == 'en'
        assert page.locator('#panorama-confirmed').is_checked()
        assert not writes, writes
        assert page.locator('#selected-images img').evaluate_all('(images)=>images.every(i=>i.naturalWidth===2048&&i.naturalHeight===1024)')
        page.screenshot(path=str(out/'english-seoul-defaults.png'), full_page=True)
        page.locator('#selected-images .remove').first.click()
        assert page.locator('#selected-images .image-tile').count() == 7
        page.locator('#clear-images').click()
        assert page.locator('#selected-images .image-tile').count() == 0
        page.locator('#load-sample').click()
        page.locator('#selected-images .image-tile').nth(7).wait_for()
        page.locator('#panoramas').set_input_files({'name':'Own.png','mimeType':'image/png','buffer':png(31)})
        page.locator('#selected-images p').filter(has_text='Own.png').wait_for()
        assert page.locator('#selected-images .image-tile').count() == 1
        assert not page.locator('#panorama-confirmed').is_checked()
        assert page.locator('[name=name]').input_value() == ''
        page.locator('#load-sample').click()
        page.locator('#selected-images .image-tile').nth(7).wait_for()
        page.locator('#save-project').click()
        page.locator('#workspace-view').wait_for(state='visible', timeout=20000)
        project_url = page.url
        project_id = project_url.split('/projects/')[1].split('/')[0]
        data = page.request.get(base+'/api/studio/projects/'+project_id).json()
        panos = [a for a in data['assets'] if a['kind'] == 'panorama']
        assert sorted(a['name'] for a in panos) == sorted(Path(c['image']).name for c in captures)
        assert len(data['assets']) == 9  # eight images and credited placeholder music
        assert data['locale'] == 'en' and data['panorama_confirmed']
        assert not data['generations']
        before = len(writes)
        page.reload()
        page.locator('#workspace-view').wait_for(state='visible')
        assert page.locator('#selected-images .image-tile').count() == 0
        assert len(writes) == before
        # Existing drafts remain intact; every public product shell is English,
        # including a session whose old localStorage preference was Vietnamese.
        for path in ['/', '/viewer.html', '/business/photos', '/assistant.html', '/export.html', '/studio-tour.html']:
            page.goto(base+path)
            page.wait_for_function("document.readyState === 'complete' && document.documentElement.lang === 'en'")
            assert page.locator('html').get_attribute('lang') == 'en', path
            assert not re.search(r'[ăâđêôơưĂÂĐÊÔƠƯ\u1ea0-\u1ef9]', page.locator('body').inner_text()), path
            assert page.locator('[data-lang]:visible').count() == 0
        # A failed sample fetch leaves custom uploads usable.
        page.route('**/api/demos/seoul-apartment/assets/house/manifest.json', lambda r:r.fulfill(status=503, body='unavailable'))
        page.goto(base+'/business/create')
        page.locator('#sample-status').filter(has_text='could not load').wait_for()
        assert not page.locator('#save-project').is_disabled()
        page.locator('#panoramas').set_input_files({'name':'Fallback.png','mimeType':'image/png','buffer':png(39)})
        page.locator('#selected-images p').filter(has_text='Fallback.png').wait_for()
        assert page.locator('#selected-images .image-tile').count() == 1
        # Hold a response until a user upload cancels the automatic sample.
        page.unroute('**/api/demos/seoul-apartment/assets/house/manifest.json')
        held = []
        page.route('**/api/demos/seoul-apartment/assets/house/manifest.json', lambda r:held.append(r))
        page.goto(base+'/business/create', wait_until='domcontentloaded')
        page.locator('#sample-status').filter(has_text='Loading').wait_for()
        assert held
        page.locator('#panoramas').set_input_files({'name':'During-load.png','mimeType':'image/png','buffer':png(43)})
        held[0].fulfill(path=str(root/'house/manifest.json'), content_type='application/json')
        page.locator('#selected-images p').filter(has_text='During-load.png').wait_for()
        page.wait_for_load_state('networkidle')
        assert page.locator('#selected-images .image-tile').count() == 1
        assert not page.locator('#save-project').is_disabled()
        assert not errors, errors
        report = {'status':'PASS', 'provider_calls':0, 'sample_images':8, 'saved_assets':9,
                  'checks':['stock source SHA-256 matches', 'no automatic writes', 'English locale and old preference',
                            'remove and clear', 'custom images replace stock', 'sample load cancellation',
                            'sample failure fallback', 'real draft upload', 'existing draft preserved',
                            'English product shells'], 'page_errors':errors}
        (out/'english-demo-browser.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
        browser.close()


if __name__ == '__main__':
    main()
