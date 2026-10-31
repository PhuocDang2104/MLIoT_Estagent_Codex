"""Licensed demo music, selectable without an external network dependency."""
from pathlib import Path
import json
from fastapi import HTTPException
from .store import wav_duration

PLACEHOLDER = Path(__file__).resolve().parents[2]/'web/assets/music/dream-culture-placeholder.wav'
CREDIT = ('Dream Culture — Kevin MacLeod (incompetech.com). '
          'CC BY 4.0 https://creativecommons.org/licenses/by/4.0/; 75-second excerpt with fades.')


def replace_music(store, project_id, name, data, credit):
    """Called under the store lock; published asset IDs must remain immutable."""
    if store.rows('SELECT id FROM published WHERE project=?', (project_id,)):
        raise HTTPException(409, 'Published music is preserved. Create a new project to change it.')
    duration = wav_duration(data)
    assets = store.assets(project_id)
    if sum(a['size'] for a in assets if a['kind'] != 'music') + len(data) > 80*1024*1024:
        raise HTTPException(413, 'The project exceeds the 80 MB limit.')
    result = store.put_asset(project_id, name, 'music', 'audio/wav', data,
        {'width':0, 'height':0, 'duration':duration, 'credit':credit, 'warning':None})
    result.update(name=name, credit=credit)
    store.execute('UPDATE assets SET meta=? WHERE id=?', (json.dumps(result,ensure_ascii=False),result['id']))
    # Draft packages may reference old music; publish resolves the current track afresh.
    store.execute("DELETE FROM assets WHERE project=? AND json_extract(meta,'$.kind')='music' AND id<>?",
                  (project_id,result['id']))
    return result
