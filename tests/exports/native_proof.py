"""Synthetic native render proof; outputs/logs only in caller's scratch directory."""
import array
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
import wave
from PIL import Image,ImageDraw
from server.exports.plan import plan
from server.exports.render import render
from tests.exports.check_audio import measure

root=Path(sys.argv[1]).resolve();root.mkdir(parents=True,exist_ok=True)
scenes=[];narration=[]
for i,color in enumerate(['#526e75','#956d47']):
 id=f'{i+1:032x}'
 scenes.append({'id':id,'asset_id':id,'name':f'Phòng {i+1} · Synthetic','description':'Synthetic photos only. No property or geometry evidence.','file':f'{id}.jpg'})
 narration.append({'scene_id':id,'locale':'en','transcript':f'Checkpoint {i+1}: synthetic tone, not speech.','track':{'duration_seconds':1}})
 image=Image.new('RGB',(1280,720),color);draw=ImageDraw.Draw(image)
 for x in range(80,1280,150):draw.rectangle((x,60,x+70,590),outline='white',width=8)
 image.save(root/f'{id}.jpg')
for name,frequency,seconds in [('music-loop.wav',220,6),('voice-0.wav',440,1),('voice-1.wav',660,1)]:
 samples=array.array('h',(int(3000*math.sin(i*frequency*2*math.pi/16000)) for i in range(seconds*16000)))
 if sys.byteorder!='little':samples.byteswap()
 with wave.open(str(root/name),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(samples.tobytes())
snapshot={'id':'f'*32,'title':'Synthetic home tour','locale':'en','start_scene_id':scenes[0]['id'],'scenes':scenes,'audio':{'narration':narration,'music':{'duration_seconds':6}}}
results=[]
for aspect in ['portrait','landscape']:
 edit=plan(snapshot,aspect);edit['music_file']='music-loop.wav'
 for i,s in enumerate(edit['scenes']):s['voice_file']=f'voice-{i}.wav'
 start=time.monotonic();info=render(edit,root,root/f'{aspect}.mp4',None,Path('web').resolve(),renderer='ffmpeg')
 results.append({'aspect':aspect,'elapsed_seconds':round(time.monotonic()-start,3),'streams':[{k:s.get(k) for k in ['codec_type','codec_name','width','height','duration']} for s in info['streams']],'audio':measure(root/f'{aspect}.mp4')})
mem={}
for name in ['memory.peak','memory.max','cpu.max','pids.max','memory.events']:
 p=Path('/sys/fs/cgroup')/name
 if p.exists():mem[name]=p.read_text().strip()
report={'pass':True,'actual_native_render':True,'synthetic':True,'platform':sys.platform,'results':results,'cgroup':mem,'child_maxrss':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,'self_maxrss':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'rss_units':'KiB on Linux, bytes on macOS'}
(root/'native-proof.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
