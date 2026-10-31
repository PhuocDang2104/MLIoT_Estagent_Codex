"""Play actual Linux candidate MP4s served from private synthetic scratch."""
import functools
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import json
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import uuid

root=Path(sys.argv[1]).resolve();repo=Path(__file__).resolve().parents[2]
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
session='native-video-'+uuid.uuid4().hex[:8]
def browser(*args):
 result=subprocess.run([shutil.which('playwright-cli'),'-s='+session,'--raw',*args],cwd=repo,capture_output=True,text=True,timeout=90)
 if result.returncode or '### Error' in result.stdout:raise RuntimeError(result.stdout+result.stderr)
 return result.stdout
try:
 browser('open','about:blank')
 code='''async page=>{const results=[];for(const aspect of ['portrait','landscape']){await page.goto('BASE/'+aspect+'.mp4');await page.locator('video').evaluate(v=>v.play());await page.waitForFunction(()=>document.querySelector('video').currentTime>.4);const value=await page.locator('video').evaluate(v=>{v.pause();v.controls=false;return {width:v.videoWidth,height:v.videoHeight,duration:v.duration,time:v.currentTime};});if(value.width!==(aspect==='portrait'?720:1280)||value.height!==(aspect==='portrait'?1280:720)||Math.abs(value.duration-6)>.1)throw new Error('Wrong media');await page.locator('video').screenshot({path:'tests/exports/evidence/native-linux-'+aspect+'-playback.png'});results.push({aspect,...value});}return {pass:true,source:'actual Linux candidate MP4',results};}'''.replace('BASE',f'http://127.0.0.1:{server.server_port}')
 result=browser('run-code',code);(repo/'tests/exports/evidence/native-linux-browser.log').write_text(result.rstrip()+'\n');print(result)
finally:
 browser('close');server.shutdown();server.server_close()
