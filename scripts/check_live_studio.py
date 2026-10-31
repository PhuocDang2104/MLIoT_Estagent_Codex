"""Explicitly staged local UI check. `create` makes ONE paid generation.

Subsequent review/publish actions are performed separately after inspecting its
source-grounded plan and script; this script never auto-approves a model.
"""
import argparse
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'projects/local-live/work'
BASE='http://127.0.0.1:5180'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['create','preview','published'])
    args=parser.parse_args()
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,**({'executable_path':os.environ['CREATOR_QA_BROWSER']} if os.environ.get('CREATOR_QA_BROWSER') else {}))
        context=browser.new_context(viewport={'width':1440,'height':1050},
            **({'storage_state':str(WORK/'browser-private.json')} if (WORK/'browser-private.json').exists() else {}))
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        if args.stage=='create':
            assert not (WORK/'run.json').exists(), 'A run already exists; do not spend twice'
            page.goto(BASE)
            ctas=page.locator('a[href="/business/create"]')
            assert ctas.count()>0
            ctas.first.click();page.locator('#create-form').wait_for()
            page.wait_for_function('document.querySelector("#panoramas").onchange !== null')
            source=json.loads((WORK/'input/source-manifest.json').read_text())
            data=json.loads((WORK/'input/project.json').read_text(encoding='utf-8'))
            page.locator('#panoramas').set_input_files([str(WORK/'input'/c['file']) for c in source['prepared_captures']])
            page.locator('#selected-images .image-tile').nth(2).wait_for()
            page.locator('[name=name]').fill(data['name']);page.locator('[name=description]').fill(data['description'])
            page.locator('#panorama-confirmed').check();page.locator('.extras > summary').click()
            page.locator('[name=locale]').select_option('en')
            page.locator('#floorplan').set_input_files(str(WORK/'input/source-floorplan.png'))
            # Exercise late music recovery, not only music at creation time.
            page.locator('#placeholder-music').uncheck()
            page.locator('#save-project').click()
            try: page.locator('#generate').wait_for(state='visible')
            except Exception:
                page.screenshot(path=str(WORK/'create-error.png'),full_page=True)
                print(json.dumps({'notice':page.locator('#notice').inner_text(),'errors':errors,
                    'invalid':page.locator(':invalid').evaluate_all('(els)=>els.map(e=>({name:e.name,message:e.validationMessage}))')},ensure_ascii=True),flush=True)
                raise
            pid=page.url.split('/projects/')[1].split('/')[0]
            context.storage_state(path=str(WORK/'browser-private.json'))
            with page.expect_response(lambda r:r.request.method=='POST' and r.url.endswith('/generations')) as result:
                page.locator('#generate').click()
            response=result.value
            assert response.status==202,response.text()
            run={'project_id':pid,'generation_id':response.json()['id'],'url':page.url}
            (WORK/'run.json').write_text(json.dumps(run,indent=2))
            print(json.dumps(run))
        elif args.stage=='preview':
            run=json.loads((WORK/'run.json').read_text());page.goto(run['url'])
            page.get_by_role('tab',name='Nhà 3D',exact=True).click()
            page.locator('.house-stage[data-loaded=true]').wait_for(timeout=30000)
            page.screenshot(path=str(WORK/'creator-model.png'),full_page=True)
            print(json.dumps({'markers':page.locator('.house-marker').count(),'errors':errors}))
        else:
            run=json.loads((WORK/'run.json').read_text())
            page.goto(BASE+'/viewer.html');page.locator(f'a[href="/studio-tour.html?id={run["public_id"]}"]').wait_for()
            page.screenshot(path=str(WORK/'library.png'),full_page=True)
            page.add_init_script('''window.__audioEvents=[];window.__audios=[];const OriginalAudio=window.Audio;window.Audio=class extends OriginalAudio{constructor(...a){super(...a);window.__audios.push(this);for(const type of ['play','ended','pause'])this.addEventListener(type,()=>window.__audioEvents.push({type,duration:this.duration,volume:this.volume}));}};''')
            page.goto(BASE+f'/studio-tour.html?id={run["public_id"]}')
            page.locator('#show-model').click();page.locator('.house-stage[data-loaded=true]').wait_for(timeout=30000)
            assert 1<=page.locator('.house-marker').count()<=2
            page.screenshot(path=str(WORK/'dollhouse.png'),full_page=True)
            canvas=page.locator('.house-stage canvas').bounding_box()
            page.mouse.move(canvas['x']+canvas['width']*.5,canvas['y']+canvas['height']*.5);page.mouse.down()
            page.mouse.move(canvas['x']+canvas['width']*.65,canvas['y']+canvas['height']*.55,steps=20);page.mouse.up()
            page.mouse.wheel(0,-150);page.wait_for_timeout(500)
            page.screenshot(path=str(WORK/'dollhouse-orbit.png'),full_page=True)
            page.locator('.house-marker').first.click();page.locator('#room').wait_for(state='visible')
            page.locator('#room').select_option('cp02');page.locator('#room').select_option('cp03')
            page.locator('#play').click();page.wait_for_function('window.__audioEvents.filter(e=>e.type==="play").length>=2')
            page.wait_for_timeout(1500);page.locator('#pause').click()
            assert page.evaluate('window.__audios.every(a=>a.paused)')
            assert 'CC BY 4.0' in page.locator('#music-credit').inner_text()
            page.screenshot(path=str(WORK/'panorama.png'),full_page=True)
            page.set_viewport_size({'width':320,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            page.screenshot(path=str(WORK/'mobile.png'),full_page=True)
            evidence={'status':'PASS','kind':'real OpenAI/Blender/ZInD/recorded speech/licensed music',
                'checks':['entry','library','GLB','orbit/zoom','central markers','panorama checkpoint switch','music + narration play/pause','music credit','320px layout'],
                'audio':page.evaluate('window.__audioEvents'),'page_errors':errors}
            (WORK/'browser-result.json').write_text(json.dumps(evidence,indent=2))
            print(json.dumps(evidence))
        assert not errors,errors
        browser.close()


if __name__=='__main__': main()
