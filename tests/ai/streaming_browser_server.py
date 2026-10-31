"""Synthetic public-summary stream for isolated, unpaid browser verification."""
import os
import time
from pathlib import Path
import uvicorn
from server.assistant.app import create_app
from tests.ai.creator_fixtures import Provider, Worker
from tests.core.house_fixture import house_plan


class StreamingProvider(Provider):
    supports_modeling_progress=True
    def modeling_plan(self,project,rooms,observations,assets,read_asset,clarification,on_progress=None):
        started=time.time()*1000
        for i in range(35):
            on_progress({'model':'Astra stream fixture','effort':'high','phase':'thinking',
                'started_at':started,'elapsed_seconds':round(i*.2),'plan_preview':{},'output_characters':0,
                'reasoning_summary':'Synthetic public summary. Not live model output.\n'+
                    '\n'.join(f'Check {j}: compare supplied walls and visible fixtures.' for j in range(i+1))})
            time.sleep(.2)
        return house_plan([r['asset_id'] for r in rooms])


class PlannedWorker(Worker):
    requires_scene_plan=True


if __name__=='__main__':
    root=Path(os.environ['STREAM_QA_DIR'])
    app=create_app(db_path=root/'assistant.sqlite',env={'ASSISTANT_ORIGIN':'http://127.0.0.1:5192','STUDIO_GEOMETRY':'off'},
                   creator_provider=StreamingProvider(),creator_worker=PlannedWorker())
    uvicorn.run(app,host='127.0.0.1',port=5192,access_log=False)
