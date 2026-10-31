"""Real browser → HTTP → graph → SQLite. Start creator_browser_server first.

Requires Playwright in the QA environment, not an application dependency.
Uses only synthetic fixtures, never loads .env or calls a paid provider.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=ROOT/'tests/ai/evidence/creator'


def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True, **(
            {'executable_path':os.environ['CREATOR_QA_BROWSER']} if os.environ.get('CREATOR_QA_BROWSER') else {}))
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:5186/business/create')
        page.locator('#save-project').wait_for(state='visible')
        page.screenshot(path=str(EVIDENCE/'create-desktop.png'),full_page=True)
        page.locator('#panoramas').set_input_files([
            {'name':'Living fixture.png','mimeType':'image/png','buffer':png(10)},
            {'name':'Bedroom fixture.png','mimeType':'image/png','buffer':png(20)}])
        page.locator('#selected-images .image-tile').nth(1).wait_for()
        page.locator('[name=name]').fill('Creator browser fixture')
        page.locator('[name=description]').fill('Dữ liệu tổng hợp dùng để kiểm thử Studio, không phải bất động sản thật.')
        page.locator('#panorama-confirmed').check()
        page.locator('#save-project').click()
        page.locator('#generate').wait_for(state='visible')
        assert '/business/projects/' in page.url
        page.locator('#generate').click()
        page.get_by_role('button',name='Xác nhận & tiếp tục ↗',exact=True).wait_for(timeout=15000)
        page.locator('#review [name=label]').first.fill('Phòng khách fixture')
        page.get_by_role('button',name='＋ Thêm đường nối hai chiều').click()
        page.locator('[name=forward]').fill('90')
        page.locator('[name=back]').fill('-90')
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(EVIDENCE/'spatial-review-desktop.png'),full_page=True)
        page.get_by_role('button',name='Xác nhận & tiếp tục ↗',exact=True).click()
        page.get_by_role('heading',name='Đã sẵn sàng cho bước dựng 3D').wait_for(timeout=15000)
        assert not page.locator('#publish').is_visible()
        assert page.locator('#top-status').inner_text()=='Chờ kết nối dựng 3D'
        url=page.url
        page.reload()
        page.get_by_role('heading',name='Đã sẵn sàng cho bước dựng 3D').wait_for()
        assert page.url==url
        page.get_by_role('tab',name='Nhà 3D',exact=True).click()
        assert 'worker' in page.locator('#preview').inner_text()
        page.screenshot(path=str(EVIDENCE/'waiting-integration-desktop.png'),full_page=True)
        for width in (390,320):
            page.set_viewport_size({'width':width,'height':844})
            page.evaluate('window.scrollTo(0,0)')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Overflow at {width}'
            page.screenshot(path=str(EVIDENCE/f'workspace-{width}.png'),full_page=True)
        isolated=browser.new_page()
        isolated.goto('http://127.0.0.1:5186/business/create')
        assert isolated.locator('#create-view').is_visible()
        assert not isolated.locator('#projects').inner_text()
        browser.close()
    assert not errors,errors
    result={'status':'PASS','fixture':'finite provider, no geometry worker, synthetic PNG',
            'checks':['upload','real HTTP/LangGraph/SQLite','spatial review','SSE','reload',
                      'publish blocked without worker','preview placeholder','390/320 no overflow','separate browser session'],
            'page_errors':errors,'live_openai':False}
    (EVIDENCE/'browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':
    main()
