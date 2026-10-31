"""Full UI workflow using the explicitly configured synthetic geometry worker."""
import json
import os
from urllib.parse import urlsplit, parse_qs
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png, wav

EVIDENCE=Path(os.environ.get('CREATOR_QA_EVIDENCE_DIR', Path(__file__).resolve().parents[2]/'tests/ai/evidence/creator'))


def main():
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,**({'executable_path':os.environ['CREATOR_QA_BROWSER']} if os.environ.get('CREATOR_QA_BROWSER') else {}))
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:5187/business/create')
        page.locator('#panoramas').set_input_files([
            {'name':'Living fixture.png','mimeType':'image/png','buffer':png(30)},
            {'name':'Bedroom fixture.png','mimeType':'image/png','buffer':png(40)}])
        page.locator('#selected-images .image-tile').nth(1).wait_for()
        page.locator('[name=name]').fill('Published synthetic tour')
        page.locator('[name=description]').fill('Synthetic end-to-end workflow test. Not an actual property.')
        page.locator('#panorama-confirmed').check()
        page.locator('.extras > summary').click()
        page.locator('#floorplan').set_input_files({'name':'Floorplan fixture.png','mimeType':'image/png','buffer':png(50)})
        page.locator('#music').set_input_files({'name':'Synthetic silence.wav','mimeType':'audio/wav','buffer':wav()})
        page.locator('[name=music_credit]').fill('Generated test silence, no external asset.')
        page.locator('#save-project').click()
        page.locator('#generate').wait_for(state='visible')
        page.locator('#generate').click()
        page.get_by_role('button',name='Confirm & continue ↗',exact=True).wait_for(timeout=15000)
        page.get_by_role('button',name='＋ Connect two spaces').click()
        page.locator('[name=forward]').fill('90')
        page.locator('[name=back]').fill('-90')
        page.get_by_role('button',name='Confirm & continue ↗',exact=True).click()
        page.get_by_role('button',name='Approve & generate voice ↗',exact=True).wait_for(timeout=15000)
        page.locator('#script-editor textarea').first.fill('Lời giới thiệu fixture do Business kiểm tra.')
        page.get_by_role('button',name='Approve & generate voice ↗',exact=True).click()
        page.locator('#publish').wait_for(state='visible',timeout=15000)
        page.get_by_role('tab',name='Tour',exact=True).click()
        assert page.locator('#preview audio').count()==3
        page.locator('#publish').click()
        link=page.get_by_role('link',name='Open tour ↗')
        link.wait_for()
        share=link.get_attribute('href')
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(EVIDENCE/'completed-fixture-desktop.png'),full_page=True)
        viewer=browser.new_page(viewport={'width':1440,'height':1000})
        viewer.add_init_script('''window.__audioEvents=[];window.__audios=[];const OriginalAudio=window.Audio;window.Audio=class extends OriginalAudio{constructor(...a){super(...a);window.__audios.push(this);for(const type of ['play','ended','pause'])this.addEventListener(type,()=>window.__audioEvents.push({type,src:this.src,duration:this.duration,volume:this.volume}));}};''')
        viewer.on('pageerror',lambda e:errors.append(str(e)))
        viewer.goto('http://127.0.0.1:5187'+share)
        viewer.get_by_role('heading',name='Published synthetic tour').wait_for()
        assert viewer.locator('#publish').count()==0
        viewer.locator('#play').click()
        viewer.wait_for_function('window.__audioEvents.some(e=>e.type==="ended")')
        events=viewer.evaluate('window.__audioEvents')
        assert any(e['type']=='play' and e['volume']<.1 for e in events)
        assert any(e['type']=='ended' and e['duration']>0 for e in events)
        viewer.locator('#pause').click()
        viewer.evaluate('''() => {document.querySelector('#play').click();const select=document.querySelector('#room');select.value='cp02';select.dispatchEvent(new Event('change'));select.value='cp01';select.dispatchEvent(new Event('change'));document.querySelector('#pause').click();}''')
        viewer.wait_for_timeout(200)
        assert viewer.evaluate('window.__audios.every(a=>a.paused)')
        viewer.locator('#question').fill('Không gian này có đặc điểm gì?')
        viewer.locator('#ask').click()
        viewer.locator('#chat').get_by_text('Thông tin chỉ đọc từ tour fixture đã duyệt.',exact=True).wait_for()
        viewer.screenshot(path=str(EVIDENCE/'published-viewer-desktop.png'),full_page=True)
        viewer.set_viewport_size({'width':320,'height':844})
        assert viewer.evaluate('document.documentElement.scrollWidth<=innerWidth')
        viewer.screenshot(path=str(EVIDENCE/'published-viewer-320.png'),full_page=True)
        public_id = parse_qs(urlsplit(share).query)['id'][0]
        original = viewer.request.get('http://127.0.0.1:5187/api/studio-tours/'+public_id).json()
        page.locator('#edit-text').fill('Sửa lời giới thiệu khu đầu ngắn gọn hơn.')
        page.locator('#propose-edit').click()
        page.locator('#apply-edit').wait_for(timeout=15000)
        page.screenshot(path=str(EVIDENCE/'edit-proposal-desktop.png'),full_page=True)
        page.reload()
        page.locator('#apply-edit').wait_for(timeout=15000)
        page.locator('#apply-edit').click()
        page.get_by_role('button',name='Approve & generate voice ↗',exact=True).wait_for(timeout=15000)
        assert page.locator('#script-editor textarea').first.input_value() == 'Lời mới đã được Business yêu cầu.'
        assert page.locator('#publish').is_hidden()
        assert page.locator('#history-count').inner_text() == '2'
        page.set_viewport_size({'width':320,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(EVIDENCE/'edit-fork-review-320.png'),full_page=True)
        page.get_by_role('button',name='Approve & generate voice ↗',exact=True).click()
        page.locator('#publish').wait_for(state='visible',timeout=15000)
        assert viewer.request.get('http://127.0.0.1:5187/api/studio-tours/'+public_id).json() == original
        browser.close()
    assert not errors,errors
    result={'status':'PASS','fixture':'synthetic provider, triangle GLB, silence WAV; not live OpenAI/Blender',
        'checks':['floorplan/music upload','final script edit','approve before TTS','publish snapshot',
                  'share page','360 preview','browser media play/ended','music ducking','rapid checkpoint switch/pause','read-only Viewer Q&A','320 no overflow',
                  'OpenAI fixture edit proposal','pending proposal survives reload','explicit confirmation forks graph',
                  'new script final review before TTS/publish','published parent unchanged'],
        'media_events':events,'page_errors':errors}
    # Strip runtime IDs from evidence; all input/media are synthetic.
    for event in result['media_events']:
        event['src']='synthetic-published-wav'
    (EVIDENCE/'full-browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('FULL BROWSER PASS; fixture provider/worker/audio only')


if __name__=='__main__':
    main()
