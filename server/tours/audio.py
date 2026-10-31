"""User-uploaded PCM WAV only. No codecs/providers, immutable normalized blobs."""
import hashlib
import io
import json
import logging
import re
import secrets
import struct
import wave
from urllib.parse import unquote

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import ValidationError
from server.storage import upload_reservation
from .models import AudioProvenance, AudioUpdate, AudioTrack

MAX_AUDIO_BYTES = 20 * 1024 * 1024
MAX_AUDIO_SECONDS = 180
SAMPLE_RATES = {8000,11025,16000,22050,24000,32000,44100,48000}


def decode_wav(body):
    if len(body)>MAX_AUDIO_BYTES: raise HTTPException(413,'WAV exceeds 20 MiB / WAV vượt 20 MiB.')
    try:
        if len(body)<44 or body[:4]!=b'RIFF' or body[8:12]!=b'WAVE' or struct.unpack_from('<I',body,4)[0]+8!=len(body):
            raise ValueError('Invalid RIFF length/signature')
        chunks={}; offset=12
        while offset<len(body):
            if offset+8>len(body): raise ValueError('Truncated chunk header')
            tag=body[offset:offset+4];size=struct.unpack_from('<I',body,offset+4)[0]
            end=offset+8+size
            if end+(size%2)>len(body):raise ValueError('Truncated chunk')
            if tag in {b'fmt ',b'data'}:
                if tag in chunks:raise ValueError('Duplicate format/data chunk')
                chunks[tag]=body[offset+8:end]
            offset=end+(size%2)
        fmt=chunks[b'fmt '];pcm=chunks[b'data']
        encoding,channels,rate,byte_rate,alignment,bits=struct.unpack_from('<HHIIHH',fmt)
        if encoding!=1 or bits!=16 or channels not in {1,2} or rate not in SAMPLE_RATES:
            raise HTTPException(415,'Only PCM WAV 16-bit, mono/stereo, 8–48 kHz supported / Chỉ nhận WAV PCM 16-bit, mono/stereo, 8–48 kHz.')
        if alignment!=channels*2 or byte_rate!=rate*alignment or not pcm or len(pcm)%alignment:
            raise ValueError('Invalid PCM frame layout')
        frames=len(pcm)//alignment
        duration=frames/rate
        if duration>MAX_AUDIO_SECONDS:raise HTTPException(413,'Audio exceeds 180 seconds / Audio dài quá 180 giây.')
        with wave.open(io.BytesIO(body),'rb') as source:
            if source.getcomptype()!='NONE' or source.getnframes()!=frames or source.readframes(frames+1)!=pcm:
                raise ValueError('Incomplete PCM payload')
        # Drop RIFF metadata, never keep arbitrary uploaded chunks or paths.
        output=io.BytesIO()
        with wave.open(output,'wb') as normalized:
            normalized.setnchannels(channels);normalized.setsampwidth(2);normalized.setframerate(rate);normalized.writeframes(pcm)
        return output.getvalue(),{'duration_seconds':duration,'channels':channels,'sample_rate':rate,'sample_width':2,'content_type':'audio/wav'}
    except (ValueError,KeyError,struct.error,wave.Error,EOFError,OSError):
        raise HTTPException(415,'Invalid or truncated PCM WAV / WAV PCM lỗi hoặc thiếu dữ liệu.') from None


def audio_tracks(doc):
    audio=doc.get('audio') or {}
    return ([audio['music']] if audio.get('music') else [])+[n['track'] for n in audio.get('narration') or []]


def summarize_audio(doc):
    audio=doc.get('audio') or {'music':None,'narration':None,'source':'none','status':'unavailable'}
    narrations=audio.get('narration') or []
    has_audio=bool(audio.get('music') or narrations)
    complete=all(any(n['scene_id']==s['id'] and n['locale']==doc['locale'] for n in narrations) for s in doc['scenes'])
    audio['status']='ready' if complete else 'partial' if has_audio else 'unavailable'
    tracks=([audio['music']] if audio.get('music') else [])+[n['track'] for n in narrations]
    generated=sum(bool(t.get('generation')) for t in tracks)
    audio['source']='none' if not tracks else 'openai_generated' if generated==len(tracks) else 'mixed' if generated else 'user_uploaded'
    doc['audio']=audio
    return doc


def audio_urls(doc,prefix):
    for track in audio_tracks(doc):track['url']=f'{prefix}/{track["asset_id"]}'
    return doc


