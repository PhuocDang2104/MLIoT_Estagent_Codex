"""Short real admission windows for the upload-only browser regression. No providers."""
import os
from pathlib import Path
from server.assistant.app import create_app

root = Path(os.environ['UPLOAD_QA_DIR'])
app = create_app(db_path=root/'assistant.sqlite', env={
    'ASSISTANT_ORIGIN': 'http://127.0.0.1:5195', 'STUDIO_GEOMETRY': 'off',
    'API_LIMITS_ENABLED': '1', 'API_LIMITS_DB': str(root/'limits.sqlite'),
    'API_LIMITS_AI_REQUESTS': '6', 'API_LIMITS_AI_WINDOW_SECONDS': '60',
    'API_LIMITS_AI_CONCURRENCY': '1', 'API_LIMITS_AI_ATTEMPTS': '50',
    'API_LIMITS_AI_ATTEMPT_WINDOW_SECONDS': '3600',
    'API_LIMITS_UPLOAD_REQUESTS': '6', 'API_LIMITS_UPLOAD_WINDOW_SECONDS': '2',
    'API_LIMITS_UPLOAD_CONCURRENCY': '1',
})
