"""Real HTTP uploads/SQLite limits; one injected failure tests manual resumption."""
import json
import os
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png


def main():
    out = Path(os.environ['UPLOAD_QA_DIR'])
    requests = Counter()
    errors = []
    injected = False
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, **({'executable_path': os.environ['CREATOR_QA_BROWSER']} if os.environ.get('CREATOR_QA_BROWSER') else {}))
        page = browser.new_page(viewport={'width': 1200, 'height': 900})
        page.on('pageerror', lambda e: errors.append(str(e)))

        def intercept(route):
            nonlocal injected
            query = parse_qs(urlparse(route.request.url).query)
            name = query['name'][0]
            requests[name] += 1
            if query['kind'] == ['floorplan'] and not injected:
                injected = True
                route.fulfill(status=503, json={'error': 'Synthetic transient failure'})
            else:
                route.continue_()

        page.route('**/api/studio/projects/*/assets?*', intercept)
        page.goto('http://127.0.0.1:5195/business/create')
        page.locator('#panoramas').set_input_files([
            {'name': f'Capture-{i:02}.png', 'mimeType': 'image/png', 'buffer': png(i+10)} for i in range(12)])
        page.locator('#selected-images .image-tile').nth(11).wait_for()
        page.locator('[name=name]').fill('Upload retry synthetic fixture')
        page.locator('[name=description]').fill('Synthetic upload-only test. No provider generation requested.')
        page.locator('.extras > summary').click()
        page.locator('#floorplan').set_input_files({'name': 'Plan.png', 'mimeType': 'image/png', 'buffer': png(100)})
        page.locator('#save-project').click()
        page.locator('#notice').filter(has_text='resuming in').wait_for()
        assert page.locator('#save-project').is_disabled()
        page.screenshot(path=str(out/'upload-countdown.png'))
        page.locator('#notice').filter(has_text='Synthetic transient failure').wait_for()
        page.locator('#save-project').click()
        page.locator('#workspace-view').wait_for(state='visible', timeout=15000)
        project_id = page.url.split('/projects/')[1].split('/')[0]
        data = page.request.get('http://127.0.0.1:5195/api/studio/projects/'+project_id).json()
        assert Counter(a['kind'] for a in data['assets']) == {'panorama': 12, 'floorplan': 1, 'music': 1}
        assert data['generations'] == []
        assert all(requests[f'Capture-{i:02}.png'] == 1 for i in range(6)), requests
        assert all(requests[f'Capture-{i:02}.png'] == 1 for i in range(7,12)), requests
        assert requests['Capture-06.png'] == 2, requests
        assert not errors, errors
        report = {'status': 'PASS', 'saved_assets': 14, 'panoramas': 12, 'provider_calls': 0,
                  'checks': ['real upload 429 and Retry-After', 'visible countdown', 'automatic continuation',
                             'manual retry skips completed files', 'floorplan and placeholder music retained'],
                  'requests_by_synthetic_file': dict(requests), 'page_errors': errors}
        (out/'upload-browser.json').write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        browser.close()


if __name__ == '__main__':
    main()
