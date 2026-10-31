"""TEST ONLY: production application, isolated disk, no model/provider fixture."""
import argparse
import os
import uvicorn
from server.assistant.app import create_app

class ReadyServer(uvicorn.Server):
    async def startup(self,sockets=None):
        await super().startup(sockets)
        if self.started:print('AUDIO_TEST_READY',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--port',required=True,type=int);args=p.parse_args()
    assert not any(k.startswith(('OPENAI_','LANGSMITH_','LANGCHAIN_')) for k in os.environ)
    app=create_app(db_path=args.db,env={'ASSISTANT_ORIGIN':f'http://127.0.0.1:{args.port}'})
    ReadyServer(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_level='warning')).run()
