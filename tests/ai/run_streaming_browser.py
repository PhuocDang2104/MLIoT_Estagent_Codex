import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png


def main():
    out=Path(os.environ['STREAM_QA_DIR']);errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,executable_path=os.environ['CREATOR_QA_BROWSER'])
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:5192/business/create')
        page.wait_for_function('document.querySelector("#panoramas").onchange !== null')
        page.locator('#panoramas').set_input_files([
            {'name':f'Synthetic room {i}.png','mimeType':'image/png','buffer':png(i)} for i in range(2)])
        page.locator('#selected-images .image-tile').nth(1).wait_for()
        page.locator('[name=name]').fill('Synthetic streaming UI check')
        page.locator('[name=description]').fill('Synthetic images and public summaries only, not a property or live model output.')
        page.locator('#save-project').click();page.locator('#generate').wait_for(state='visible');page.locator('#generate').click()
        page.locator('.thinking-summary').filter(has_text='Check 0').wait_for()
        first=page.locator('.thinking-summary').inner_text()
        page.wait_for_function('(n)=>document.querySelector(".thinking-summary").textContent.length>n',arg=len(first))
        page.screenshot(path=str(out/'streaming-live-fixture.png'),full_page=True)
        page.get_by_role('button',name='Xác nhận & tiếp tục ↗',exact=True).wait_for()
        page.reload();page.locator('[data-node=spatial] summary').click()
        page.locator('.thinking-summary').filter(has_text='Check 34').wait_for()
        page.set_viewport_size({'width':320,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/'streaming-mobile-fixture.png'),full_page=True)
        assert not errors,errors
        (out/'streaming-browser.json').write_text(json.dumps({'status':'PASS','synthetic':True,
            'checks':['summary grows through real SSE','reload restores final summary','320px no overflow'], 'page_errors':errors},indent=2))
        print('STREAMING BROWSER PASS (synthetic provider, real HTTP/SSE)')
        browser.close()


if __name__=='__main__': main()
