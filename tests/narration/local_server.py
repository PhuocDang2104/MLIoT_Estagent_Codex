"""QA ONLY: mounted production router callbacks and real MinIO adapter / synthetic SDK."""
import argparse
from pathlib import Path
import uvicorn
from fastapi.responses import HTMLResponse,FileResponse,Response
from tests.narration.fixtures import build
from tests.ai.creator_fixtures import png

PAGE='''<!doctype html><meta charset="utf-8"><title>Narration fixture QA</title><link rel="stylesheet" href="/qa/narration-panel.css"><h1>SDK fixture tone — not speech</h1><main id="panel"></main><script type="module">
import {mountNarrationPanel} from '/qa/narration-panel.js';
async function api(path,opts={}){const r=await fetch('/api/tours'+path,{method:opts.method||'GET',headers:opts.body?{'Content-Type':'application/json'}:{},body:opts.body?JSON.stringify(opts.body):undefined});const body=await r.json();if(!r.ok)throw Error(JSON.stringify(body));return body;}
await api('/session');const assets=[];for(let i=0;i<2;i++){const image=await fetch('/qa/image/'+i);const r=await fetch('/api/tours/assets',{method:'POST',body:await image.blob()});assets.push((await r.json()).id);}
window.doc=await api('/drafts',{method:'POST',body:{asset_ids:assets,locale:'en',request_id:crypto.randomUUID()}});
window.api=api;window.panel=mountNarrationPanel(document.querySelector('#panel'),{getManifest:()=>api('/drafts/'+window.doc.id),onManifest:doc=>{window.doc=doc;},api,intervalMs:100});
</script>'''
class Ready(uvicorn.Server):
    async def startup(self,sockets=None):
        await super().startup(sockets)
        if self.started:print('NARRATION_READY',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--keyless',action='store_true');p.add_argument('--live-dir');a=p.parse_args()
    root=Path(a.root);app,service,_,_=build(root,{'ASSISTANT_ORIGIN':f'http://127.0.0.1:{a.port}','FIXTURE_PROVIDER':'0' if a.keyless else '1'})
    @app.get('/qa/narration')
    def page():return HTMLResponse(PAGE)
    @app.get('/qa/narration-panel.js')
    def script():return FileResponse('web/narration-panel.js',media_type='text/javascript')
    @app.get('/qa/narration-panel.css')
    def style():return FileResponse('web/narration-panel.css',media_type='text/css')
    @app.get('/qa/image/{index}')
    def image(index:int):return Response(png(index),media_type='image/png')
    if a.live_dir:
        @app.get('/qa/live/{locale}')
        def live(locale:str):
            from fastapi import HTTPException
            if locale not in {'en','vi'}:raise HTTPException(404)
            return FileResponse(Path(a.live_dir)/f'{locale}.wav',media_type='audio/wav')
    try:Ready(uvicorn.Config(app,host='127.0.0.1',port=a.port,log_level='warning')).run()
    finally:service.close()
