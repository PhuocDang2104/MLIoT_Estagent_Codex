"""Explicit local QA server with synthetic model responses; no paid services."""
import os
from server.assistant.app import create_app
from tests.ai.creator_fixtures import Provider, Worker

app = create_app(db_path=os.environ['CREATOR_QA_DB'],
    env={'ASSISTANT_ORIGIN':os.environ.get('CREATOR_QA_ORIGIN','http://127.0.0.1:5186'),'STUDIO_GEOMETRY':'off'},
    creator_provider=Provider(),creator_worker=Worker() if os.environ.get('CREATOR_QA_WORKER') == '1' else None)
