"""QA ONLY private synthetic DB, zero provider keys; wait endpoint joins real worker."""
import argparse
from contextlib import asynccontextmanager
import os
from pathlib import Path
import uvicorn
from server.assistant.app import create_app

class ReadyServer(uvicorn.Server):
    async def startup(self,sockets=None):
        await super().startup(sockets)
        if self.started: print('EXPORT_TEST_READY',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--cli',required=True);args=p.parse_args()
    assert not any(k.startswith(('OPENAI_','LANGSMITH_','LANGCHAIN_','MINIO_')) for k in os.environ)
    app=create_app(db_path=Path(args.root)/'assistant.sqlite',env={'ASSISTANT_ORIGIN':f'http://127.0.0.1:{args.port}','VIDEO_EXPORT_ENABLED':'1','VIDEO_EXPORT_LOCAL_QA':'1','VIDEO_EXPORT_HYPERFRAMES':args.cli})
    original=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(app):
        async with original(app):
            try: yield
            finally: app.state.close_video_exports()
    app.router.lifespan_context=lifespan
    @app.get('/__qa/wait')
    def wait():
        app.state.wait_video_exports();return {'joined_real_worker':True}
    ReadyServer(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_level='warning')).run()
