"""Offline HyperFrames composition, fixed argv and bounded child process group."""
import html
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import wave
import math

ID = re.compile(r'[a-f0-9]{32}')


class ProcessScope:
    def __init__(self):
        self.lock = threading.Lock()
        self.processes = set()
        self.closed = False

    def add(self, process):
        with self.lock:
            if self.closed:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
                raise RuntimeError('Export service is shutting down')
            self.processes.add(process)

    def remove(self, process):
        with self.lock:
            self.processes.discard(process)

    def close(self):
        with self.lock:
            self.closed = True
            for process in self.processes:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: continue  # Child already exited.


def run_process(argv, cwd, timeout, log, scope=None):
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'HOME', 'TMPDIR', 'LANG'}}
    env['DO_NOT_TRACK'] = '1'
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, start_new_session=True)
    if scope: scope.add(process)
    try:
        output, _ = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            output, _ = process.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
        log.write_bytes(output[-100000:])
        raise RuntimeError('Renderer timed out; process group terminated') from None
    finally:
        if scope: scope.remove(process)
    log.write_bytes(output[-100000:])
    if process.returncode:
        raise RuntimeError('Renderer failed; inspect private renderer log')
    return output


def materialize(edit, directory, data_root, db, storage):
    def asset(kind, id):
        if not ID.fullmatch(id):
            raise ValueError('Invalid internal asset ID')
        suffix = '.jpg' if kind == 'image' else '.wav'
        with db() as conn:
            remote = conn.execute('SELECT 1 FROM media_storage WHERE kind=? AND id=? AND backend=?', (kind, id, 'minio')).fetchone()
        if remote:
            if storage is None:
                raise RuntimeError('Source object storage unavailable; no local fallback')
            key = f'tours/{"images" if kind == "image" else "audio"}/{id}{suffix}'
            if storage.stat(key).size > 40*1024*1024:
                raise RuntimeError('Source media exceeds export size limit')
            content = storage.get_bytes(key)
        else:
            path = data_root / ('assets' if kind == 'image' else 'audio') / (id + suffix)
            if path.stat().st_size > 40*1024*1024:
                raise RuntimeError('Source media exceeds export size limit')
            content = path.read_bytes()
        (directory / (id + suffix)).write_bytes(content)
        return id + suffix
    for scene in edit['scenes']:
        scene['file'] = asset('image', scene['asset_id'])
        if scene['narration']:
            track = scene['narration']['track']
            scene['voice_file'] = asset('audio', track['asset_id'])
    if edit['music']:
        original = asset('audio', edit['music']['asset_id'])
        # Repeat validated PCM once into a bounded bed, not one HTML node per tiny clip.
        with wave.open(str(directory/original),'rb') as source:
            channels,width,rate=source.getnchannels(),source.getsampwidth(),source.getframerate()
            if channels not in (1,2) or width!=2 or not 8000<=rate<=48000:
                raise RuntimeError('Unsupported stored music encoding')
            frames=source.readframes(source.getnframes())
        if not frames: raise RuntimeError('Stored music is empty')
        needed=math.ceil(edit['duration']*rate)*channels*width
        bed=(frames*math.ceil(needed/len(frames)))[:needed]
        with wave.open(str(directory/'music-loop.wav'),'wb') as target:
            target.setnchannels(channels);target.setsampwidth(width);target.setframerate(rate);target.writeframes(bed)
        edit['music_file']='music-loop.wav'


