"""Adapt approved cached-demo facts into the existing published Manifest, offline."""
import hashlib,json
from pathlib import Path
from server.tours.models import Manifest

def scene_id(demo_id,capture):return hashlib.sha256((demo_id+'\n'+capture).encode()).hexdigest()[:32]
def snapshot_id(guide):
    rows=sorted([[r['capture_id'],r['room_id'],r['locale'],r.get('description') or r['script']] for r in guide])
    return hashlib.sha256(json.dumps(rows,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()[:32]

def build_snapshot(house,guide,demo_id='zind-house-000'):
    selected=[(r,c) for r in house['rooms'] for c in r['dollhouseCaptureIds']];captures={c['id']:c for c in house['captures']};scenes=[]
    for room,capture in selected:
        descriptions={item['locale']:item.get('description') or item['script'] for item in guide if item['capture_id']==capture and item['room_id']==room['id']}
        if not descriptions:raise ValueError('Missing approved room description')
        text='\n'.join(locale.upper()+': '+descriptions[locale] for locale in sorted(descriptions))
        image=f'/api/demos/{demo_id}/assets'+captures[capture]['url']
        scenes.append({'id':scene_id(demo_id,capture),'asset_id':hashlib.sha256(image.encode()).hexdigest()[:32],
            'name':room['label']+' · '+capture,'description':text,'image_url':image,'thumbnail_url':image,'projection':'photo'})
    return Manifest.model_validate({'id':snapshot_id(guide),'revision':1,'status':'published','title':'ZInD sample home · Visitor chat','locale':'vi','scenes':scenes,'start_scene_id':scenes[0]['id'],'credits':['Approved cached-demo room descriptions; observed facts are not measurements.']}).model_dump()

def load_snapshots(raw):
    if raw is None:return {}
    root=Path(raw)
    if not str(raw).strip() or not root.is_dir():raise ValueError('TOUR_PUBLIC_SNAPSHOTS_DIR must point to the prepared snapshot directory')
    files=list(root.glob('*.json'))
    if len(files)>100:raise ValueError('Too many public snapshots')
    docs={}
    for path in files:
        doc=Manifest.model_validate_json(path.read_text()).model_dump()
        if doc['status']!='published' or path.stem!=doc['id']:raise ValueError('Public snapshot filename/status mismatch')
        docs[doc['id']]=doc
    return docs
