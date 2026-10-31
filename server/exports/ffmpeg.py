"""Native fixed-template FFmpeg backend. No shell/text filter interpolation."""
import json
import math
import time
from PIL import Image, ImageDraw, ImageFont, ImageOps
from .render import run_process


def wrapped(draw, text, font, width):
    lines=[];line=''
    for char in str(text):
        if char=='\n' or draw.textlength(line+char,font=font)>width:
            lines.append(line);line='' if char=='\n' else char
        else: line+=char
    if line: lines.append(line)
    return lines


def artwork(edit,scene,index,directory,web):
    width,height=edit['width'],edit['height']
    with Image.open(directory/scene['file']) as image:
        image=ImageOps.fit(image.convert('RGB'),(width,height),method=Image.Resampling.LANCZOS)
        image.save(directory/f'photo-{index}.png')
    overlay=Image.new('RGBA',(width,height),(0,0,0,0));draw=ImageDraw.Draw(overlay)
    fontpath=str(web/'assets/manrope-variable.ttf')
    def block(text,size,x,y,maxwidth):
        font=ImageFont.truetype(fontpath,size);lines=wrapped(draw,text,font,maxwidth-32)
        lineheight=int(size*1.4);bottom=y+len(lines)*lineheight+24
        draw.rectangle((x,y,x+maxwidth,bottom),fill='#102829')
        for j,line in enumerate(lines):draw.text((x+16,y+10+j*lineheight),line,font=font,fill='white')
        return bottom
    block(edit['title'],26,int(width*.06),int(height*.04),int(width*.88))
    text=scene['narration']['transcript'] if scene['narration'] and scene['narration']['transcript'] else scene['description']
    text=text if len(text)<=160 else text[:157]+'…'
    body=f'{index+1} / {len(edit["scenes"])} · {edit["locale"].upper()}\n{scene["name"]}\n{text}'
    size=28 if edit['aspect']=='portrait' else 24;maxwidth=int(width*(.88 if edit['aspect']=='portrait' else .62))
    font=ImageFont.truetype(fontpath,size);lines=wrapped(draw,body,font,maxwidth-32)
    block(body,size,int(width*.06),int(height*.90)-len(lines)*int(size*1.4)-24,maxwidth)
    block('Edited images · Not 3D' if edit['locale']=='vi' else 'Edited photos · Not 3D',16,int(width*.06),int(height*.95),int(width*.6))
    overlay.save(directory/f'text-{index}.png')


def render_native(edit,directory,output,web,timeout=180,scope=None):
    start=time.monotonic();logs=[]
    def run(args,name):
        remaining=timeout-(time.monotonic()-start)
        if remaining<=0:raise RuntimeError('Renderer timed out')
        log=directory/name
        result=run_process(args,directory,remaining,log,scope)
        logs.append(log.read_text(errors='replace'))
        (directory/'renderer.log').write_text('\n'.join(logs))
        return result
    common=['ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y','-threads','1','-filter_threads','1','-filter_complex_threads','1']
    clips=[]
    for i,scene in enumerate(edit['scenes']):
        artwork(edit,scene,i,directory,web)
        frames=round(scene['duration']*24);denominator=max(1,frames-1)
        if edit['aspect']=='portrait':
            motion=f"zoompan=z=1.08:x='(iw-iw/zoom)*on/{denominator}':y='(ih-ih/zoom)/2':d={frames}:s={edit['width']}x{edit['height']}:fps=24"
        else:
            motion=f"zoompan=z='1.04+0.04*on/{denominator}':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)*on/{denominator}':d={frames}:s={edit['width']}x{edit['height']}:fps=24"
        graph=f'[0:v]{motion}[picture];[picture][1:v]overlay=0:0:shortest=1,format=yuv420p[out]'
        clip=f'scene-{i}.mp4';clips.append(clip)
        run(common+['-i',f'photo-{i}.png','-loop','1','-i',f'text-{i}.png','-filter_complex',graph,'-map','[out]','-frames:v',str(frames),'-an','-c:v','libx264','-preset','veryfast','-crf','23','-threads','1','-movflags','+faststart',clip],f'scene-{i}.log')
    (directory/'clips.txt').write_text(''.join(f"file '{name}'\n" for name in clips))
    run(common+['-f','concat','-safe','1','-i','clips.txt','-c','copy','-an','video.mp4'],'concat.log')
    args=common+['-i','video.mp4'];filters=[];inputs=[];number=1
    if edit['music']:
        args+=['-i',edit['music_file']]
        intervals='+'.join(f"between(t,{s['start']},{s['start']+s['narration']['track']['duration_seconds']})" for s in edit['scenes'] if s['narration']) or '0'
        filters.append(f"[{number}:a]volume='if({intervals},0.05,0.25)':eval=frame[a{number}]")
        inputs.append(f'[a{number}]');number+=1
    for scene in edit['scenes']:
        if scene['narration']:
            args+=['-i',scene['voice_file']]
            delay=round(scene['start']*1000)
            filters.append(f'[{number}:a]adelay={delay}:all=1[a{number}]');inputs.append(f'[a{number}]');number+=1
    if inputs:
        filters.append(''.join(inputs)+f'amix=inputs={len(inputs)}:normalize=0,apad,atrim=duration={edit["duration"]}[audio]')
        args+=['-filter_complex',';'.join(filters),'-map','0:v','-map','[audio]','-c:a','aac','-b:a','128k']
    else:args+=['-map','0:v','-an']
    run(args+['-c:v','copy','-t',str(edit['duration']),'-threads','1','-movflags','+faststart',str(output)],'mux.log')
