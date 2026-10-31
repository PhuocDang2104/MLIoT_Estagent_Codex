"""Prepare a source-derived, three-capture ZInD 000 subset for a local live test.

No API calls. Requires the existing handoff and original ZInD images under --workspace.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
from PIL import Image, ImageDraw, ImageFont


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    meta=args.workspace/'artifacts/handoff/zind-house-000/metadata'
    room=next(r for r in json.loads((meta/'floorplan.json').read_text())['rooms'] if r['id']=='complete_room_06')
    captures=json.loads((meta/'checkpoints.json').read_text())['captures']
    captures=[next(c for c in captures if c['id']==name) for name in ('pano_12','pano_7','pano_5')]
    args.output.mkdir(parents=True,exist_ok=True)
    for c in captures:
        source=args.workspace/c['sourcePath']
        assert hashlib.sha256(source.read_bytes()).hexdigest()==c['sha256']
        shutil.copyfile(source,args.output/Path(c['sourcePath']).name)
    poly=[[round(x,3),round(z,3)] for x,z in room['polygon']]
    lo=[min(p[i] for p in poly) for i in range(2)]
    scale=95
    def xy(p): return (100+(p[0]-lo[0])*scale,100+(p[1]-lo[1])*scale)
    image=Image.new('RGB',(1280,1050),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.load_default(size=19)
    draw.text((30,20),'ZInD 000 / open-plan kitchen, dining, living + hallway ONLY',fill='black',font=font)
    draw.text((30,50),'Metres; X right, Z down; Y up. Original annotated outline; no other rooms included.',fill='black',font=font)
    draw.polygon([xy(p) for p in poly],fill='#f3eee7',outline='#334b52',width=4)
    for i,p in enumerate(poly): draw.text(xy(p),str(i),fill='#994411',font=font)
    dims=[]
    for i,c in enumerate(captures,1):
        x,y,z=c['position']; m=c['cameraToWorld'];heading=math.degrees(math.atan2(m[0][2],-m[2][2]))
        at=xy((x,z));draw.ellipse((at[0]-8,at[1]-8,at[0]+8,at[1]+8),fill='#007f8b')
        draw.text((at[0]+12,at[1]-10),f'cp{i:02} / {c["id"]}',fill='#007f8b',font=font)
        dims.append({'checkpoint_id':f'cp{i:02}','file':Path(c['sourcePath']).name,
                     'position':{'x':round(x,3),'y':round(y,3),'z':round(z,3)},'heading':round(heading,2)})
    draw.text((30,950),'Height: %.3f m. Vertex numbers correspond to the outline in the description.'%room['height'],fill='black',font=font)
    draw.text((30,985),'Kitchen and dining: wood-look floor. Living: carpet. Furnishings only where photographed.',fill='black',font=font)
    image.save(args.output/'source-floorplan.png')
    description=('Real ZInD sample home 000; a limited open-plan kitchen/dining/living/hallway subset, NOT the whole house. '
        'Three original equirectangular panoramas. Unfurnished living/dining; model only visible kitchen built-ins and appliances. '
        'No invented furniture; author reusable materials, no panorama projection onto geometry. '
        'Source annotation gives one connected complete room; keep it as ONE space (r01) so no artificial subdivision walls. '
        'Mixed wood-look kitchen/dining and carpet living floors: one material per space is an acknowledged MVP limitation; choose wood and record carpet uncertainty. '
        'The attached derived floorplan outline uses world X/Z metres and Y up, height '+str(round(room['height'],3))+' m. '
        'Preserve this exact vertex order (indices start at 0): '+json.dumps(poly,separators=(',',':'))+'. '
        'Capture coordinates/heading from source annotations: '+json.dumps(dims,separators=(',',':'))+'. '
        'All three cameras share this open area; cp01-cp02 and cp02-cp03 are valid passage routes. '
        'Create only the supplied subset, leave excluded adjacent rooms unmodeled. Openings and fixtures may be approximate and must cite photos. '
        'Mark the model provisional for fixture placement; source-annotated outline and camera positions have metric scale. '
        'Narration should be short and describe visible features, not coordinate data or the modeling process.')
    assert len(description)<=6000
    (args.output/'project.json').write_text(json.dumps({'name':'ZInD 000 · Kitchen, dining & living',
        'description':description,'locale':'en','voice':'coral','panorama_confirmed':True},ensure_ascii=False,indent=2),encoding='utf-8')
    (args.output/'source-manifest.json').write_text(json.dumps({'room':room,'captures':captures,'prepared_captures':dims},indent=2),encoding='utf-8')
    print(json.dumps({'captures':len(captures),'description_characters':len(description),'output':str(args.output)}))


if __name__=='__main__': main()
