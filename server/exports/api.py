"""Private persistent export admission and one service-wide local renderer."""
import fcntl
import json
import secrets
import shutil
import threading
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from .plan import plan
from .render import materialize, render, ProcessScope


class CreateExport(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tour_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    aspect: Literal['portrait','landscape']
    request_id: str = Field(pattern=r'^[A-Za-z0-9-]{8,80}$')


def install(app, env, data_root, db, owner, storage, web):
    data_root, web = data_root.resolve(), web.resolve()
    router = APIRouter(prefix='/api/tours/exports')
    enabled = env.get('VIDEO_EXPORT_ENABLED', '0')
    local = env.get('VIDEO_EXPORT_LOCAL_QA', '0')
    if enabled not in {'0','1'} or local not in {'0','1'}:
        raise ValueError('VIDEO_EXPORT_ENABLED/VIDEO_EXPORT_LOCAL_QA must be 0 or 1')
    cli = Path(env.get('VIDEO_EXPORT_HYPERFRAMES', ''))
    if enabled=='1' and (not cli.is_absolute() or not cli.is_file()):
        raise ValueError('VIDEO_EXPORT_HYPERFRAMES must name an installed absolute CLI .mjs path')
    if enabled=='1':
        for executable in ('node','ffmpeg','ffprobe'):
            if shutil.which(executable) is None:
                raise ValueError(f'Video export requires {executable} on PATH')
    folder = data_root/'exports'
    # No export DB/files/worker side effects on the current rollout when disabled.
    if enabled=='1':
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        with db() as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS video_exports(
                id TEXT PRIMARY KEY,owner TEXT NOT NULL,request_id TEXT NOT NULL,body TEXT NOT NULL,
                snapshot TEXT NOT NULL,edit TEXT NOT NULL,state TEXT NOT NULL,stage TEXT NOT NULL,
                error TEXT,created REAL NOT NULL,backend TEXT,UNIQUE(owner,request_id))''')
        with (folder/'renderer.lock').open('a') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: pass  # Another service process owns the actual renderer.
            else:
                with db() as conn:
                    conn.execute("UPDATE video_exports SET state='error',stage='interrupted',error='Server restarted; explicit new export required' WHERE state IN ('queued','rendering')")
                fcntl.flock(lock, fcntl.LOCK_UN)
    guard = threading.Lock()
    worker = None
    processes = ProcessScope()

    def owned(conn, id, who):
        row = conn.execute('SELECT p.doc FROM published p JOIN drafts d ON p.draft=d.id WHERE p.id=? AND d.owner=?',(id,who)).fetchone()
        if not row: raise HTTPException(404, 'Published snapshot not found in this session')
        return json.loads(row['doc'])

    def admission():
        if enabled!='1': raise HTTPException(503, 'Video export is not enabled on this server')
        if local!='1':
            from server.object_storage import KEY
            if storage is None or not KEY.fullmatch('tours/exports/'+'0'*32+'.mp4'):
                raise HTTPException(503, 'Private video storage integration required; no local production fallback')

    def result(row):
        return dict(id=row['id'], state=row['state'], stage=row['stage'], error=row['error'],
                    aspect=json.loads(row['body'])['aspect'], download=f'/api/tours/exports/{row["id"]}/download' if row['state']=='ready' else None)

    def update(id, state, stage, error=None, backend=None):
        with db() as conn:
            conn.execute('UPDATE video_exports SET state=?,stage=?,error=?,backend=? WHERE id=?',(state,stage,error,backend,id))

    def work():
        nonlocal worker
        with (folder/'renderer.lock').open('a') as lock:
            try: fcntl.flock(lock, fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: return
            while True:
                with guard:
                    with db() as conn:
                        row=conn.execute("SELECT * FROM video_exports WHERE state='queued' ORDER BY created LIMIT 1").fetchone()
                        if not row:
                            fcntl.flock(lock,fcntl.LOCK_UN)
                            worker=None
                            return
                        conn.execute("UPDATE video_exports SET state='rendering',stage='reading-source' WHERE id=?",(row['id'],))
                id=row['id'];workdir=folder/(id+'-work');output=folder/(id+'.mp4')
                try:
                    workdir.mkdir(mode=0o700)
                    edit=json.loads(row['edit'])
                    materialize(edit,workdir,data_root,db,storage)
                    update(id,'rendering','renderer-running')
                    render(edit,workdir,output,cli,web,scope=processes)
                    if output.stat().st_size>50*1024*1024: raise RuntimeError('Export exceeds 50 MiB output limit')
                    if local=='1': backend='local-qa'
                    else:
                        update(id,'rendering','storing-private-output')
                        storage.put_bytes(f'tours/exports/{id}.mp4',output.read_bytes(),'video/mp4')
                        output.unlink();backend='minio'
                    update(id,'ready','complete',backend=backend)
                except Exception as error:
                    # Worker failures persist visibly; never report ready or retry automatically.
                    message='Renderer timed out; children terminated' if 'timed out' in str(error) else 'Export failed; source/storage/renderer unavailable. Explicit retry required.'
                    update(id,'error','failed',message)
                    output.unlink(missing_ok=True)
                finally:
                    for log_name in ('renderer.log','check.json'):
                        if (workdir/log_name).is_file():
                            shutil.copyfile(workdir/log_name,folder/(id+'-'+log_name))
                    if workdir.exists(): shutil.rmtree(workdir,ignore_errors=False)
            fcntl.flock(lock,fcntl.LOCK_UN)

    @router.get('/sources')
    def sources(request: Request):
        who=owner(request)
        with db() as conn:
            rows=conn.execute('SELECT p.doc FROM published p JOIN drafts d ON p.draft=d.id WHERE d.owner=? ORDER BY p.rowid DESC',(who,)).fetchall()
        return {'enabled':enabled=='1','items':[{'id':d['id'],'title':d['title'],'revision':d['revision'],'locale':d['locale']} for d in (json.loads(r['doc']) for r in rows)]}

    @router.get('/preview/{tour_id}')
    def preview(tour_id: str, request: Request, aspect: Literal['portrait','landscape']='portrait'):
        with db() as conn: snapshot=owned(conn,tour_id,owner(request))
        return plan(snapshot,aspect)

    @router.post('')
    def create(data: CreateExport, request: Request):
        nonlocal worker
        who=owner(request);admission()
        body=data.model_dump_json()
        with guard:
            with db() as conn:
                conn.execute('BEGIN IMMEDIATE')
                existing=conn.execute('SELECT * FROM video_exports WHERE owner=? AND request_id=?',(who,data.request_id)).fetchone()
                if existing:
                    if existing['body']!=body: raise HTTPException(409,'Request ID already used for another export')
                    return result(existing)
                snapshot=owned(conn,data.tour_id,who);edit=plan(snapshot,data.aspect)
                if conn.execute("SELECT count(*) FROM video_exports WHERE state IN ('queued','rendering')").fetchone()[0]>=2:
                    raise HTTPException(429,'Export queue is full; try later')
                cutoff=time.time()-86400
                total=conn.execute('SELECT count(*) FROM video_exports WHERE created>?',(cutoff,)).fetchone()[0]
                own=conn.execute('SELECT count(*) FROM video_exports WHERE owner=? AND created>?',(who,cutoff)).fetchone()[0]
                if total>=12 or own>=4: raise HTTPException(429,'Daily export allowance reached')
                id=secrets.token_hex(16)
                conn.execute('INSERT INTO video_exports VALUES(?,?,?,?,?,?,?,?,?,?,?)',(id,who,data.request_id,body,json.dumps(snapshot),json.dumps(edit),'queued','queued',None,time.time(),None))
                row=conn.execute('SELECT * FROM video_exports WHERE id=?',(id,)).fetchone()
            if worker is None or not worker.is_alive():
                worker=threading.Thread(target=work,daemon=True,name='tour-video-export');worker.start()
        return result(row)

    def job(id,request):
        who=owner(request)
        if enabled!='1': raise HTTPException(503,'Video export is disabled')
        with db() as conn: row=conn.execute('SELECT * FROM video_exports WHERE id=? AND owner=?',(id,who)).fetchone()
        if not row: raise HTTPException(404,'Export not found')
        return row

    @router.get('/{id}')
    def status(id: str, request: Request): return result(job(id,request))

    @router.get('/{id}/download')
    def download(id: str, request: Request):
        row=job(id,request)
        if row['state']!='ready': raise HTTPException(409,'Export is not ready')
        if row['backend']=='minio':
            if storage is None: raise HTTPException(503,'Private video storage unavailable')
            return storage.response(f'tours/exports/{id}.mp4',range_header=request.headers.get('range'))
        path=folder/(row['id']+'.mp4')
        if not path.is_file(): raise HTTPException(404,'Export file unavailable')
        return FileResponse(path,media_type='video/mp4',filename='tour-'+json.loads(row['body'])['aspect']+'.mp4',content_disposition_type='inline',headers={'Cache-Control':'no-store'})

    app.include_router(router)
    # These exact new UI routes are installed before the existing filename allowlist.
    def page_route(name):
        def serve(): return FileResponse(web/name)
        return serve
    for name in ('export.html','export.js','export.css'):
        app.add_api_route('/'+name,page_route(name),methods=['GET'],include_in_schema=False)
    def wait(timeout=240):
        thread=worker
        if thread: thread.join(timeout)
        if thread and thread.is_alive(): raise TimeoutError('Export worker still active')
    app.state.wait_video_exports=wait

    def close():
        processes.close()
        wait(timeout=10)
    app.state.close_video_exports=close
