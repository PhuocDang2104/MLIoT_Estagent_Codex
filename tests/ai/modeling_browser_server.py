"""Explicit QA: synthetic planner, actual automatic Blender worker, no API key."""
import os
from server.assistant.app import create_app
from tests.ai.test_modeling import PlanningProvider

app=create_app(db_path=os.environ['CREATOR_QA_DB'],env={
    'ASSISTANT_ORIGIN':'http://127.0.0.1:5191','STUDIO_GEOMETRY':'blender',
    **({'STUDIO_BLENDER_EXECUTABLE':os.environ['STUDIO_BLENDER_EXECUTABLE']} if os.environ.get('STUDIO_BLENDER_EXECUTABLE') else {})
},creator_provider=PlanningProvider())