def composition(edit, directory, web):
    shutil.copyfile(web / 'assets/manrope-variable.ttf', directory / 'font.ttf')
    portrait = edit['aspect'] == 'portrait'
    fragments = []
    duck = [{'t': 0, 'v': .25}]
    for i, scene in enumerate(edit['scenes']):
        start, duration = scene['start'], scene['duration']
        text = scene['narration']['transcript'] if scene['narration'] and scene['narration']['transcript'] else scene['description']
        excerpt = text if len(text) <= 160 else text[:157] + '…'
        esc = html.escape
        fragments.append(f'''<section id="scene-{i}" class="clip" data-start="{start}" data-duration="{duration}" data-track-index="0">
<div class="photo"><img alt="" src="{scene['file']}" style="animation: drift {duration}s linear {start}s 1 both"></div>
<div class="copy"><p class="count">{i+1} / {len(edit['scenes'])} · {edit['locale'].upper()}</p><h2>{esc(scene['name'])}</h2><p>{esc(excerpt)}</p></div></section>''')
        if scene['narration']:
            length = scene['narration']['track']['duration_seconds']
            fragments.append(f'<audio id="voice-{i}" src="{scene["voice_file"]}" data-start="{start}" data-duration="{length}" data-track-index="2" data-volume="1"></audio>')
            if start > 0: duck.append({'t': max(0,start-.05), 'v': .25})
            duck += [{'t': start, 'v': .05}, {'t': start+length, 'v': .05}, {'t': min(start+length+.15, start+duration), 'v': .25}]
    if edit['music']:
        points = [{'t': t, 'v': v} for t,v in sorted({p['t']:p['v'] for p in duck}.items())]
        automation = html.escape(json.dumps({'version':1,'lanes':[{'target':'volume','points':points}]}),quote=True)
        fragments.append(f'<audio id="music-bed" src="{edit["music_file"]}" data-start="0" data-duration="{edit["duration"]}" data-track-index="3" data-volume="1" data-automation="{automation}"></audio>')
    style = '''@font-face{font-family:Tour;src:url(font.ttf)}*{box-sizing:border-box}body{margin:0;color:#fff;background:#102829;font-family:Tour,sans-serif}#root{position:relative;width:100%;height:100%;overflow:hidden}.clip{position:absolute;inset:0}.photo{position:absolute;inset:0;overflow:hidden}.photo img{width:100%;height:100%;object-fit:cover}.copy{overflow-wrap:anywhere;position:absolute;left:6%;right:6%;bottom:8%;padding:24px;background:#102829}h2{font-size:38px;line-height:1.15;margin:8px 0}p{font-size:26px;line-height:1.4;margin:0}.count{font-size:18px;color:#d9e4cf}.title{overflow-wrap:anywhere;position:absolute;top:4%;left:6%;right:6%;font-size:26px;background:#102829;padding:12px;z-index:5}.note{position:absolute;bottom:2%;left:6%;font-size:16px;z-index:5;background:#102829;padding:4px}'''
    style += '@keyframes drift{from{transform:scale(1.08) translateX(-2%)}to{transform:scale(1.08) translateX(2%)}}' if portrait else '@keyframes drift{from{transform:scale(1.04) translateY(1%)}to{transform:scale(1.08) translateY(-1%)}}.copy{right:32%;bottom:10%}h2{font-size:32px}p{font-size:22px}'
    source = f'''<!doctype html><html lang="{edit['locale']}"><head><meta charset="UTF-8"><style>{style}</style></head><body><div id="root" data-composition-id="main" data-no-timeline data-width="{edit['width']}" data-height="{edit['height']}" data-duration="{edit['duration']}">{''.join(fragments)}<div class="title">{html.escape(edit['title'])}</div><div class="note">{'Ảnh theo thứ tự biên tập · Không phải 3D' if edit['locale']=='vi' else 'Edited photo sequence · Not 3D'}</div></div></body></html>'''
    (directory / 'index.html').write_text(source)


def render(edit, directory, output, cli, web, timeout=180, scope=None, renderer="hyperframes"):
    if renderer == 'ffmpeg':
        from .ffmpeg import render_native
        render_native(edit,directory,output,web,timeout,scope)
    elif renderer == 'hyperframes':
        composition(edit, directory, web)
        run_process(['node', str(cli), 'check', str(directory), '--json'], directory, 60, directory/'check.json', scope)
        run_process(['node', str(cli), 'render', str(directory), '--workers', '1', '--fps', '24',
                     '--quality', 'draft', '--output', str(output)], directory, timeout, directory/'renderer.log', scope)
    else:
        raise ValueError('VIDEO_EXPORT_RENDERER must be hyperframes or ffmpeg')
    raw = run_process(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)],
                      directory, 15, directory/'probe.json')
    info = json.loads(raw)
    video = next(s for s in info['streams'] if s['codec_type']=='video')
    if video['codec_name'] != 'h264' or (video['width'],video['height']) != (edit['width'],edit['height']):
        raise RuntimeError('Rendered codec or dimensions do not match export')
    if abs(float(info['format']['duration'])-edit['duration']) > .3:
        raise RuntimeError('Rendered duration mismatch')
    audio = [s for s in info['streams'] if s['codec_type']=='audio']
    if edit['audio_status']!='silent' and (not audio or audio[0]['codec_name']!='aac'):
        raise RuntimeError('Expected recorded AAC track missing')
    return info
