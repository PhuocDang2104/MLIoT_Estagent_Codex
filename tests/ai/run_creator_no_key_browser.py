"""Honest no-key UI against the actual app, no injected provider."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png


def main():
    directory=Path(os.environ.get('CREATOR_QA_EVIDENCE_DIR', Path(__file__).resolve().parents[2]/'tests/ai/evidence/creator'))
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,**({'executable_path':os.environ['CREATOR_QA_BROWSER']} if os.environ.get('CREATOR_QA_BROWSER') else {}))
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:5188/business/create')
        page.get_by_text('Chưa kết nối OpenAI.',exact=False).wait_for()
        page.locator('#panoramas').set_input_files({'name':'No-key fixture.png','mimeType':'image/png','buffer':png(60)})
        page.locator('#selected-images .image-tile').wait_for()
        page.locator('[name=name]').fill('No-key synthetic draft')
        page.locator('[name=description]').fill('Synthetic input remains savable without an API key.')
        page.locator('#save-project').click()
        page.locator('#generate').wait_for(state='visible')
        assert page.locator('#generate').is_disabled()
        assert page.locator('#activity .activity-card').count()==0
        page.reload()
        page.locator('#generate').wait_for(state='visible')
        assert page.locator('#generate').is_disabled()
        assert page.locator('#assets .image-tile').count()==1
        page.screenshot(path=str(directory/'no-key-desktop.png'),full_page=True)
        browser.close()
    assert not errors,errors
    result={'status':'PASS','checks':['actual app without OpenAI key','save upload without provider','generate disabled','reload keeps draft','no invented progress'],'page_errors':errors}
    (directory/'no-key-browser.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('NO KEY BROWSER PASS')


if __name__=='__main__':
    main()
