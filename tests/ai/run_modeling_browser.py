"""Full UI workflow with a synthetic planner and the real automatic Blender CLI."""
import json
import math
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from tests.ai.creator_fixtures import png, wav

EVIDENCE=Path(os.environ.get('CREATOR_QA_EVIDENCE_DIR', Path(__file__).resolve().parents[2]/'tests/ai/evidence/house-modeling'))


def main():
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,**({'executable_path':os.environ['CREATOR_QA_BROWSER']} if os.environ.get('CREATOR_QA_BROWSER') else {}))
        page=browser.new_page(viewport={'width':1440,'height':1050})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('http://127.0.0.1:5191/business/create')
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
        page.get_by_role('button',name='Xác nhận & tiếp tục ↗',exact=True).wait_for(timeout=120000)
        assert page.get_by_role('button',name='Xác nhận & tiếp tục ↗',exact=True).is_disabled()
        page.get_by_role('textbox',name='Làm rõ bố cục').fill('Kitchen and living share this doorway. Approximate layout is acceptable.')
        page.get_by_role('button',name='Cập nhật bố cục (1/3)',exact=True).click()
        page.get_by_role('button',name='Cập nhật bố cục (2/3)',exact=True).wait_for(timeout=15000)
        page.locator('[name=accept_approximate]').check()
        page.get_by_role('tab',name='Mặt bằng',exact=True).click()
        assert page.locator('#preview svg polygon').count()==2
        page.get_by_role('button',name='＋ Nối hai khu').click()
        page.locator('[name=forward]').fill('90')
        page.locator('[name=back]').fill('-90')
        page.get_by_role('button',name='Xác nhận & tiếp tục ↗',exact=True).click()
        page.get_by_role('button',name='Duyệt & tạo giọng ↗',exact=True).wait_for(timeout=120000)
        page.get_by_role('tab',name='Nhà 3D',exact=True).click()
        page.locator('.house-stage[data-loaded=true]').wait_for(timeout=30000)
        assert page.locator('.house-marker').count()==2
        page.screenshot(path=str(EVIDENCE/'creator-model.png'),full_page=True)
        page.locator('.house-marker[data-checkpoint=cp02]').click()
        assert page.get_by_role('tab',name='Panorama',exact=True).get_attribute('aria-selected')=='true'
        page.locator('#script-editor textarea').first.fill('Lời giới thiệu fixture do Business kiểm tra.')
        page.get_by_role('button',name='Duyệt & tạo giọng ↗',exact=True).click()
        page.locator('#publish').wait_for(state='visible',timeout=120000)
        page.get_by_role('tab',name='Tour',exact=True).click()
        assert page.locator('#preview audio').count()==3
        page.locator('#publish').click()
        link=page.get_by_role('link',name='Mở tour ↗')
        link.wait_for()
        share=link.get_attribute('href')
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(EVIDENCE/'completed-fixture-desktop.png'),full_page=True)
        viewer=browser.new_page(viewport={'width':1440,'height':1000})
        viewer.add_init_script('''window.__audioEvents=[];window.__audios=[];const OriginalAudio=window.Audio;window.Audio=class extends OriginalAudio{constructor(...a){super(...a);window.__audios.push(this);for(const type of ['play','ended','pause'])this.addEventListener(type,()=>window.__audioEvents.push({type,src:this.src,duration:this.duration,volume:this.volume}));}};''')
        viewer.on('pageerror',lambda e:errors.append(str(e)))
        viewer.goto('http://127.0.0.1:5191'+share)
        viewer.get_by_role('heading',name='Published synthetic tour').wait_for()
        viewer.locator('#show-model').click()
        viewer.locator('.house-stage[data-loaded=true]').wait_for(timeout=30000)
        canvas=viewer.locator('.house-stage canvas')
        bounds=canvas.bounding_box()
        viewer.mouse.move(bounds['x']+bounds['width']*.45,bounds['y']+bounds['height']*.5)
        viewer.mouse.down();viewer.mouse.move(bounds['x']+bounds['width']*.58,bounds['y']+bounds['height']*.55,steps=12);viewer.mouse.up()
        viewer.mouse.wheel(0,-80)
        viewer.get_by_role('button',name='Ẩn tường',exact=True).click()
        viewer.screenshot(path=str(EVIDENCE/'published-dollhouse.png'),full_page=True)
        viewer.locator('.house-marker[data-checkpoint=cp02]').click()
        assert viewer.locator('#room').input_value()=='cp02'
        viewer.locator('#room').select_option('cp01')
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
        viewer.locator('#show-model').click()
        viewer.locator('.house-stage[data-loaded=true]').wait_for(timeout=30000)
        assert viewer.evaluate('document.documentElement.scrollWidth<=innerWidth')
        viewer.screenshot(path=str(EVIDENCE/'published-viewer-320.png'),full_page=True)
        browser.close()
    assert not errors,errors
    result={'status':'PASS','fixture':'synthetic provider, actual Blender GLB, silence WAV; not live OpenAI',
        'checks':['floorplan/music upload','clarification revision','approximate scale acceptance','real Blender build',
                  'Three.js textured GLB','orbit/zoom/wall visibility','model marker enters panorama','final script edit','approve before TTS','publish snapshot',
                  'share page','360 preview','browser media play/ended','music ducking','rapid checkpoint switch/pause','read-only Viewer Q&A','320 no overflow'],
        'media_events':events,'page_errors':errors}
    # Strip runtime IDs from evidence; all input/media are synthetic.
    for event in result['media_events']:
        event['src']='synthetic-published-wav'
        if not math.isfinite(event['duration']):
            event['duration']=None  # Browser metadata was not available for this event.
    (EVIDENCE/'full-browser.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    print('FULL BROWSER PASS; synthetic planner/audio, actual Blender and Three.js')


if __name__=='__main__':
    main()
