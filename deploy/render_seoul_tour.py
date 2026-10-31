"""Render the authorized English sample from source panoramas and cached voice.

Produces a conventional 1080p H.264/AAC video, PCM voice, TXT and timed WebVTT.
The source panoramas are 2048x1024; output resolution is not additional detail.
No network or provider calls. Originals and the existing catalog are unchanged.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave


def stamp(seconds):
    milliseconds = round(seconds*1000)
    hours, remainder = divmod(milliseconds, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    secs, millis = divmod(remainder, 1000)
    return f'{hours:02}:{minutes:02}:{secs:02}.{millis:03}'


def render(catalog_dir, voice_dir, output, font):
    catalog_dir, voice_dir, output, font = map(lambda p: Path(p).resolve(), [catalog_dir, voice_dir, output, font])
    output.mkdir(parents=True, exist_ok=True)
    work=output/'work';work.mkdir(exist_ok=True)
    export=output/'house'/'exports';export.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(font,work/'font.ttf')
    narration=json.loads((voice_dir/'chapters.json').read_text(encoding='utf-8'))
    authored=json.loads(Path(__file__).with_name('seoul_narration_en.json').read_text(encoding='utf-8'))
    paths={c['capture_id']:c for c in authored['chapters']}
    catalog=json.loads((catalog_dir/'catalog.json').read_text())
    assert catalog['id']=='seoul-apartment' and narration['locale']=='en'
    timeline=[];pcm=[];clips=[];offset=0;rate=24000;fps=25
    def run(args, log):
        with (work/log).open('w') as stream:
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','warning','-y',*args],cwd=work,
                           stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=600)
    for i,chapter in enumerate(narration['chapters']):
        camera=paths[chapter['capture_id']]
        assert chapter['text']==camera['text']
        chapter={**chapter,**camera}
        image=catalog_dir/'house'/'panos'/(chapter['capture_id']+'.jpg')
        key='house/panos/'+image.name
        assert hashlib.sha256(image.read_bytes()).hexdigest()==catalog['assets'][key]['sha256']
        with wave.open(str(voice_dir/chapter['audio']),'rb') as audio:
            assert (audio.getframerate(),audio.getnchannels(),audio.getsampwidth())==(rate,1,2)
            frames=audio.readframes(audio.getnframes())
        length=math.ceil((len(frames)/(rate*2)+1)*fps)/fps
        lead=round(rate*.35);tail=round(length*rate)-lead-len(frames)//2
        pcm.append(bytes(lead*2)+frames+bytes(tail*2))
        timeline.append({k:chapter[k] for k in ['capture_id','title','text']} | {'start':round(offset,3),'duration':length})
        yawfile=work/f'yaw-{i}.txt'
        yawfile.write_text('\n'.join(f'{f/fps:.3f} v360@view yaw {chapter["yaw_start"]+(chapter["yaw_end"]-chapter["yaw_start"])*f/max(1,round(length*fps)-1):.4f};' for f in range(round(length*fps))))
        (work/f'title-{i}.txt').write_text(f'{i+1:02} / 08   {chapter["title"]}',encoding='utf-8')
        # Runtime yaw commands otherwise accumulate rotation. Reset makes each
        # sampled angle absolute and preserves the authored pitch.
        filters=(f'sendcmd=f=yaw-{i}.txt,v360@view=input=equirect:output=flat:w=1920:h=1080:h_fov=100:v_fov=68:reset_rot=1:pitch={chapter.get("pitch",-8)}:yaw={chapter["yaw_start"]},'
            'drawbox=x=0:y=0:w=iw:h=135:color=black@0.38:t=fill,'
            f'drawtext=fontfile=font.ttf:textfile=title-{i}.txt:fontsize=38:fontcolor=white:x=64:y=50,'
            'drawtext=fontfile=font.ttf:text=SEOUL APARTMENT:fontsize=18:fontcolor=white@0.85:x=64:y=h-58,'
            f'fade=t=in:d=0.25,fade=t=out:st={length-.25}:d=0.25,format=yuv420p')
        clip=work/f'clip-{i:02}.mp4'
        run(['-loop','1','-framerate',str(fps),'-i',str(image),'-vf',filters,'-t',str(length),
             '-an','-c:v','libx264','-preset','fast','-crf','19','-threads','6','-filter_threads','8',str(clip)],f'clip-{i}.log')
        clips.append(clip.name);offset+=length
        print('Rendered',chapter['capture_id'],length,'seconds',flush=True)
    wav=export/'seoul-tour-en.wav'
    with wave.open(str(wav),'wb') as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate);audio.writeframes(b''.join(pcm))
    (work/'concat.txt').write_text('\n'.join(f"file '{name}'" for name in clips))
    run(['-f','concat','-safe','0','-i','concat.txt','-i',str(wav),'-map','0:v:0','-map','1:a:0',
         '-c:v','copy','-c:a','aac','-b:a','160k','-movflags','+faststart','-shortest',str(export/'seoul-tour-en.mp4')],'mux.log')
    transcript=['SEOUL APARTMENT — ENGLISH TOUR','AI-generated voice: gpt-4o-mini-tts / alloy.',
        'Narration based on eight supplied panoramas. Premade source-assisted model; approximate scale.','']
    vtt=['WEBVTT',''];cue=0
    for chapter in timeline:
        transcript.extend([f'[{stamp(chapter["start"])}] {chapter["title"]}',chapter['text'],''])
        sentences=[s.strip()+'.' for s in chapter['text'].split('.') if s.strip()]
        words=sum(len(s.split()) for s in sentences);current=chapter['start']+.35
        duration=chapter['duration']-.85
        for sentence in sentences:
            end=current+duration*len(sentence.split())/words;cue+=1
            vtt.extend([str(cue),f'{stamp(current)} --> {stamp(end)}',sentence,'']);current=end
    (export/'seoul-tour-en.txt').write_text('\n'.join(transcript),encoding='utf-8')
    (export/'seoul-tour-en.vtt').write_text('\n'.join(vtt),encoding='utf-8')
    package={'locale':'en','scope':'seoul_sample_only','voice_source':'openai_generated',
             'voice_model':'gpt-4o-mini-tts','duration_seconds':round(offset,3),'chapters':timeline,
             'caption_timing':'Sentence timing estimated within each measured audio chapter.',
             'video_resolution':[1920,1080],'source_panorama_resolution':[2048,1024]}
    for kind,extension,mime in [('video','mp4','video/mp4'),('audio','wav','audio/wav'),('transcript','txt','text/plain'),('captions','vtt','text/vtt')]:
        path=export/f'seoul-tour-en.{extension}';name='house/exports/'+path.name;digest=hashlib.sha256(path.read_bytes()).hexdigest()
        package[kind]=name;catalog['assets'][name]={'key':f'demos/seoul-apartment/{digest}/{name}','sha256':digest,'bytes':path.stat().st_size,'content_type':mime}
    catalog['exports']=package
    (output/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n',encoding='utf-8')
    (output/'exports.json').write_text(json.dumps(package,indent=2)+'\n',encoding='utf-8')
    print('EXPORT PACKAGE READY',round(offset,2),'seconds',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['catalog-dir','voice-dir','output','font']:p.add_argument('--'+name,required=True)
    args=vars(p.parse_args());render(**args)
