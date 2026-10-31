"""Prepare the user-approved Seoul sample. No uploads, archive execution or path trust.

First compress seoul-apartment-dollhouse.glb with glTF Transform 4.5.0 meshopt,
position=16, normal=12, texcoord=14 bits, without simplification. Pass that file.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

SOURCE_SHA = '254d6bc4a53ac452e07247b05b1418066f7ad4546a072e0ed1325a099e5b8d58'
IDS = ['00000000', '00000030', '00000070', '00000110', '00000150', '00000180', '00000250', '00000310']


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(bundle, model, panoramas, output):
    if sha(bundle) != SOURCE_SHA:
        raise ValueError('Unexpected source bundle; review provenance before importing')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    house = output/'house'
    (house/'panos').mkdir(parents=True)
    with zipfile.ZipFile(bundle) as archive:
        hashes = json.loads(archive.read('delivery-sha256.json'))
        extracted = {}
        for name in ['scene-manifest.json', 'floorplan.png', 'previews/model-preview.jpg']:
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != hashes[name]:
                raise ValueError('Bundle member hash mismatch')
            extracted[name] = data
        source = json.loads(extracted['scene-manifest.json'])
        (house/'floorplan.png').write_bytes(extracted['floorplan.png'])
        (house/'preview.jpg').write_bytes(extracted['previews/model-preview.jpg'])
    shutil.copyfile(model, house/'dollhouse-studio.glb')
    captures = []
    primary = ['entrance_passage', 'kitchen_dining', 'living', 'living', 'entrance_passage', 'bathroom', 'sleeping_alcove', 'sleeping_alcove']
    for index, capture in enumerate(source['captures']):
        if capture['id'] != IDS[index]:
            raise ValueError('Unexpected capture order')
        # Ignore absolute paths in the supplied manifest. Only use the explicit folder.
        image = Path(panoramas)/(capture['id']+'.jpg')
        if sha(image) != capture['sha256']:
            raise ValueError('Original panorama hash mismatch')
        shutil.copyfile(image, house/'panos'/image.name)
        x, y, z = capture['camera_to_world_translation']
        captures.append({
            'checkpoint_id': f'cp{index+1:02}', 'source_capture_id': capture['id'],
            'label': capture['label'], 'room_id': primary[index],
            'image': f'house/panos/{image.name}', 'sha256': capture['sha256'],
            'anchor': {'position': [x, z, -y], 'dollhouse_visible': index in [0, 1, 3, 5, 7],
                       'accuracy': 'approximate_real_world'},
            'source_euler_xyz': capture['camera_to_world_euler_xyz'],
            'world_forward': [-1, 0, 0], 'pose_status': capture['pose_status'],
            'initial_yaw_degrees': 0,
        })
    if len(captures) != 8:
        raise ValueError('Expected eight captures')
    manifest = {
        'id': 'seoul-apartment', 'title': 'Seoul apartment', 'model': 'house/dollhouse-studio.glb',
        'floorplan': 'house/floorplan.png', 'captures': captures,
        'coordinate_system': 'glTF: X/Z horizontal, Y up; source (x,y,z) -> (x,z,-y)',
        'provenance': 'Premade furnished model recovered from companion source; not a new panorama-only reconstruction.',
        'scale': 'Approximate; source meter convention retained without physical measurements.',
        'navigation': 'Capture sequence only; no inferred traversable edges through walls.',
        'rooms': [{k: r[k] for k in ['id', 'name', 'source_capture_ids', 'boundary_note']} for r in source['rooms']],
    }
    (house/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    types = {'.glb': 'model/gltf-binary', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg'}
    assets = {}
    for path in sorted(house.rglob('*')):
        if path.is_file():
            name = path.relative_to(output).as_posix()
            digest = sha(path)
            assets[name] = {'key': f'demos/seoul-apartment/{digest}/{name}', 'sha256': digest,
                            'bytes': path.stat().st_size, 'content_type': types[path.suffix]}
    catalog = {'id': 'seoul-apartment', 'source_bundle_sha256': SOURCE_SHA,
               'thumbnail': 'house/preview.jpg', 'assets': assets}
    (output/'catalog.json').write_text(json.dumps(catalog, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'assets': len(assets), 'bytes': sum(a['bytes'] for a in assets.values()), 'source_sha256': SOURCE_SHA}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for arg in ['bundle', 'model', 'panoramas', 'output']:
        p.add_argument('--'+arg, type=Path, required=True)
    prepare(**vars(p.parse_args()))