def install_audio(router,db,owner,draft,check_revision,validate_doc,published,data_root,*,object_storage=None):
    def prepare(conn):
        conn.execute('CREATE TABLE IF NOT EXISTS audio_assets(id TEXT PRIMARY KEY,owner TEXT NOT NULL,digest TEXT NOT NULL,metadata TEXT NOT NULL,UNIQUE(owner,digest))')

    def get_track(conn,id,who):
        prepare(conn)
        row=conn.execute('SELECT metadata FROM audio_assets WHERE id=? AND owner=?',(id,who)).fetchone()
        if not row:raise HTTPException(404,'Audio not found in this session / Không tìm thấy audio trong phiên này.')
        return json.loads(row['metadata'])

    def audio_file(id,range_header=None,verify_only=False):
        if not re.fullmatch(r'[a-f0-9]{32}',id):raise HTTPException(404)
        with db() as conn:
            remote=conn.execute("SELECT 1 FROM media_storage WHERE kind='audio' AND id=? AND backend='minio'",(id,)).fetchone()
        if remote:
            if object_storage is None:raise HTTPException(503,'Object storage unavailable')
            key=f'tours/audio/{id}.wav'
            if verify_only:object_storage.stat(key);return None
            return object_storage.response(key,range_header=range_header)
        path=data_root/'audio'/f'{id}.wav'
        if not path.is_file():raise HTTPException(404,'Audio file unavailable / Không còn file audio.')
        if verify_only:return None
        return FileResponse(path,media_type='audio/wav')

    @router.post('/audio-assets')
    async def upload_audio(request:Request):
        who=owner(request)
        metadata=request.headers.get('x-audio-metadata','')
        if not metadata or len(metadata)>4096:raise HTTPException(422,'Audio source and rights declaration required / Cần khai nguồn và quyền sử dụng audio.')
        try:provenance=AudioProvenance.model_validate_json(unquote(metadata))
        except (ValidationError,ValueError):raise HTTPException(422,'Invalid audio source/rights declaration / Nguồn hoặc khai báo quyền audio không hợp lệ.') from None
        normalized,measurements=decode_wav(await request.body())
        digest=hashlib.sha256(normalized+provenance.model_dump_json().encode()).hexdigest()
        with db() as conn:
            prepare(conn)
            previous=conn.execute('SELECT metadata FROM audio_assets WHERE owner=? AND digest=?',(who,digest)).fetchone()
            if previous:return json.loads(previous['metadata'])
            if conn.execute('SELECT count(*) FROM audio_assets WHERE owner=?',(who,)).fetchone()[0]>=100:
                raise HTTPException(413,'Session audio limit reached (100) / Phiên đã có 100 file audio.')
            id=secrets.token_hex(16)
            track={'asset_id':id,'url':f'/api/tours/audio-assets/{id}',**measurements,**provenance.model_dump()}
            directory=data_root/'audio'
            target=directory/f'{id}.wav'
            attempted=False
            with upload_reservation(request,4096 if object_storage else len(normalized)):
                try:
                    if object_storage:
                        attempted=True
                        object_storage.put_bytes(f'tours/audio/{id}.wav',normalized,'audio/wav')
                        conn.execute("INSERT INTO media_storage VALUES('audio',?,'minio')",(id,))
                    else:
                        directory.mkdir(exist_ok=True,mode=0o700)
                        with target.open('xb') as output:output.write(normalized)
                    conn.execute('INSERT INTO audio_assets VALUES(?,?,?,?)',(id,who,digest,json.dumps(track)))
                    conn.commit()
                except BaseException:
                    conn.rollback()
                    if object_storage and attempted:
                        try:object_storage.remove(f'tours/audio/{id}.wav')
                        except Exception:logging.getLogger(__name__).warning('Orphan media cleanup failed; operator reconciliation required')
                    elif not object_storage:target.unlink(missing_ok=True)
                    raise
        return track

    @router.get('/audio-assets/{id}')
    def private_audio(id:str,request:Request):
        with db() as conn:get_track(conn,id,owner(request))
        return audio_file(id,range_header=request.headers.get('range'))

    @router.put('/drafts/{id}/audio')
    def attach_audio(id:str,data:AudioUpdate,request:Request):
        who=owner(request)
        with db() as conn:
            row,doc=draft(conn,id,who);check_revision(doc,data.revision)
            ids={s['id'] for s in doc['scenes']}
            pairs=[(n.scene_id,n.locale) for n in data.narration]
            if len(set(pairs))!=len(pairs) or any(n.scene_id not in ids for n in data.narration):
                raise HTTPException(422,'Narration requires unique existing scene/language pairs / Lời phải thuộc cặp điểm xem và ngôn ngữ duy nhất.')
            music=get_track(conn,data.music_asset_id,who) if data.music_asset_id else None
            narrations=[{'scene_id':n.scene_id,'locale':n.locale,'transcript':n.transcript,'track':get_track(conn,n.asset_id,who)} for n in data.narration]
            for n in narrations:
                generation=n['track'].get('generation')
                if generation:
                    if generation['locale']!=n['locale'] or generation['script_sha256']!=hashlib.sha256(n['transcript'].encode()).hexdigest():
                        raise HTTPException(422,'Generated speech must keep its approved script and language.')
                elif n['locale']!=doc['locale']:
                    raise HTTPException(422,'Uploaded narration requires the tour source locale.')
            doc['audio']={'music':music,'narration':narrations or None,'status':'unavailable','source':'none'}
            for track in audio_tracks(doc):audio_file(track['asset_id'],verify_only=True)
            doc['revision']+=1
            doc=validate_doc(summarize_audio(doc))
            conn.execute('UPDATE drafts SET doc=?,reviewed=NULL WHERE id=?',(json.dumps(doc),id))
        return doc

    @router.get('/published/{id}/audio/{asset_id}')
    def public_audio(id:str,asset_id:str,request:Request):
        doc=published(id)
        if not any(track['asset_id']==asset_id for track in audio_tracks(doc)):raise HTTPException(404)
        return audio_file(asset_id,range_header=request.headers.get('range'))

    def verify_publish(conn,doc,who):
        for track in audio_tracks(doc):
            stored=get_track(conn,track['asset_id'],who)
            if AudioTrack.model_validate(track)!=AudioTrack.model_validate(stored):raise HTTPException(409,'Audio metadata changed; reattach before publishing / Hãy gắn lại audio trước khi xuất bản.')
            audio_file(track['asset_id'],verify_only=True)
    return verify_publish
