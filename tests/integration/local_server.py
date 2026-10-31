"""TEST ONLY: synthetic provider, real HTTP/SQLite. Never loads env or uses secrets."""
import argparse
import os
import uvicorn
from server.assistant.app import create_app


def interpreter(context):
    ids=[s['id'] for s in context['tour']['scenes']]
    if context['mode']=='viewer' and context['text']=='Is a sofa guaranteed to fit?':
        return {'reply':'No verified measurements are supplied. Ask the listing agent for dimensions before deciding.','changes':[],'order':None,'start_scene_id':None}
    if context['mode']=='creator' and context['text']=='Rename the first scene Lobby and reverse the order.':
        return {'reply':'Test provider fixture: renamed the first scene Lobby and reversed the order.','changes':[{'scene_id':ids[0],'name':'Lobby','description':'Synthetic test description, not a real listing.'}],'order':ids[::-1],'start_scene_id':ids[-1]}
    raise ValueError('Input not in the finite test provider fixture')

class ReadyServer(uvicorn.Server):
    async def startup(self,sockets=None):
        await super().startup(sockets)
        if self.started:print('INTEGRATION_READY',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--port',type=int,required=True);p.add_argument('--mode',choices=['missing-key','fixture'],required=True);args=p.parse_args()
    assert not any(k.startswith(('OPENAI_','LANGSMITH_','LANGCHAIN_')) for k in os.environ)
    app=create_app(db_path=args.db,env={'ASSISTANT_ORIGIN':f'http://127.0.0.1:{args.port}'},tour_interpreter=interpreter if args.mode=='fixture' else None)
    ReadyServer(uvicorn.Config(app,host='127.0.0.1',port=args.port,log_level='warning')).run()
